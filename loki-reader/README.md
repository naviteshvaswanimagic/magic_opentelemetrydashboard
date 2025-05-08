# Otel-Loki-Reader

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

## 📑 Table of Contents
- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Uninstallation](#uninstallation)

## Overview

Otel-Loki-Reader is a specialized tool for reading and processing logs from Loki and converting them into Prometheus metrics through OpenTelemetry (OTel). It connects to a Loki log server, extracts specific metrics from structured logs, and exports them to Prometheus. This enables better monitoring and visualization of log data as time-series metrics, facilitating integration with Grafana dashboards and alerting systems.

The tool is particularly useful for monitoring server and application health by extracting information like:
- Server start/stop events
- Error rates
- Flow execution rates
- Session uptimes
- Server status (Running, Stopped, Error, Unresponsive)

## Prerequisites

Before installing Otel-Loki-Reader, ensure you have the following components:

- Python 3.11+
- Loki server (for log storage)
- Prometheus server with Push Gateway (for metrics storage)
- Docker/Podman (for containerized deployment)
- Kubernetes/MicroK8s (for orchestrated deployment - optional)

## Installation

### Local Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/naviteshvaswanimagic/magic_opentelemetrydashboard.git
   cd magic_opentelemetrydashboard
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure the application (copy `.env.example` to `.env` and modify as needed)

4. Run the application:
   ```bash
   python loki_reader.py
   ```

### Docker Installation

1. Build the Docker image:
   ```bash
   docker build -t loki-reader:latest .
   ```

2. Run the container:
   ```bash
   docker run -d --name loki-reader --env-file .env loki-reader:latest
   ```

### Podman Installation (Windows)

1. Build using provided script:
   ```bash
   build.bat
   ```

2. The image will be exported to `./exported-images/`

### Kubernetes Deployment

1. Build and export the image:
   - Windows: Use `build.bat`
   - Linux: Use `build.sh`

2. Deploy to Kubernetes:
   - Windows: Use `deploy-k8s.bat`
   - Linux: Use `deploy-k8s.sh`

## Uninstallation

### Local Uninstallation

1. Stop the application if running:
   ```bash
   pkill -f loki_reader.py
   ```

2. Remove the virtual environment and dependencies (if applicable):
   ```bash
   rm -rf venv
   pip uninstall -r requirements.txt -y
   ```

### Docker Uninstallation

1. Stop and remove the container:
   ```bash
   docker stop loki-reader
   docker rm loki-reader
   ```

2. Remove the Docker image:
   ```bash
   docker rmi loki-reader:latest
   ```

### Kubernetes Uninstallation

1. Remove the deployment:
   ```bash
   kubectl delete -f kubernetes/
   ```

2. Clean up persistent volumes if used:
   ```bash
   kubectl delete pvc -l app=loki-reader
   ```

## 5. Features and else

### 5.1 Features

- **Loki Log Collection**: Connects to Loki to query and extract log entries
- **Metrics Generation**: Converts log data into time-series metrics
- **Supported Formats**: [View supported logs formats](Supported%20Logs%20format.txt)
- **Prometheus Integration**: Pushes metrics to Prometheus via push gateway
- **Server Status Monitoring**: Tracks server status and detects unresponsive systems
- **Project-level Aggregation**: Consolidates metrics from multiple servers into project-level summaries
- **Containerized Deployment**: Ready for Docker and Kubernetes deployment
- **Configurable**: All parameters can be adjusted via environment variables

### 5.2 Configuration

All configuration is done via environment variables, which can be set in the `.env` file:

| Variable | Description | Default Value |
|----------|-------------|---------------|
| Loki_SERVER_HOST | Loki server hostname | loki |
| Loki_SERVER_PORT | Loki server port | 3100 |
| MAX_WORKERS | Number of worker threads | 10 |
| PROMETHEUS_GATEWAY | Prometheus push gateway URL | http://prometheus-prometheus-pushgateway:9091 |
| PROMETHEUS_JOB_NAME | Job name for Prometheus metrics | summary_metrics |
| LOG_LEVEL | Logging level | INFO |
| LOG_DIR | Log directory | logs |
| LOG_MAX_BYTES | Maximum log file size | 10485760 |
| LOG_BACKUP_COUNT | Number of backup log files | 5 |
| ENABLE_CONSOLE_LOG | Enable console logging | true |
| ERROR_TIMEOUT_HOURS | Error status timeout in hours | 1 |
| UNRESPONSIVE_TIMEOUT_MINUTES | Unresponsive status timeout in minutes | 5 |
| RESET_TIMEOUT_HOURS | Reset timeout in hours | 3 |

### 5.3 Metrics

The following metrics are generated:

| Metric | Description | Labels |
|--------|-------------|--------|
| project_name | Name of the project | serverid, projectkey |
| current_session_start | Session start timestamp | serverid, projectkey |
| latest_transaction_time | Latest transaction timestamp | serverid, projectkey |
| uptime_current_session_ns | Session uptime in nanoseconds | serverid, projectkey |
| uptime_current_session_sec | Session uptime in seconds | serverid, projectkey |
| total_errors_current_session | Total errors in current session | serverid, projectkey |
| errors_last_hour | Error count in last hour | serverid, projectkey |
| total_flows_current_session | Total flow count in session | serverid, projectkey |
| flows_last_hour | Flow count in last hour | serverid, projectkey |
| server_status | Current server status | serverid, projectkey, status |
| project_status | Current project status | projectkey, status |
| server_count | Count of servers | projectkey |

### 5.4 Usage

The application runs continuously, querying Loki for new logs at regular intervals and pushing metrics to Prometheus.

#### Command line

```bash
python loki_reader.py
```

#### Docker

```bash
docker run -d --name loki-reader --env-file .env loki-reader:latest
```

#### Kubernetes

Once deployed with the `deploy-k8s.sh` or `deploy-k8s.bat` script, the application runs as a deployment in the specified namespace.

### 5.5 Architecture

The application consists of several key components:

1. **Config**: Manages configuration and sets up logging
2. **MetricsState**: Maintains the current state of metrics and server sessions
3. **LokiLogReader**: Queries Loki for logs and processes the results
4. **Prometheus Integration**: Pushes metrics to the Prometheus push gateway

### 5.6 Security

- The application uses environment variables for configuration
- No authentication credentials are hardcoded
- Network communication should be secured using HTTPS where applicable

### 5.7 Testing

Manual testing can be performed by:

1. Setting up a Loki server with sample logs
2. Setting up a Prometheus server with push gateway
3. Running the application with appropriate configuration
4. Verifying metrics in Prometheus

### 5.8 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### 5.9 Helm Chart - Otel Loki Reader Monitoring Stack

This Helm chart deploys a complete OpenTelemetry-based monitoring stack integrated with Loki and Prometheus. It includes components like Grafana, Loki, Promtail, Pushgateway, Prometheus, and a custom Loki Reader application that transforms logs into Prometheus metrics.

#### Prerequisites
1. Kubernetes Cluster (MicroK8s, Minikube, etc.)
2. Helm v3 or higher
3. MetalLB (for LoadBalancer support if using MicroK8s)

#### Components
1. Grafana: Dashboards UI
2. Prometheus: Metrics collection
3. Alertmanager: Alerting system
4. Loki: Log storage backend
5. Promtail: Log shipping agent
6. Pushgateway: Push metrics endpoint
7. Otel-Collector: Ingest metrics, logs, and traces
8. Loki Reader: Converts logs to Prometheus metrics

#### Helm Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/naviteshvaswanimagic/magic_opentelemetrydashboard.git
   cd Otel-Loki-Reader/helm_chart/monitoring-stack
   ```
2. Deploy the chart using:
   ```bash
   ./deploy-monitoring.sh
   ```
Or with plain Helm:
   ```bash
   helm install monitoring-stack . -n monitoring --create-namespace
   ```

#### Post-Installation
1. To verify that everything is running:
   ```bash
   kubectl get pods -n monitoring
   kubectl get svc -n monitoring
   ```

#### External Access
1. Use the following commands to retrieve the service IPs:
   - Grafana (Dashboards UI):
     ```bash
     kubectl get svc -n monitoring -l app.kubernetes.io/name=grafana
     ```
   - Loki Reader (Log aggregation):
     ```bash
     kubectl get svc -n monitoring -l app=loki-reader
     ```
   - Prometheus Pushgateway:
     ```bash
     kubectl get svc -n monitoring -l app=prometheus-pushgateway
     ```
   - OpenTelemetry Collector:
     ```bash
     kubectl get svc -n monitoring -l app.kubernetes.io/name=otel-collector
     ```

#### Grafana Login
1. Username: admin
2. Password: admin123

#### Customization
1. You can customize the deployment by editing the values.yaml file or setting values inline:
   ```bash
   helm install monitoring-stack . -n monitoring -f values.yaml
   ```

#### Upgrade
1. To upgrade the stack after making changes:
   ```bash
   helm upgrade monitoring-stack . -n monitoring
   ```

#### Uninstall
1. To remove all components:
   ```bash
   ./undeploy-monitoring.sh
   ```

   Or use Helm directly:
   ```bash
   helm uninstall monitoring-stack -n monitoring
   ```

### 5.10 License

This project is licensed under the MIT License - see the LICENSE file for details.

### 5.11 Contact

For questions or support, please open an issue on the GitHub repository. 

<div align="center">
Made with ❤️ by the Magic Team
</div>