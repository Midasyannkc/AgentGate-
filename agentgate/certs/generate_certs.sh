#!/usr/bin/env bash
# Generates a self-signed CA, a server cert for the gateway, and one client
# cert per demo agent (CN = agent ID, matched against policy/data.json).
# For a real deployment, replace this with a proper internal CA or a tool
# like step-ca / cert-manager; this is deliberately simple for a reference
# implementation.
set -euo pipefail

OUT_DIR="$(dirname "$0")/generated"
mkdir -p "$OUT_DIR"
cd "$OUT_DIR"

echo "Generating CA..."
openssl genrsa -out ca.key 2048
openssl req -x509 -new -nodes -key ca.key -sha256 -days 365 \
  -subj "/CN=AgentGate-Demo-CA" -out ca.crt

echo "Generating gateway server cert..."
openssl genrsa -out server.key 2048
openssl req -new -key server.key -subj "/CN=agentgate-gateway" -out server.csr
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
  -out server.crt -days 365 -sha256

for agent in agent-demo-1 agent-demo-2; do
  echo "Generating client cert for ${agent}..."
  openssl genrsa -out "${agent}.key" 2048
  openssl req -new -key "${agent}.key" -subj "/CN=${agent}" -out "${agent}.csr"
  openssl x509 -req -in "${agent}.csr" -CA ca.crt -CAkey ca.key -CAcreateserial \
    -out "${agent}.crt" -days 365 -sha256
  rm "${agent}.csr"
done

rm server.csr
echo "Done. Certs are in ${OUT_DIR}/ (gitignored — do not commit these)."
