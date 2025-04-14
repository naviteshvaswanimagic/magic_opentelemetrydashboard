import requests
import json
from datetime import datetime, timedelta
import pytz
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway
import time
from collections import defaultdict
import traceback
import logging
from logging.handlers import RotatingFileHandler
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
class Config:
    # Server Configuration
    LOKI_SERVER_HOST = os.getenv('Loki_SERVER_HOST', '10.9.9.149')
    LOKI_SERVER_PORT = int(os.getenv('Loki_SERVER_PORT', '3100'))
    MAX_WORKERS = int(os.getenv('MAX_WORKERS', '10'))

    # Prometheus Configuration
    PROMETHEUS_GATEWAY = os.getenv('PROMETHEUS_GATEWAY', 'http://10.9.8.59:9091')
    PROMETHEUS_JOB_NAME = os.getenv('PROMETHEUS_JOB_NAME', 'summary_metrics')

    # Logging Configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_DIR = os.getenv('LOG_DIR', 'logs')
    LOG_MAX_BYTES = int(os.getenv('LOG_MAX_BYTES', '10485760'))
    LOG_BACKUP_COUNT = int(os.getenv('LOG_BACKUP_COUNT', '5'))

    # Metrics Configuration
    ERROR_TIMEOUT_HOURS = int(os.getenv('ERROR_TIMEOUT_HOURS', '1'))
    UNRESPONSIVE_TIMEOUT_MINUTES = int(os.getenv('UNRESPONSIVE_TIMEOUT_MINUTES', '5'))
    RESET_TIMEOUT_HOURS = int(os.getenv('RESET_TIMEOUT_HOURS', '3'))

    @staticmethod
    def setup_logging():
        """Setup logging configuration"""
        log_level = getattr(logging, Config.LOG_LEVEL.upper())
        os.makedirs(Config.LOG_DIR, exist_ok=True)
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        
        # Create file handler
        file_handler = RotatingFileHandler(
            os.path.join(Config.LOG_DIR, 'loki_reader.log'),
            maxBytes=Config.LOG_MAX_BYTES,
            backupCount=Config.LOG_BACKUP_COUNT
        )
        file_handler.setFormatter(formatter)
        
        # Get root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        
        # Remove any existing handlers
        root_logger.handlers = []
        
        # Add handlers
        root_logger.addHandler(console_handler)
        root_logger.addHandler(file_handler)

# Setup logging
Config.setup_logging()
logger = logging.getLogger(__name__)

# Global registry for Prometheus
REGISTRY = CollectorRegistry()

# Server status constants (copied from otel.py)
class ServerStatus:
    RUNNING = "Running"
    STOPPED = "Stopped"
    ERROR = "Error"
    UNRESPONSIVE = "Unresponsive"

class StatusMapping:
    RUNNING = 1
    STOPPED = 2
    ERROR = 3
    UNRESPONSIVE = 4
    
    @staticmethod
    def get_numeric_status(status_text):
        status_map = {
            ServerStatus.RUNNING: StatusMapping.RUNNING,
            ServerStatus.STOPPED: StatusMapping.STOPPED,
            ServerStatus.ERROR: StatusMapping.ERROR,
            ServerStatus.UNRESPONSIVE: StatusMapping.UNRESPONSIVE
        }
        return status_map.get(status_text, 0)

# Create gauges for each KPI (copied from otel.py)
SUMMARY_METRICS = {
    'project_name': Gauge('project_name', 'Name of the Project', ['serverid', 'projectkey'], registry=REGISTRY),
    'current_session_start': Gauge('current_session_start', 'Current Session Start Time', ['serverid', 'projectkey'], registry=REGISTRY),
    'latest_transaction_time': Gauge('latest_transaction_time', 'Latest Transaction Time', ['serverid', 'projectkey'], registry=REGISTRY),
    'uptime_current_session_ns': Gauge('uptime_current_session_ns', 'Uptime of Current Session in Nanoseconds', ['serverid', 'projectkey'], registry=REGISTRY),
    'uptime_current_session_sec': Gauge('uptime_current_session_sec', 'Uptime of Current Session in Seconds', ['serverid', 'projectkey'], registry=REGISTRY),
    'total_errors_current_session': Gauge('total_errors_current_session', 'Total Errors in Current Session', ['serverid', 'projectkey'], registry=REGISTRY),
    'errors_last_hour': Gauge('errors_last_hour', 'Errors in Last Hour', ['serverid', 'projectkey'], registry=REGISTRY),
    'total_flows_current_session': Gauge('total_flows_current_session', 'Total Flows Executed Current Session', ['serverid', 'projectkey'], registry=REGISTRY),
    'flows_last_hour': Gauge('flows_last_hour', 'Flows Executed in Last Hour', ['serverid', 'projectkey'], registry=REGISTRY),
    'server_status': Gauge('server_status', 'Current Server Status', ['serverid', 'projectkey', 'status'], registry=REGISTRY),
    'project_status': Gauge('project_status', 'Current Project Status', ['projectkey', 'status'], registry=REGISTRY),
    'server_count': Gauge('server_count', 'Count of Servers', ['projectkey'], registry=REGISTRY)
}

class MetricsState:
    def __init__(self):
        self.server_sessions = defaultdict(dict)
        self.project_servers = defaultdict(dict)
        self.server_history = defaultdict(list)
        self.error_timestamps = {}
        self.last_project_status = {}
        self.last_processed_timestamp = 0  # Track last processed timestamp to avoid duplicates

    def update_metrics(self, server_id, project_key, msg_type, timestamp):
        """Update metrics based on the log entry"""
        try:
            # Skip if we've already processed this timestamp
            if timestamp <= self.last_processed_timestamp:
                return
            
            # Initialize server session if it doesn't exist
            if server_id not in self.server_sessions:
                self.update_server_start(server_id, project_key, timestamp)

            session = self.server_sessions[server_id]
            session['last_seen'] = timestamp
            
            # Update latest transaction time
            SUMMARY_METRICS['latest_transaction_time'].labels(serverid=server_id, projectkey=project_key).set(timestamp)
            
            # Update metrics based on message type
            if msg_type == 15:  # Error message
                session['error_count'] += 1
                self.server_history[server_id].append({'type': 'error', 'time': timestamp})
                self._update_server_status(server_id, project_key, ServerStatus.ERROR)
            elif msg_type == 5:  # Flow completed
                session['flow_count'] += 1
                self.server_history[server_id].append({'type': 'flow', 'time': timestamp})
            elif msg_type == 3:  # Server Stop
                self._update_server_status(server_id, project_key, ServerStatus.STOPPED)
            elif msg_type == 1:  # Server Start
                self.update_server_start(server_id, project_key, timestamp)

            # Update session metrics
            self._update_session_metrics(server_id, project_key, timestamp)
            
            # Update last processed timestamp
            self.last_processed_timestamp = timestamp

        except Exception as e:
            logger.error(f"Error updating metrics: {e}")
            logger.error(traceback.format_exc())

    def update_server_start(self, server_id, project_key, timestamp):
        """Handle server start event"""
        try:
            self.server_sessions[server_id] = {
                'session_start': timestamp,
                'project_key': project_key,
                'status': ServerStatus.RUNNING,
                'error_count': 0,
                'flow_count': 0,
                'last_seen': timestamp
            }
            
            self.project_servers[project_key][server_id] = {
                'start_time': timestamp,
                'status': ServerStatus.RUNNING,
                'last_seen': timestamp
            }

            # Initialize metrics
            SUMMARY_METRICS['project_name'].labels(serverid=server_id, projectkey=project_key).set(1)
            SUMMARY_METRICS['current_session_start'].labels(serverid=server_id, projectkey=project_key).set(timestamp)
            SUMMARY_METRICS['latest_transaction_time'].labels(serverid=server_id, projectkey=project_key).set(timestamp)
            
            self._update_server_status(server_id, project_key, ServerStatus.RUNNING)
            SUMMARY_METRICS['server_count'].labels(projectkey=project_key).set(len(self.project_servers[project_key]))

        except Exception as e:
            logger.error(f"Error updating server start: {e}")
            logger.error(traceback.format_exc())

    def _update_server_status(self, server_id, project_key, status):
        """Update server status and related metrics"""
        try:
            if server_id in self.server_sessions:
                old_status = self.server_sessions[server_id]['status']
                self.server_sessions[server_id]['status'] = status
                self.project_servers[project_key][server_id]['status'] = status

                # Reset all status values to 0 first
                for s in [ServerStatus.RUNNING, ServerStatus.STOPPED, ServerStatus.ERROR, ServerStatus.UNRESPONSIVE]:
                    SUMMARY_METRICS['server_status'].labels(serverid=server_id, projectkey=project_key, status=s).set(0)
                
                # Set the current status
                numeric_status = StatusMapping.get_numeric_status(status)
                SUMMARY_METRICS['server_status'].labels(serverid=server_id, projectkey=project_key, status=status).set(numeric_status)

                self._update_project_status(project_key)

        except Exception as e:
            logger.error(f"Error updating server status: {e}")
            logger.error(traceback.format_exc())

    def _update_project_status(self, project_key):
        """Update project status based on servers' status"""
        try:
            servers = self.project_servers[project_key]
            if not servers:
                return

            status_counts = defaultdict(int)
            for server in servers.values():
                status_counts[server['status']] += 1

            # Determine project status
            if status_counts[ServerStatus.ERROR] > 0:
                project_status = ServerStatus.ERROR
            elif status_counts[ServerStatus.RUNNING] > 0:
                project_status = ServerStatus.RUNNING
            else:
                project_status = ServerStatus.STOPPED

            # Update project status metrics
            for s in [ServerStatus.RUNNING, ServerStatus.STOPPED, ServerStatus.ERROR, ServerStatus.UNRESPONSIVE]:
                SUMMARY_METRICS['project_status'].labels(projectkey=project_key, status=s).set(0)
            
            numeric_status = StatusMapping.get_numeric_status(project_status)
            SUMMARY_METRICS['project_status'].labels(projectkey=project_key, status=project_status).set(numeric_status)

        except Exception as e:
            logger.error(f"Error updating project status: {e}")
            logger.error(traceback.format_exc())

    def _update_session_metrics(self, server_id, project_key, current_timestamp):
        """Update session-related metrics"""
        try:
            session = self.server_sessions[server_id]
            
            # Update session metrics
            SUMMARY_METRICS['total_errors_current_session'].labels(serverid=server_id, projectkey=project_key).set(session['error_count'])
            SUMMARY_METRICS['total_flows_current_session'].labels(serverid=server_id, projectkey=project_key).set(session['flow_count'])
            
            # Calculate last hour metrics
            hour_ago = current_timestamp - (60 * 60 * 1_000_000_000)  # Convert to nanoseconds
            recent_events = [e for e in self.server_history[server_id] if e['time'] > hour_ago]
            
            errors_last_hour = sum(1 for e in recent_events if e['type'] == 'error')
            flows_last_hour = sum(1 for e in recent_events if e['type'] == 'flow')
            
            SUMMARY_METRICS['errors_last_hour'].labels(serverid=server_id, projectkey=project_key).set(errors_last_hour)
            SUMMARY_METRICS['flows_last_hour'].labels(serverid=server_id, projectkey=project_key).set(flows_last_hour)

            # Update uptime
            uptime_ns = current_timestamp - session['session_start']
            uptime_sec = uptime_ns / 1_000_000_000
            
            SUMMARY_METRICS['uptime_current_session_ns'].labels(serverid=server_id, projectkey=project_key).set(uptime_ns)
            SUMMARY_METRICS['uptime_current_session_sec'].labels(serverid=server_id, projectkey=project_key).set(uptime_sec)

        except Exception as e:
            logger.error(f"Error updating session metrics: {e}")
            logger.error(traceback.format_exc())

class LokiLogReader:
    def __init__(self):
        self.loki_url = f"http://{Config.LOKI_SERVER_HOST}:{Config.LOKI_SERVER_PORT}"
        self.query_endpoint = f"{self.loki_url}/loki/api/v1/query_range"
        self.prometheus_url = Config.PROMETHEUS_GATEWAY
        self.metrics_state = MetricsState()
        logger.info(f"Initialized LokiLogReader with Loki URL: {self.loki_url}")
        logger.info(f"Using Prometheus gateway: {self.prometheus_url}")

    def process_logs(self, minutes=5):
        """
        Query and process logs from the last N minutes
        """
        end_time = datetime.now(pytz.UTC)
        start_time = end_time - timedelta(minutes=minutes)

        query = '''{app="otel-collector"} |~ `Body: Map\(` | regexp `Body: Map\((?P<body>\{.*\})\)` | line_format "{{.body}}" | json'''
        logger.debug(f"Querying logs from {start_time} to {end_time}")

        logs = self.get_logs(query, start_time.isoformat(), end_time.isoformat())
        
        processed_count = 0
        error_count = 0
        
        for log in logs:
            try:
                log_data = log['log']
                if isinstance(log_data, str):
                    log_data = json.loads(log_data)

                server_id = log_data.get('serverid')
                project_key = log_data.get('projectkey')
                msg_type = log_data.get('messagetypeid')
                timestamp = int(log['timestamp'])

                if all(v is not None for v in [server_id, project_key, msg_type]):
                    self.metrics_state.update_metrics(server_id, project_key, msg_type, timestamp)
                    processed_count += 1
                else:
                    logger.warning(f"Incomplete log data: {log_data}")

            except Exception as e:
                error_count += 1
                logger.error(f"Error processing log entry: {e}")
                continue

        # Push metrics to Prometheus
        try:
            push_to_gateway(self.prometheus_url, job=Config.PROMETHEUS_JOB_NAME, registry=REGISTRY)
            logger.info(f"Successfully pushed metrics to Prometheus. Processed: {processed_count}, Errors: {error_count}")
        except Exception as e:
            logger.error(f"Failed to push to Prometheus: {e}")

    def get_logs(self, query, start_time, end_time, limit=5000):
        """Query logs from Loki"""
        try:
            params = {
                'query': query,
                'start': start_time,
                'end': end_time,
                'limit': limit,
            }

            response = requests.get(self.query_endpoint, params=params)
            response.raise_for_status()
            data = response.json()
            
            if 'data' in data and 'result' in data['data']:
                return self._parse_results(data['data']['result'])
            return []
        
        except Exception as e:
            logger.error(f"Error querying Loki: {e}")
            return []

    def _parse_results(self, results):
        """Parse Loki results"""
        parsed_logs = []
        for stream in results:
            labels = stream.get('stream', {})
            for value in stream.get('values', []):
                timestamp, log_line = value
                try:
                    log_data = json.loads(log_line)
                except json.JSONDecodeError:
                    log_data = log_line

                parsed_logs.append({
                    'timestamp': timestamp,
                    'labels': labels,
                    'log': log_data
                })
        return parsed_logs

def main():
    try:
        logger.info("Starting Loki Reader service")
        logger.info(f"Log level: {Config.LOG_LEVEL}")
        logger.info(f"Loki Server: {Config.LOKI_SERVER_HOST}:{Config.LOKI_SERVER_PORT}")
        logger.info(f"Prometheus Gateway: {Config.PROMETHEUS_GATEWAY}")
        
        reader = LokiLogReader()
        
        # Process logs every minute
        while True:
            try:
                reader.process_logs(minutes=Config.UNRESPONSIVE_TIMEOUT_MINUTES)
                logger.info("Processed logs and updated metrics")
                time.sleep(60)  # Wait for 1 minute before next processing
            except KeyboardInterrupt:
                logger.info("Stopping log processing")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(60)  # Wait before retrying

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main() 