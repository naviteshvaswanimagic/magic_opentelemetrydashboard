#!/bin/bash

set -e

NAMESPACE="monitoring"
RELEASE_NAME="monitoring-stack"

echo "🧹 Uninstalling Helm release '$RELEASE_NAME'..."
helm uninstall $RELEASE_NAME -n $NAMESPACE || echo "⚠️  Helm release not found or already removed."

echo "🕓 Waiting for all pods to terminate in namespace '$NAMESPACE'..."
for i in {1..20}; do
  PODS=$(microk8s.kubectl get pods -n $NAMESPACE --no-headers 2>/dev/null | wc -l)
  if [[ "$PODS" -eq 0 ]]; then
    echo "✅ All pods terminated."
    break
  fi
  echo "⏳ Still waiting... ($i/20)"
  sleep 3
done

echo "🗑️  Deleting namespace '$NAMESPACE'..."
microk8s.kubectl delete namespace $NAMESPACE || echo "⚠️  Namespace not found or already deleted."

echo "🗑️  Deleting 'loki-reader' deployment if it still exists..."
microk8s.kubectl delete deployment loki-reader -n $NAMESPACE --ignore-not-found=true


echo "🎉 Uninstallation complete!"
echo "🚀 You can now redeploy the monitoring stack if needed."