#!/usr/bin/env bash
set -euo pipefail

# Installs a single-node k3s cluster. Good enough for a demo/reference
# deployment of AgentGate; a real production cluster would be multi-node
# and likely managed (EKS) rather than this, but that's a much bigger
# Terraform footprint than this project needs to prove the pattern.
curl -sfL https://get.k3s.io | sh -s - --write-kubeconfig-mode 644

# Make kubeconfig easy to pull down for kubectl on your machine
mkdir -p /home/ubuntu/.kube
cp /etc/rancher/k3s/k3s.yaml /home/ubuntu/.kube/config
chown -R ubuntu:ubuntu /home/ubuntu/.kube
