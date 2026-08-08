#!/usr/bin/env python3
"""
Manual test client: calls the gateway as a specific agent using its client
cert, so you can see the allow/deny/rate-limit paths actually happen.

Usage:
  python3 test_client.py agent-demo-1 get_weather   # should be allowed
  python3 test_client.py agent-demo-2 list_files    # should be denied (403)
  python3 test_client.py agent-demo-1 delete_file   # should be denied (403, no agent has this)
"""
import sys
import requests

GATEWAY_URL = "https://localhost:8443"
CERTS_DIR = "../certs/generated"


def call_tool(agent_id: str, tool: str):
    cert = (f"{CERTS_DIR}/{agent_id}.crt", f"{CERTS_DIR}/{agent_id}.key")
    try:
        resp = requests.post(
            f"{GATEWAY_URL}/{tool}",
            cert=cert,
            verify=f"{CERTS_DIR}/ca.crt",
            json={},
            timeout=10,
        )
        print(f"[{agent_id} -> {tool}] status={resp.status_code} body={resp.json()}")
    except requests.RequestException as e:
        print(f"[{agent_id} -> {tool}] request failed: {e}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    call_tool(sys.argv[1], sys.argv[2])
