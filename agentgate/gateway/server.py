#!/usr/bin/env python3
"""
AgentGate: a policy-enforcing gateway for AI agent traffic.

Every request must present a client certificate under mTLS. The cert's CN
becomes the agent's identity — not a shared API key, so every request is
attributable to a specific agent. Each request is checked against an OPA
policy (which tools this agent may call) and an in-process rate limiter
before being forwarded to the backend service. All requests, allowed and
denied, are logged for audit.

Built on Python's http.server + ssl rather than a framework, because
extracting the verified client certificate's subject CN for mTLS identity
needs direct access to the underlying SSL socket, which most WSGI-based
frameworks don't expose cleanly.
"""
import json
import logging
import os
import ssl
import time
from collections import defaultdict, deque
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
audit_log = logging.getLogger("agentgate.audit")
audit_handler = logging.FileHandler("audit.log")
audit_handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
audit_log.addHandler(audit_handler)

OPA_URL = os.environ.get("OPA_URL", "http://localhost:8181/v1/data/agentgate")
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:6000")
GATEWAY_CERT = os.environ.get("GATEWAY_CERT", "certs/generated/server.crt")
GATEWAY_KEY = os.environ.get("GATEWAY_KEY", "certs/generated/server.key")
CA_CERT = os.environ.get("CA_CERT", "certs/generated/ca.crt")

# Sliding-window rate limiter: agent_id -> deque of recent request timestamps.
_request_log = defaultdict(deque)


def is_rate_limited(agent_id: str, limit_per_minute: int) -> bool:
    now = time.time()
    window = _request_log[agent_id]
    while window and now - window[0] > 60:
        window.popleft()
    if len(window) >= limit_per_minute:
        return True
    window.append(now)
    return False


def get_rate_limit(agent_id: str) -> int:
    resp = requests.post(f"{OPA_URL}/rate_limit_per_minute", json={"input": {"agent": agent_id}}, timeout=5)
    result = resp.json().get("result")
    return result if result is not None else 5  # conservative default if agent isn't in policy data


def check_policy(agent_id: str, tool: str) -> bool:
    resp = requests.post(f"{OPA_URL}/allow", json={"input": {"agent": agent_id, "tool": tool}}, timeout=5)
    return bool(resp.json().get("result", False))


class GatewayHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        tool = self.path.lstrip("/")

        # Extract the verified client cert's CN as the agent identity.
        cert = self.connection.getpeercert()
        if not cert:
            self._respond(401, {"error": "client certificate required"})
            return
        agent_id = None
        for field in cert.get("subject", []):
            for key, value in field:
                if key == "commonName":
                    agent_id = value

        if not agent_id:
            self._respond(401, {"error": "could not determine agent identity from certificate"})
            audit_log.info(json.dumps({"agent": None, "tool": tool, "decision": "deny", "reason": "no_cn"}))
            return

        limit = get_rate_limit(agent_id)
        if is_rate_limited(agent_id, limit):
            self._respond(429, {"error": "rate limit exceeded"})
            audit_log.info(json.dumps({"agent": agent_id, "tool": tool, "decision": "deny", "reason": "rate_limited"}))
            return

        allowed = check_policy(agent_id, tool)
        if not allowed:
            self._respond(403, {"error": f"agent '{agent_id}' is not authorized to call '{tool}'"})
            audit_log.info(json.dumps({"agent": agent_id, "tool": tool, "decision": "deny", "reason": "policy_denied"}))
            return

        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length) if content_length else b"{}"
            backend_resp = requests.post(f"{BACKEND_URL}/{tool}", data=body, timeout=10)
            self._respond(backend_resp.status_code, backend_resp.json())
            audit_log.info(json.dumps({"agent": agent_id, "tool": tool, "decision": "allow", "backend_status": backend_resp.status_code}))
        except requests.RequestException as e:
            self._respond(502, {"error": f"backend unreachable: {e}"})
            audit_log.info(json.dumps({"agent": agent_id, "tool": tool, "decision": "allow_but_backend_failed", "error": str(e)}))

    def _respond(self, status: int, payload: dict):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass  # audit_log handles structured logging; suppress default access log noise


def run():
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile=GATEWAY_CERT, keyfile=GATEWAY_KEY)
    context.load_verify_locations(cafile=CA_CERT)
    context.verify_mode = ssl.CERT_REQUIRED

    server = HTTPServer(("0.0.0.0", 8443), GatewayHandler)
    server.socket = context.wrap_socket(server.socket, server_side=True)

    logging.info("AgentGate listening on :8443 (mTLS required)")
    server.serve_forever()


if __name__ == "__main__":
    run()
