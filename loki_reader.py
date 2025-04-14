import os
import sys
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
    ENABLE_CONSOLE_LOG = os.getenv('ENABLE_CONSOLE_LOG', 'false').lower() == 'true'
    
    # Log file names with timestamps
    @staticmethod
    def get_log_filename(level):
        timestamp = datetime.now().strftime('%Y%m%d')
        return f'log_converter_{level}_{timestamp}.log'

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
        
        # Get root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        
        # Remove any existing handlers
        root_logger.handlers = []
        
        # Add console handler only if enabled
        if Config.ENABLE_CONSOLE_LOG:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)
        
        # Create file handlers for different log levels
        info_handler = RotatingFileHandler(
            os.path.join(Config.LOG_DIR, Config.get_log_filename('info')),
            maxBytes=Config.LOG_MAX_BYTES,
            backupCount=Config.LOG_BACKUP_COUNT
        )
        info_handler.setLevel(logging.INFO)
        info_handler.setFormatter(formatter)
        
        error_handler = RotatingFileHandler(
            os.path.join(Config.LOG_DIR, Config.get_log_filename('error')),
            maxBytes=Config.LOG_MAX_BYTES,
            backupCount=Config.LOG_BACKUP_COUNT
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        
        debug_handler = RotatingFileHandler(
            os.path.join(Config.LOG_DIR, Config.get_log_filename('debug')),
            maxBytes=Config.LOG_MAX_BYTES,
            backupCount=Config.LOG_BACKUP_COUNT
        )
        debug_handler.setLevel(logging.DEBUG)
        debug_handler.setFormatter(formatter)
        
        # Add file handlers
        root_logger.addHandler(info_handler)
        root_logger.addHandler(error_handler)
        root_logger.addHandler(debug_handler)

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
        self.project_primary_hosts = {}

    def get_earliest_active_server_start_time(self, project_key):
        """Get the earliest start time among active servers for a project"""
        try:
            logger.debug(f"Getting earliest active server start time for project {project_key}")
            active_servers = {
                server_id: details 
                for server_id, details in self.project_servers[project_key].items()
                if details.get('status') == ServerStatus.RUNNING
            }
            if not active_servers:
                logger.info(f"No active servers found for project {project_key}")
                return None
            earliest_time = min(details['start_time'] for details in active_servers.values())
            logger.debug(f"Earliest start time for project {project_key}: {earliest_time}")
            return earliest_time
        except Exception as e:
            logger.error(f"Error getting earliest active server start time for project {project_key}: {str(e)}")
            logger.debug(f"Stack trace: {traceback.format_exc()}")
            return None

    def update_metrics(self, server_id, project_key, msg_type, timestamp):
        """Update metrics based on the log entry"""
        try:
            logger.debug(f"Updating metrics for server_id={server_id}, project_key={project_key}, msg_type={msg_type}, timestamp={timestamp}")
            # Skip if we've already processed this timestamp
            if timestamp <= self.last_processed_timestamp:
                logger.debug(f"Skipping update for timestamp {timestamp} as it's already processed")
                return
            
            # Initialize server session if it doesn't exist
            if server_id not in self.server_sessions:
                self.update_server_start(server_id, project_key, timestamp)

            session = self.server_sessions[server_id]
            session['last_seen'] = timestamp
            
            # Update latest transaction time
            SUMMARY_METRICS['latest_transaction_time'].labels(serverid=server_id, projectkey=project_key).set(timestamp)
            
            # Update metrics based on message type
            message_handled = False
            current_time = time.time_ns()
            
            if msg_type == 15:  # Error message
                session['error_count'] += 1
                self.server_history[server_id].append({'type': 'error', 'time': timestamp})
                self._update_server_status(server_id, project_key, ServerStatus.ERROR)
                self.error_timestamps[server_id] = current_time
                message_handled = True
            elif msg_type == 5:  # Flow completed
                session['flow_count'] += 1
                self.server_history[server_id].append({'type': 'flow', 'time': timestamp})
                message_handled = True
            elif msg_type == 3:  # Server Stop
                self._update_server_status(server_id, project_key, ServerStatus.STOPPED)
                if server_id in self.error_timestamps:
                    del self.error_timestamps[server_id]
                message_handled = True
            elif msg_type == 1:  # Server Start
                self.update_server_start(server_id, project_key, timestamp)
                if server_id in self.error_timestamps:
                    del self.error_timestamps[server_id]
                message_handled = True
            
            if not message_handled:
                logger.warning("Received message type %d from server %s, project %s", 
                             msg_type, server_id, project_key)
            
            # Check if server should still be in ERROR state
            if session.get('status') == ServerStatus.ERROR:
                error_time = self.error_timestamps.get(server_id, 0)
                if current_time - error_time > (Config.ERROR_TIMEOUT_HOURS * 60 * 60 * 1000000000):
                    logger.info("Server %s error timeout expired after %s hours, updating to RUNNING", 
                              server_id, Config.ERROR_TIMEOUT_HOURS)
                    self._update_server_status(server_id, project_key, ServerStatus.RUNNING)
                    if server_id in self.error_timestamps:
                        del self.error_timestamps[server_id]

            # Update session metrics
            self._update_session_metrics(server_id, project_key, timestamp)
            
            # Check for unresponsive servers
            self._check_unresponsive_servers()
            
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

                # Log status transition
                if old_status != status:
                    logger.info("Server %s (Project: %s) status changed from %s to %s", 
                              server_id, project_key, old_status, status)

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

    def _check_unresponsive_servers(self):
        """Mark servers as unresponsive if they haven't sent messages in the last 5 minutes"""
        try:
            current_time = time.time_ns()
            timeout = Config.UNRESPONSIVE_TIMEOUT_MINUTES * 60 * 1_000_000_000
            reset_timeout = Config.RESET_TIMEOUT_HOURS * 60 * 60 * 1_000_000_000

            for server_id, session in self.server_sessions.items():
                time_since_last_seen = current_time - session['last_seen']
                project_key = session['project_key']
                
                # If server hasn't sent messages for more than reset timeout
                if time_since_last_seen > reset_timeout and session['status'] != ServerStatus.STOPPED:
                    logger.info("Server %s has been unresponsive for over %s hours, marking as STOPPED", 
                              server_id, Config.RESET_TIMEOUT_HOURS)
                    
                    # Only reset metrics if transitioning from UNRESPONSIVE to STOPPED
                    if session['status'] == ServerStatus.UNRESPONSIVE:
                        # Reset all metrics for this server
                        SUMMARY_METRICS['total_errors_current_session'].labels(serverid=server_id, projectkey=project_key).set(0)
                        SUMMARY_METRICS['total_flows_current_session'].labels(serverid=server_id, projectkey=project_key).set(0)
                        SUMMARY_METRICS['errors_last_hour'].labels(serverid=server_id, projectkey=project_key).set(0)
                        SUMMARY_METRICS['flows_last_hour'].labels(serverid=server_id, projectkey=project_key).set(0)
                        SUMMARY_METRICS['uptime_current_session_ns'].labels(serverid=server_id, projectkey=project_key).set(0)
                        SUMMARY_METRICS['uptime_current_session_sec'].labels(serverid=server_id, projectkey=project_key).set(0)
                        
                        # Reset session data
                        session['error_count'] = 0
                        session['flow_count'] = 0
                        session['session_start'] = current_time
                        
                        # Clear history for this server
                        self.server_history[server_id] = []
                    
                    # Update server status to STOPPED
                    self._update_server_status(server_id, project_key, ServerStatus.STOPPED)
                    
                # Regular unresponsive check
                elif time_since_last_seen > timeout and session['status'] not in [ServerStatus.STOPPED, ServerStatus.UNRESPONSIVE]:
                    logger.info("Server %s has been unresponsive for over %s minutes, marking as UNRESPONSIVE", 
                              server_id, Config.UNRESPONSIVE_TIMEOUT_MINUTES)
                    self._update_server_status(server_id, project_key, ServerStatus.UNRESPONSIVE)
        except Exception as e:
            logger.error(f"Error checking unresponsive servers: {e}")
            logger.error(traceback.format_exc())

    def _update_project_status(self, project_key):
        """Update project status based on servers' status"""
        try:
            servers = self.project_servers[project_key]
            if not servers:
                return

            # First check for unresponsive servers
            self._check_unresponsive_servers()

            status_counts = defaultdict(int)
            for server in servers.values():
                status_counts[server['status']] += 1

            total_servers = len(servers)

            # Determine project status based on the rules
            if status_counts[ServerStatus.ERROR] > 0:
                project_status = ServerStatus.ERROR
            elif status_counts[ServerStatus.RUNNING] > 0:
                project_status = ServerStatus.RUNNING
            elif status_counts[ServerStatus.STOPPED] > 0:
                project_status = ServerStatus.STOPPED
            elif status_counts[ServerStatus.UNRESPONSIVE] == total_servers:
                project_status = ServerStatus.UNRESPONSIVE
            else:
                project_status = ServerStatus.RUNNING

            # Log project status change
            old_status = self.last_project_status.get(project_key)
            if old_status != project_status:
                logger.info("Project %s status changed from %s to %s", 
                          project_key, old_status, project_status)
                logger.info("Project %s server status counts: %s", 
                          project_key, dict(status_counts))
                self.last_project_status[project_key] = project_status

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

        query = r'''{app="otel-collector"} |~ `Body: Map\(` | regexp `Body: Map\((?P<body>\{.*\})\)` | line_format "{{.body}}" | json'''
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
        """Query logs from Loki with comprehensive error handling"""
        try:
            logger.debug(f"Querying Loki with params: query={query}, start={start_time}, end={end_time}, limit={limit}")
            params = {
                'query': query,
                'start': start_time,
                'end': end_time,
                'limit': limit,
            }

            response = requests.get(self.query_endpoint, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            logger.debug(f"Successfully retrieved {len(response.content)} bytes from Loki")
            
            if 'data' in data and 'result' in data['data']:
                results = self._parse_results(data['data']['result'])
                logger.info(f"Found {len(results)} log entries")
                return results
            else:
                logger.warning("No results found in Loki response")
                return []
        
        except requests.exceptions.Timeout:
            logger.error(f"Timeout while querying Loki endpoint: {self.query_endpoint}")
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to query Loki: {str(e)}")
            logger.debug(f"Stack trace: {traceback.format_exc()}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode Loki response: {str(e)}")
            logger.debug(f"Response content: {response.content[:1000]}...")
            return []
        except Exception as e:
            logger.error(f"Unexpected error querying Loki: {str(e)}")
            logger.debug(f"Stack trace: {traceback.format_exc()}")
            return []

    def _parse_results(self, results):
        """Parse Loki results with detailed logging"""
        parsed_logs = []
        parse_errors = 0
        logger.debug(f"Parsing {len(results)} result streams")

        for stream in results:
            labels = stream.get('stream', {})
            values = stream.get('values', [])
            logger.debug(f"Processing stream with labels: {labels}, containing {len(values)} values")

            for value in values:
                try:
                    timestamp, log_line = value
                    try:
                        log_data = json.loads(log_line)
                        logger.debug(f"Successfully parsed JSON log entry at timestamp {timestamp}")
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse JSON at timestamp {timestamp}: {str(e)}")
                        log_data = log_line
                        parse_errors += 1

                    parsed_logs.append({
                        'timestamp': timestamp,
                        'labels': labels,
                        'log': log_data
                    })
                except Exception as e:
                    logger.error(f"Error processing log value: {str(e)}")
                    logger.debug(f"Problematic value: {value}")
                    parse_errors += 1
                    continue

        if parse_errors > 0:
            logger.warning(f"Encountered {parse_errors} parsing errors while processing {len(parsed_logs)} logs")
        else:
            logger.info(f"Successfully parsed {len(parsed_logs)} logs without errors")
        return parsed_logs

def main():
    try:
        logger.info("Starting Loki Reader service")
        logger.info(f"Configuration: Log level={Config.LOG_LEVEL}, Loki Server={Config.LOKI_SERVER_HOST}:{Config.LOKI_SERVER_PORT}")
        logger.info(f"Prometheus Gateway: {Config.PROMETHEUS_GATEWAY}")
        
        reader = LokiLogReader()
        consecutive_errors = 0
        max_consecutive_errors = 3
        
        # Process logs every minute
        while True:
            try:
                reader.process_logs(minutes=Config.UNRESPONSIVE_TIMEOUT_MINUTES)
                if consecutive_errors > 0:
                    logger.info(f"Successfully recovered after {consecutive_errors} errors")
                    consecutive_errors = 0
                logger.info("Completed log processing cycle")
                time.sleep(60)  # Wait for 1 minute before next processing

            except KeyboardInterrupt:
                logger.info("Received shutdown signal, stopping service...")
                break

            except Exception as e:
                consecutive_errors += 1
                logger.error(f"Error in main loop (attempt {consecutive_errors}): {str(e)}")
                logger.debug(f"Stack trace: {traceback.format_exc()}")

                if consecutive_errors >= max_consecutive_errors:
                    logger.critical(f"Service stopping after {consecutive_errors} consecutive errors")
                    sys.exit(1)

                # Exponential backoff for retries
                sleep_time = min(60 * (2 ** (consecutive_errors - 1)), 300)  # Max 5 minutes
                logger.info(f"Retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)

    except Exception as e:
        logger.critical(f"Fatal error in main process: {str(e)}")
        logger.debug(f"Stack trace: {traceback.format_exc()}")
        sys.exit(1)

if __name__ == "__main__":
    main() 