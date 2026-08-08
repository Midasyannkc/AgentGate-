# AgentGate

A zero-trust gateway for AI agent traffic. Every agent authenticates with a
distinct mTLS client certificate — not a shared API key — so every request
is attributable to a specific agent. Each tool call is checked against an
OPA policy before being forwarded, rate-limited per agent, and logged for
audit. Runs on Kubernetes, provisioned via Terraform, built and tested
through a GitHub Actions pipeline.

## Architecture

```
 Agent (client cert: CN=agent-id)
        |  mTLS
        v
 Gateway (gateway/server.py, :8443)
   |-- extracts agent identity from the verified client cert's CN
   |-- checks rate limit (in-process sliding window, per agent)
   |-- checks OPA policy: POST /v1/data/agentgate/allow
   |-- logs every request (allow/deny/rate-limited) to audit.log
        |
        v (only if allowed)
 Backend service (backend/app.py, :6000)
   |-- get_weather, list_files, delete_file (demo tools of varying sensitivity)

 OPA (policy/agentgate.rego + policy/data.json, :8181)
   |-- per-agent tool allowlist and rate limit, evaluated on every request
```

## Why mTLS + OPA, not just an API key

A shared API key can't tell two agents apart, can't be scoped per-tool
without custom logic bolted onto every service, and leaks the same blast
radius to every caller if it's ever exposed. mTLS gives each agent a
distinct, hard-to-forge identity; OPA gives that identity a policy that's
declarative, testable (see `policy/agentgate_test.rego`), and changeable
without redeploying the gateway.

## Setup

### 1. Provision the k3s cluster
```bash
cd terraform
terraform init
terraform apply -var="key_name=YOUR_KEYPAIR" -var="my_ip_cidr=YOUR_IP/32"
terraform output kubeconfig_fetch_command
# run the printed scp command, then:
export KUBECONFIG=./kubeconfig-agentgate
kubectl get nodes   # should show the one k3s node, Ready
```

### 2. Generate mTLS certs
```bash
cd certs
./generate_certs.sh
```
This creates a CA, a server cert for the gateway, and client certs for two
demo agents (`agent-demo-1`, `agent-demo-2`) in `certs/generated/` —
gitignored, regenerate locally rather than committing them.

### 3. Test the policy in isolation
```bash
cd policy
opa test . -v
```

### 4. Run everything locally (no cluster needed, for fast iteration)
```bash
# terminal 1
docker run -p 8181:8181 -v $(pwd)/policy:/policy openpolicyagent/opa:0.65.0 \
  run --server /policy/agentgate.rego /policy/data.json

# terminal 2
cd backend && pip install -r requirements.txt && python3 app.py

# terminal 3
cd gateway && pip install -r requirements.txt && python3 server.py

# terminal 4 — test the allow and deny paths
cd gateway
python3 test_client.py agent-demo-1 get_weather   # 200, allowed
python3 test_client.py agent-demo-2 list_files    # 403, not in agent-demo-2's allowlist
python3 test_client.py agent-demo-1 delete_file   # 403, no agent is allowed this tool
```
Check `gateway/audit.log` afterward — every one of those calls should have
a logged entry with the decision and reason.

### 5. Run the gateway's own unit tests
```bash
cd gateway && python3 -m pytest tests/ -v
```

### 6. Deploy to the k3s cluster
```bash
kubectl apply -f k8s/namespace.yaml

kubectl create configmap agentgate-policy \
  --from-file=agentgate.rego=policy/agentgate.rego \
  --from-file=data.json=policy/data.json -n agentgate

kubectl create secret generic agentgate-certs \
  --from-file=server.crt=certs/generated/server.crt \
  --from-file=server.key=certs/generated/server.key \
  --from-file=ca.crt=certs/generated/ca.crt -n agentgate

kubectl apply -f k8s/opa.yaml
kubectl apply -f k8s/backend.yaml
kubectl apply -f k8s/gateway.yaml
kubectl get pods -n agentgate   # confirm all three are Running
```

### 7. Enable the CI/CD pipeline
Pushing to `main` runs the policy tests and gateway unit tests, then builds
both Docker images. Deploying to the cluster requires manually triggering
the workflow with `deploy: true` and a `KUBECONFIG_B64` repo secret
(base64 of your kubeconfig) — deploys are never automatic on push.

## Teardown
```bash
cd terraform
terraform destroy
```

## Status
All components are implemented and independently testable: the OPA policy
has real unit tests, the gateway's rate limiter has real unit tests, and
`test_client.py` exercises the full allow/deny path end to end. Not yet
done: pushing built images to a real container registry (currently builds
locally in CI only) and TLS cert rotation — both called out as the next
steps rather than glossed over.
