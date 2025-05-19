# Monitoring Stack Installation Helm Chart
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Helm](https://img.shields.io/badge/Helm-v3-blue)](https://helm.sh)
[![MicroK8s](https://img.shields.io/badge/MicroK8s-Latest-orange)](https://microk8s.io)

> A comprehensive OpenTelemetry monitoring solution that includes Loki, Prometheus, and Grafana, with additional custom components like loki-reader.

## 📑 Table of Contents

### 📝 General Information
- [Overview](#overview)
- [Features](#-features)
- [Components](#components)
- [Loki Reader Image Options](#loki-reader-image-options)

### 🛠️ Technical Details
- [Prerequisites](#prerequisites)
- [Storage Classes](#storage-classes)
- [Service Types](#service-types)
- [Security Context](#security-context)

### 🚀 Installation
- [Quick Start](#quick-start)
  - [AKS](#for-aks)
  - [EKS](#for-eks)
  - [Windows Development](#for-windows-development)
  - [MicroK8s](#for-microk8s)
- [Manual Installation](#manual-installation)
- [Custom Configuration](#custom-configuration)
- [Installation from OCI Registry](#installation-from-oci-registry)
  - [Azure Container Registry (ACR)](#azure-container-registry-acr)
  - [GitHub Container Registry (GHCR)](#github-container-registry-ghcr)

### 🛠️ Configuration
- [RBAC Configuration](#rbac-configuration)
  - [Service Accounts](#service-accounts)
  - [Roles and Permissions](#roles-and-permissions)
  - [Cloud Provider IAM Integration](#cloud-provider-iam-integration)
    - [AKS Workload Identity](#aks-workload-identity)
    - [EKS IRSA (IAM Roles for Service Accounts)](#eks-irsa-iam-roles-for-service-accounts)

### 📈 Usage Guide
- [Accessing the Services](#accessing-the-services)
  - [MicroK8s](#microk8s)
  - [AKS](#aks)
  - [EKS](#eks)
- [Accessing Pod Logs](#accessing-pod-logs)
  - [View Logs of a Specific Pod](#view-logs-of-a-specific-pod)
  - [View Logs from Multi-Container Pods](#view-logs-from-multi-container-pods)

### 🛠️ Troubleshooting
- [Common Issues](#common-issues)
- [Verification Steps](#verification-steps)

### 📱 Magic xpi OpenTelemetry Configuration
- [Configuration Steps](#configuration-steps)
- [Verification](#verification)

## ✨ Features

- Complete OpenTelemetry monitoring solution
- Easy deployment using Helm charts
- Support for multiple Kubernetes platforms:
  - MicroK8s
  - Azure Kubernetes Service (AKS)
  - Amazon Elastic Kubernetes Service (EKS)
- Real-time metrics and monitoring
- Scalable architecture

## Overview

This Helm chart provides a comprehensive monitoring solution that can be deployed on various Kubernetes platforms:
- MicroK8s
- Azure Kubernetes Service (AKS)
- Amazon Elastic Kubernetes Service (EKS)

## Components

- **Loki**: Log aggregation system
  - Centralized log management
  - Efficient query capabilities

- **Prometheus**: Metrics collection and alerting
  - Time-series data collection
  - Robust alerting system

- **Grafana**: Visualization and dashboarding
  - Interactive dashboards
  - Multiple data source support

- **Loki Reader**: Custom component
  - Reads and processes logs from Loki
  - Custom implementation for specific needs

## Loki Reader Image Options

### Build from Source
- Use the `loki-reader` folder to build the Docker image from scratch
- Recommended for custom implementations
- Follow build instructions in the `loki-reader` folder
- Refer to [View readme](loki-reader/README.md) for detailed instructions

### Use Pre-built Image
- Included in the Helm chart
- Recommended for quick deployments
- Optimized for performance and security

## Prerequisites

### Required Tools
- Helm 3.x
- kubectl configured to access your cluster

### Supported Kubernetes Platforms
- MicroK8s
- Azure Kubernetes Service (AKS)
- Amazon Elastic Kubernetes Service (EKS)

## Installation

### Quick Start for Different Platforms

#### For AKS
1. First, download the required values files from GitHub:

   Download these files directly from GitHub by clicking on the links below:
   - [values-production.yaml](https://github.com/naviteshvaswanimagic/magic_opentelemetrydashboard/blob/DEV/helm-chart/monitoring-stack/values-production.yaml)
   - [values-production-aks.yaml](https://github.com/naviteshvaswanimagic/magic_opentelemetrydashboard/blob/DEV/helm-chart/monitoring-stack/values-production-aks.yaml)

   Save these files to a local directory (e.g., create a `monitoring-values` folder):
   ```bash
   # Create a directory for the values files
   mkdir -p monitoring-values
   
   # Move your downloaded files to this directory
   # For example, if files were downloaded to your Downloads folder:
   # mv ~/Downloads/values-production*.yaml monitoring-values/
   # These files will be used in cluster-specific deployments whereas values-production.yaml is used in every production cluster
   ```

2. Install from ACR:
```bash
helm install monitoring-stack oci://<ACR_NAME>.azurecr.io/helm/monitoring-stack --version <CHART_VERSION> -n monitoring --create-namespace --values monitoring-values/values-production.yaml --values monitoring-values/values-production-aks.yaml
```

#### For EKS
1. First, download the required values files from GitHub:

   Download these files directly from GitHub by clicking on the links below:
   - [values-production.yaml](https://github.com/naviteshvaswanimagic/magic_opentelemetrydashboard/blob/DEV/helm-chart/monitoring-stack/values-production.yaml)
   - [values-production-eks.yaml](https://github.com/naviteshvaswanimagic/magic_opentelemetrydashboard/blob/DEV/helm-chart/monitoring-stack/values-production-eks.yaml)

   Save these files to a local directory (e.g., create a `monitoring-values` folder):
   ```bash
   # Create a directory for the values files
   mkdir -p monitoring-values
   
   # Move your downloaded files to this directory
   # For example, if files were downloaded to your Downloads folder:
   # mv ~/Downloads/values-production*.yaml monitoring-values/
   # mv ~/Downloads/values-production-eks.yaml monitoring-values/
   ```

2. Important: Ensure that the default storage class in your EKS cluster is gp2. If it's not, you'll need to make gp2 the default storage class using these commands:
```powershell
# First, make gp3 non-default if it's currently default
kubectl patch storageclass gp3 -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"false"}}}'

# Then make gp2 the default storage class
kubectl patch storageclass gp2 -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'
```

3. Install from GitHub Container Registry:
```bash
helm install monitoring-stack oci://ghcr.io/naviteshvaswanimagic/monitoring-stack:0.1.4 -n monitoring --create-namespace --values monitoring-values/values-production.yaml --values monitoring-values/values-production-eks.yaml
```

#### For Windows Development
```bash
# Install from local chart
helm install monitoring-stack . -n monitoring --create-namespace --values values-production.yaml
```

#### For MicroK8s
```bash
# 1. Enable required addons
microk8s enable dns storage metallb

# 2. Install the chart
helm install monitoring-stack . -n monitoring --create-namespace --values values-production.yaml
```

### Manual Installation

1. Edit `values.yaml` to set your desired configuration

2. Install the Helm chart:

```bash
helm install monitoring-stack . -n monitoring --create-namespace
```

### Custom Configuration

You can customize the installation by providing additional parameters:

```bash
# Install with custom storage class
./set-cloud-provider.sh --provider eks --storage gp3

# Install with custom service type
./set-cloud-provider.sh --provider aks --type LoadBalancer

# Install with custom release name and namespace
./set-cloud-provider.sh --provider microk8s --release my-monitoring --namespace observability
```

## Installation from OCI Registry

### Azure Container Registry (ACR)

1. First, download the required values files from GitHub:

   Download these files directly from GitHub by clicking on the links below:
   - [values-production.yaml](https://github.com/magicxpi/magic_opentelemetrydashboard/raw/main/helm-chart/values-production.yaml)
   - [values-production-aks.yaml](https://github.com/magicxpi/magic_opentelemetrydashboard/raw/main/helm-chart/values-production-aks.yaml)

   Save these files to a local directory (e.g., create a `monitoring-values` folder):
   ```bash
   # Create a directory for the values files
   mkdir -p monitoring-values
   
   # Move your downloaded files to this directory
   # For example, if files were downloaded to your Downloads folder:
   # mv ~/Downloads/values-production*.yaml monitoring-values/
   ```

2. Login to Azure and ACR:
```bash
# Login to Azure
az login

# Login to ACR
helm registry login <ACR_NAME>.azurecr.io --username <ACR_USERNAME> --password <ACR_PASSWORD>
```

3. Install from ACR:
```bash
helm install monitoring-stack oci://<ACR_NAME>.azurecr.io/helm/monitoring-stack --version <CHART_VERSION> \
  -n monitoring --create-namespace \
  --values monitoring-values/values-production.yaml \
  --values monitoring-values/values-production-aks.yaml
```

### GitHub Container Registry (GHCR)

1. First, download the required values files from GitHub:

   Download these files directly from GitHub by clicking on the links below:
   - [values-production.yaml](https://github.com/magicxpi/magic_opentelemetrydashboard/raw/main/helm-chart/values-production.yaml)
   - [values-production-aks.yaml](https://github.com/magicxpi/magic_opentelemetrydashboard/raw/main/helm-chart/values-production-aks.yaml)

   Save these files to a local directory (e.g., create a `monitoring-values` folder):
   ```bash
   # Create a directory for the values files
   mkdir -p monitoring-values
   
   # Move your downloaded files to this directory
   # For example, if files were downloaded to your Downloads folder:
   # mv ~/Downloads/values-production*.yaml monitoring-values/
   ```

2. Login to GHCR:
```bash
# Login to GHCR
helm registry login ghcr.io --username <GITHUB_USERNAME> --password <GITHUB_TOKEN>
```

3. Install from GHCR:
```bash
helm install monitoring-stack oci://ghcr.io/<GITHUB_USERNAME>/monitoring-stack --version <CHART_VERSION> \
  -n monitoring --create-namespace \
  --values monitoring-values/values-production.yaml
```

## RBAC Configuration

The monitoring stack includes comprehensive RBAC configurations for all components:

### Service Accounts

Each component gets its own service account:
- `monitoring-stack-grafana`
- `monitoring-stack-prometheus`
- `monitoring-stack-loki`
- `loki-reader`

### Roles and Permissions

- **Prometheus**: Cluster-wide permissions to collect metrics (via ClusterRole/ClusterRoleBinding)
- **Grafana**: Namespace-scoped permissions to manage dashboards and datasources
- **Loki**: Namespace-scoped permissions to manage logs
- **Loki Reader**: Namespace-scoped permissions to interact with Loki and Prometheus

### Cloud Provider IAM Integration

#### AKS Workload Identity

For AKS, you can integrate with Azure AD Workload Identity:

```bash
./set-cloud-provider.sh --provider aks \
  --aks-workload-identity \
  --aks-tenant-id "your-tenant-id" \
  --aks-grafana-client-id "grafana-client-id" \
  --aks-prometheus-client-id "prometheus-client-id" \
  --aks-loki-client-id "loki-client-id" \
  --aks-loki-reader-client-id "loki-reader-client-id"
```

#### EKS IRSA (IAM Roles for Service Accounts)

For EKS, you can integrate with AWS IAM Roles for Service Accounts (IRSA):

```bash
./set-cloud-provider.sh --provider eks \
  --eks-irsa \
  --eks-region "us-east-1" \
  --eks-grafana-role-arn "arn:aws:iam::123456789012:role/grafana-role" \
  --eks-prometheus-role-arn "arn:aws:iam::123456789012:role/prometheus-role" \
  --eks-loki-role-arn "arn:aws:iam::123456789012:role/loki-role" \
  --eks-loki-reader-role-arn "arn:aws:iam::123456789012:role/loki-reader-role"
```

## Accessing the Services

### MicroK8s

With MicroK8s, services are exposed using MetalLB LoadBalancer:

- Grafana: http://<METALLB_IP>:3000 (default credentials: admin/admin123)
- Prometheus: http://<METALLB_IP>:80

### AKS

For AKS, services are configured as internal LoadBalancers by default:

- Use port-forwarding to access services:
  ```bash
  kubectl port-forward svc/monitoring-stack-grafana 3000:3000 -n monitoring
  kubectl port-forward svc/monitoring-stack-prometheus-server 9090:80 -n monitoring
  ```

- Or enable the ingress by setting `ingress.enabled=true` and configuring your ingress controller

### EKS

For EKS, services are configured with NLB LoadBalancers:

- Access Grafana and Prometheus using the NLB endpoints
- Or enable the ingress by setting `ingress.enabled=true` and configuring your ingress controller

## Accessing Pod Logs

You can view logs of any pod using these commands:

### View Logs of a Specific Pod
```bash
# Basic logs
kubectl logs -n monitoring <pod-name>

# Follow logs in real-time
kubectl logs -n monitoring <pod-name> -f

# Show last 100 lines
kubectl logs -n monitoring <pod-name> --tail=100

# Show logs for the last hour
kubectl logs -n monitoring <pod-name> --since=1h
```

### View Logs by Label
```bash
# View Grafana logs
kubectl logs -n monitoring -l app.kubernetes.io/name=grafana

# View Prometheus logs
kubectl logs -n monitoring -l app.kubernetes.io/name=prometheus

# View Loki logs
kubectl logs -n monitoring -l app.kubernetes.io/name=loki

# View Loki Reader logs
kubectl logs -n monitoring -l app.kubernetes.io/name=loki-reader
```

### View Logs from Previous Container Instance
```bash
# If a pod crashed and was restarted
kubectl logs -n monitoring <pod-name> --previous
```

### View Logs from Multi-Container Pods
```bash
# Specify the container name
kubectl logs -n monitoring <pod-name> -c <container-name>
```

## Configuration

### Storage Classes

The monitoring stack uses the following storage classes by default:

- MicroK8s: `microk8s-hostpath`
- AKS: `managed-premium`
- EKS: `gp2`

### Service Types

- MicroK8s: `LoadBalancer` (using MetalLB)
- AKS: `ClusterIP` (with option for internal LoadBalancer)
- EKS: `ClusterIP` (with option for NLB)

### Security Context

The deployment follows Kubernetes security best practices:
- Non-root users
- Read-only filesystems where possible
- Dropped capabilities
- Resource limits

## Magic xpi OpenTelemetry Configuration

To configure Magic xpi for OpenTelemetry:

1. Log in to Magic Monitor with admin credentials
2. Navigate to Settings -> Admin Settings
3. Under "OpenTelemetry Settings" section:
   - Select "gRPC" as the exporter type
   - Configure the collector endpoint URL (default: `http://<otel-collector-External-IP>:4317`)
     Note: You will receive the External IP address after the Helm chart installation completes
4. Save your configuration
5. Verify data collection:
   - Open Grafana portal (default: `http://<Grafana-External-IP>:3000`)
   - Navigate to the "OpenTelemetry Monitor Prom Live" dashboard
   - Confirm that metrics are being received

### Viewing and Analyzing Logs
You can view activity logs through the Grafana portal:
1. Navigate to the Grafana UI
2. Click on "Explore" in the left sidebar
3. Select "Loki" as your data source
4. Use LogQL to query and filter your logs

## Cleanup and Reinstallation

To completely remove and reinstall the monitoring stack:

```bash
# Uninstall the Helm release
helm uninstall monitoring-stack -n monitoring

# Delete the namespace
kubectl delete namespace monitoring

# Clean up leftover resources if any
kubectl delete serviceaccount -n monitoring monitoring-stack-grafana monitoring-stack-loki
kubectl delete role -n monitoring monitoring-stack-grafana monitoring-stack-loki
kubectl delete rolebinding -n monitoring monitoring-stack-grafana monitoring-stack-loki

# Reinstall with custom configuration
helm install monitoring-stack oci://<REGISTRY_URL>/monitoring-stack --version <CHART_VERSION> \
  -n monitoring \
  --create-namespace \
  --set global.cloudProvider=aks \
  --set global.storageClass.default=managed-premium \
  --set grafana.service.type=LoadBalancer
```

## Uninstallation

To uninstall the monitoring stack:

```bash
helm uninstall monitoring-stack -n monitoring
```

## Troubleshooting

If you encounter issues with the installation, check the following:

1. Verify your storage class exists:
```bash
kubectl get sc
```

2. Check pod status:
```bash
kubectl get pods -n monitoring
```

3. Check persistent volume claims:
```bash
kubectl get pvc -n monitoring
```

4. Check service accounts and RBAC resources:
```bash
kubectl get serviceaccounts -n monitoring && kubectl get roles,rolebindings -n monitoring && kubectl get clusterroles,clusterrolebindings | grep monitoring-stack
```

5. View logs for specific components:
```bash
kubectl logs -l app=loki -n monitoring && kubectl logs -l app=prometheus-server -n monitoring && kubectl logs -l app=grafana -n monitoring && kubectl logs -l app=loki-reader -n monitoring
```

## Sample Helm Commands

### For MicroK8s:
```bash
helm install monitoring-stack . -n monitoring --create-namespace \
  --set global.cloudProvider=microk8s \
  --set global.storageClass.default=microk8s-hostpath \
  --set prometheus.service.type=LoadBalancer \
  --set grafana.service.type=LoadBalancer \
  --set grafana.service.annotations."metallb\.universe\.tf/allow-shared-ip"=monitoring-stack \
  --set prometheus.service.annotations."metallb\.universe\.tf/allow-shared-ip"=monitoring-stack
```

### For AKS with Workload Identity:
```bash
helm install monitoring-stack . -n monitoring --create-namespace \
  --set global.cloudProvider=aks \
  --set global.storageClass.default=managed-premium \
  --set global.aks.workloadIdentity.enabled=true \
  --set global.aks.workloadIdentity.tenantId=<your-tenant-id> \
  --set global.aks.serviceAccounts.grafana.clientId=<grafana-client-id> \
  --set global.aks.serviceAccounts.prometheus.clientId=<prometheus-client-id> \
  --set global.aks.serviceAccounts.loki.clientId=<loki-client-id> \
  --set global.aks.serviceAccounts.lokiReader.clientId=<loki-reader-client-id>
```

### For EKS with IRSA:
```bash
helm install monitoring-stack . -n monitoring --create-namespace \
  --set global.cloudProvider=eks \
  --set global.storageClass.default=gp2 \
  --set global.eks.irsa.enabled=true \
  --set global.eks.irsa.region=us-east-1 \
  --set global.eks.serviceAccounts.grafana.roleArn=arn:aws:iam::123456789012:role/grafana-role \
  --set global.eks.serviceAccounts.prometheus.roleArn=arn:aws:iam::123456789012:role/prometheus-role \
  --set global.eks.serviceAccounts.loki.roleArn=arn:aws:iam::123456789012:role/loki-role \
  --set global.eks.serviceAccounts.lokiReader.roleArn=arn:aws:iam::123456789012:role/loki-reader-role
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

---

<div align="center">
Made with ❤️ by the Magic Team
</div>
