#!/bin/bash

# Set variables
export IMAGE_NAME="loki-reader"
export IMAGE_TAG="latest"
export EXPORT_PATH="/home/itsuser/images"
export NAMESPACE="monitoring"
export ENV_FILE="/home/itsuser/otel-loki-reader/.env"  # Update this path to your .env file location

# Check if .env file exists
if [ ! -f "$ENV_FILE" ]; then
    echo "Error: .env file not found at ${ENV_FILE}"
    exit 1
fi

# Find the most recent exported image
export LATEST_IMAGE=$(ls -t ${EXPORT_PATH}/${IMAGE_NAME}_*.tar 2>/dev/null | head -n1)

if [ -z "$LATEST_IMAGE" ]; then
    echo "Error: No exported image found in ${EXPORT_PATH}"
    exit 1
fi

echo "Found image: ${LATEST_IMAGE}"

# Load the image into microk8s containerd
echo "Loading image into microk8s containerd..."
sudo microk8s ctr image import "${LATEST_IMAGE}"
if [ $? -ne 0 ]; then
    echo "Error: Failed to load image"
    exit 1
fi

# Create namespace if it doesn't exist
echo "Creating namespace if it doesn't exist..."
sudo microk8s kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | sudo microk8s kubectl apply -f -

# Delete existing ConfigMap if it exists
echo "Removing existing ConfigMap if any..."
sudo microk8s kubectl delete configmap loki-reader-config -n ${NAMESPACE} --ignore-not-found

# Create ConfigMap from .env file
echo "Creating ConfigMap from .env file..."
sudo microk8s kubectl create configmap loki-reader-config --from-file=.env=${ENV_FILE} -n ${NAMESPACE}
if [ $? -ne 0 ]; then
    echo "Error: Failed to create ConfigMap"
    exit 1
fi

# Verify ConfigMap creation
echo "Verifying ConfigMap..."
sudo microk8s kubectl get configmap loki-reader-config -n ${NAMESPACE}

# Create Kubernetes deployment
echo "Creating Kubernetes deployment..."
cat << EOF > deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: loki-reader
  namespace: ${NAMESPACE}
spec:
  replicas: 1
  selector:
    matchLabels:
      app: loki-reader
  template:
    metadata:
      labels:
        app: loki-reader
    spec:
      containers:
      - name: loki-reader
        image: localhost/${IMAGE_NAME}:${IMAGE_TAG}
        imagePullPolicy: Never
        envFrom:
        - configMapRef:
            name: loki-reader-config
        volumeMounts:
        - name: logs
          mountPath: /app/logs
      volumes:
      - name: logs
        emptyDir: {}
EOF

# Delete existing deployment if it exists
echo "Removing existing deployment if any..."
sudo microk8s kubectl delete deployment loki-reader -n ${NAMESPACE} --ignore-not-found

# Apply new deployment
echo "Applying deployment..."
sudo microk8s kubectl apply -f deployment.yaml
if [ $? -ne 0 ]; then
    echo "Error: Failed to apply deployment"
    rm deployment.yaml
    exit 1
fi

# Clean up temporary files
rm deployment.yaml

echo "Deployment completed successfully."
echo "You can check the status with: sudo microk8s kubectl get pods -n ${NAMESPACE}"
echo "View logs with: sudo microk8s kubectl logs -f deployment/loki-reader -n ${NAMESPACE}"

# List deployed resources
echo -e "\nChecking deployment status..."
sudo microk8s kubectl get all -n ${NAMESPACE} | grep loki-reader

# Show pod logs for debugging
echo -e "\nShowing pod logs (if any)..."
POD_NAME=$(sudo microk8s kubectl get pods -n ${NAMESPACE} -l app=loki-reader -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
if [ ! -z "$POD_NAME" ]; then
    sudo microk8s kubectl logs -n ${NAMESPACE} $POD_NAME
fi 