#!/bin/bash

set -e

NAMESPACE="monitoring"
RELEASE_NAME="monitoring-stack"
CHART_PATH="."

echo "🚀 Creating namespace if not exists..."
microk8s.kubectl get ns $NAMESPACE >/dev/null 2>&1 || microk8s.kubectl create ns $NAMESPACE

echo "📦 Installing Helm chart..."
helm install $RELEASE_NAME $CHART_PATH -n $NAMESPACE

echo "⏳ Waiting for Grafana service to be ready..."

# Wait for Grafana service to appear
while [[ -z $(microk8s.kubectl get svc $RELEASE_NAME-grafana -n $NAMESPACE --no-headers 2>/dev/null) ]]; do
  sleep 2
done

# Wait for external IP or NodePort to be assigned
for i in {1..20}; do
  GRAFANA_IP=$(microk8s.kubectl get svc $RELEASE_NAME-grafana -n $NAMESPACE -o jsonpath="{.status.loadBalancer.ingress[0].ip}" 2>/dev/null)
  if [[ -z "$GRAFANA_IP" ]]; then
    echo "🔎 No external IP found, falling back to node IP."
    GRAFANA_IP=$(hostname -I | awk '{print $1}')
  fi

  if [[ -n "$GRAFANA_IP" ]]; then
    break
  fi
  echo "⏳ Waiting for Grafana IP... ($i/20)"
  sleep 5
done

if [[ -z "$GRAFANA_IP" ]]; then
  echo "❌ Failed to retrieve Grafana IP."
  exit 1
fi

echo "🌐 Grafana IP is: $GRAFANA_IP"




