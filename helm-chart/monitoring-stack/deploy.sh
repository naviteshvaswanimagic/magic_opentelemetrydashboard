#!/bin/bash

# Default values
ENVIRONMENT="production"
NAMESPACE="monitoring"
RELEASE_NAME="monitoring-stack"
VALUES_FILE="values.yaml"
DRY_RUN=false
DEBUG=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --environment|-e)
      ENVIRONMENT="$2"
      shift 2
      ;;
    --namespace|-n)
      NAMESPACE="$2"
      shift 2
      ;;
    --release-name|-r)
      RELEASE_NAME="$2"
      shift 2
      ;;
    --values-file|-f)
      VALUES_FILE="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    --debug)
      DEBUG=true
      shift
      ;;
    --help|-h)
      echo "Usage: $0 [options]"
      echo "Options:"
      echo "  --environment, -e     Environment to deploy to (default: production)"
      echo "  --namespace, -n       Kubernetes namespace (default: monitoring)"
      echo "  --release-name, -r    Helm release name (default: monitoring-stack)"
      echo "  --values-file, -f     Values file to use (default: values.yaml)"
      echo "  --dry-run             Perform a dry run without making changes"
      echo "  --debug               Enable debug output"
      echo "  --help, -h            Show this help message"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Set debug mode if requested
if [ "$DEBUG" = true ]; then
  set -x
fi

# Check if kubectl is installed
if ! command -v kubectl &> /dev/null; then
  echo "Error: kubectl is not installed"
  exit 1
fi

# Check if helm is installed
if ! command -v helm &> /dev/null; then
  echo "Error: helm is not installed"
  exit 1
fi

# Check if the namespace exists, create it if it doesn't
if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
  echo "Creating namespace $NAMESPACE..."
  kubectl create namespace "$NAMESPACE"
fi

# Build the helm upgrade command
HELM_CMD="helm upgrade --install $RELEASE_NAME ."

# Add namespace
HELM_CMD="$HELM_CMD --namespace $NAMESPACE"

# Add values file
HELM_CMD="$HELM_CMD --values $VALUES_FILE"

# Add environment-specific values file if it exists
ENV_VALUES_FILE="values-$ENVIRONMENT.yaml"
if [ -f "$ENV_VALUES_FILE" ]; then
  HELM_CMD="$HELM_CMD --values $ENV_VALUES_FILE"
fi

# Add dry run flag if requested
if [ "$DRY_RUN" = true ]; then
  HELM_CMD="$HELM_CMD --dry-run"
fi

# Execute the helm command
echo "Deploying to environment: $ENVIRONMENT"
echo "Using namespace: $NAMESPACE"
echo "Release name: $RELEASE_NAME"
echo "Values file: $VALUES_FILE"
if [ -f "$ENV_VALUES_FILE" ]; then
  echo "Environment-specific values file: $ENV_VALUES_FILE"
fi
if [ "$DRY_RUN" = true ]; then
  echo "Performing dry run..."
fi

eval "$HELM_CMD"

# Check if the deployment was successful
if [ $? -eq 0 ]; then
  echo "Deployment completed successfully"
  
  # If not a dry run, wait for the deployment to be ready
  if [ "$DRY_RUN" = false ]; then
    echo "Waiting for deployment to be ready..."
    kubectl rollout status deployment/$RELEASE_NAME -n $NAMESPACE
    
    if [ $? -eq 0 ]; then
      echo "Deployment is ready"
    else
      echo "Deployment failed to become ready"
      exit 1
    fi
  fi
else
  echo "Deployment failed"
  exit 1
fi 