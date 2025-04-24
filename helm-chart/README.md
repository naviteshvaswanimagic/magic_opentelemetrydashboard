# Monitoring Stack Installtion Helm Chart

A complete monitoring solution that includes Loki, Prometheus, and Grafana, with additional custom components like loki-reader.

## Overview

This Helm chart provides a comprehensive monitoring solution that can be deployed on various Kubernetes platforms:
- MicroK8s
- Azure Kubernetes Service (AKS)
- Amazon Elastic Kubernetes Service (EKS)

## Components

- **Loki**: Log aggregation system
- **Prometheus**: Metrics collection and alerting
- **Grafana**: Visualization and dashboarding
- **Loki Reader**: Custom component for reading and processing logs from Loki

## Prerequisites

- Kubernetes cluster (MicroK8s, AKS, or EKS)
- Helm 3.x
- kubectl configured to access your cluster

## Installation

### Quick Install with Automatic Cloud Provider Detection

Use the provided script to automatically configure and install the monitoring stack based on your cloud provider:

```bash
chmod +x set-cloud-provider.sh
./set-cloud-provider.sh --provider microk8s
./set-cloud-provider.sh --provider aks
./set-cloud-provider.sh --provider eks
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