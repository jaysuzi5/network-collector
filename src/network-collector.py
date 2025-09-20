import time
import socket
import requests
import speedtest
import os
import traceback
from dotenv import load_dotenv
from jTookkit.jLogging import LoggingInfo, Logger, EventType
from jTookkit.jConfig import Config

class NetworkCollector:
    def __init__(self, config):
        self._config = config
        logging_info = LoggingInfo(**self._config.get("logging_info", {}))
        self._logger = Logger(logging_info)
        self._local_api_base_url = os.getenv("LOCAL_API_BASE_URL")
        self._transaction = None

    def process(self):
        payload = {}
        status = {}
        self._transaction = self._logger.transaction_event(EventType.TRANSACTION_START)
        payload['return_code'] = 200

        self._get_status_endpoint(status)
        self._check_dns(status)
        self._check_tcp_latency(status)
        self._collect_internet_speed(status)

        if status:
            self._load_data(status, payload)
        else:
            payload['message'] = 'Issue collecting network stats'
            payload['return_code'] = 500
        return_code = payload['return_code']
        payload.pop('return_code')
        self._logger.transaction_event(EventType.TRANSACTION_END, transaction=self._transaction,
                                       payload=payload, return_code=return_code)

    def _get_status_endpoint(self, status: dict, router_ip: str = "192.168.86.1") -> None:
        payload = {}
        return_code = 200
        source_transaction = self._logger.transaction_event(EventType.SPAN_START, payload=payload,
                                                            source_component="Network: get_status_endpoint",
                                                            transaction=self._transaction)
        try:
            response = requests.get(f"http://{router_ip}/api/v1/status", timeout=5)
            response.raise_for_status()
            json_response = response.json()
            uptime_seconds = json_response["system"]["uptime"]
            uptime_days, remainder = divmod(uptime_seconds, 86400)
            uptime_hours, remainder = divmod(remainder, 3600)
            uptime_minutes, _ = divmod(remainder, 60)
            lease_seconds = json_response['wan']['leaseDurationSeconds']
            lease_days, remainder = divmod(lease_seconds, 86400)
            lease_hours, remainder = divmod(remainder, 3600)
            lease_minutes, _ = divmod(remainder, 60)
            status["uptime_days"] = uptime_days
            status["uptime_hours"] = uptime_hours
            status["uptime_minutes"] = uptime_minutes
            status["led_status"] = json_response["system"]["ledAnimation"]
            status["online"] = json_response["wan"]["online"]
            status["ip_method"] = json_response["wan"]["ipMethod"].upper()
            status["ip_address"] = json_response["wan"]["localIpAddress"]
            status["gateway"] = json_response["wan"]["gatewayIpAddress"]
            status["local_ip_address"] = json_response["wan"]["localIpAddress"]
            status["lease_days"] = lease_days
            status["lease_hours"] = lease_hours
            status["lease_minutes"] = lease_minutes
            status["dns_servers"] = ", ".join(json_response["wan"]["nameServers"])
            status["ethernet_link"] = json_response["wan"]["ethernetLink"]
            status["update_required"] = json_response["software"]["updateRequired"]
        except Exception as ex:
            return_code= 500
            message = f"Exception with get_status_endpoint"
            payload["message"] = message
            stack_trace = traceback.format_exc()
            self._logger.message(message=message, exception=ex, stack_trace=stack_trace, transaction=source_transaction)
        self._logger.transaction_event(EventType.SPAN_END, transaction=source_transaction,
                                       payload=payload, return_code=return_code)

    def _check_dns(self, status: dict, host="kubernetes.default.svc.cluster.local") -> None:
        payload = {}
        return_code = 200
        source_transaction = self._logger.transaction_event(EventType.SPAN_START, payload=payload,
                                                            source_component="Network: check_dns",
                                                            transaction=self._transaction)
        try:
            ip = socket.gethostbyname(host)
            status['dns'] = f"{host} resolved to {ip}"
        except Exception as ex:
            return_code = 500
            message = f"Exception with check_dns"
            payload["message"] = message
            stack_trace = traceback.format_exc()
            self._logger.message(message=message, exception=ex, stack_trace=stack_trace, transaction=source_transaction)
        self._logger.transaction_event(EventType.SPAN_END, transaction=source_transaction,
                                       payload=payload, return_code=return_code)


    def _check_tcp_latency(self, status: dict, host="kubernetes.default.svc.cluster.local",
                           port=443, attempts=4) -> None:
        payload = {}
        return_code = 200
        source_transaction = self._logger.transaction_event(EventType.SPAN_START, payload=payload,
                                                            source_component="Network: check_tcp_latency",
                                                            transaction=self._transaction)
        try:
            times = []
            for _ in range(attempts):
                start = time.time()
                s = socket.create_connection((host, port), timeout=2)
                s.close()
                elapsed = (time.time() - start) * 1000  # ms
                times.append(elapsed)
            if times:
                status['tcp_latency'] = sum(times) / len(times)
        except Exception as ex:
            return_code = 500
            message = f"Exception with check_tcp_latency"
            payload["message"] = message
            stack_trace = traceback.format_exc()
            self._logger.message(message=message, exception=ex, stack_trace=stack_trace,
                                 transaction=source_transaction)
        self._logger.transaction_event(EventType.SPAN_END, transaction=source_transaction,
                                       payload=payload, return_code=return_code)

    def _collect_internet_speed(self, status: dict) -> None:
        payload = {}
        return_code = 200
        source_transaction = self._logger.transaction_event(EventType.SPAN_START, payload=payload,
                                                            source_component="Network: collect_internet_speed",
                                                            transaction=self._transaction)
        try:
            st = speedtest.Speedtest()
            st.get_best_server()
            download_speed = st.download() / 1_000_000  # Convert from bits/s to Mbps
            upload_speed = st.upload() / 1_000_000      # Convert from bits/s to Mbps
            ping_result = st.results.ping
            status['internet_download'] = download_speed
            status['internet_upload'] = upload_speed
            status['internet_ping'] = ping_result
        except Exception as ex:
            return_code = 500
            message = f"Exception with collect_internet_speed"
            payload["message"] = message
            stack_trace = traceback.format_exc()
            self._logger.message(message=message, exception=ex, stack_trace=stack_trace,
                                 transaction=source_transaction)
        self._logger.transaction_event(EventType.SPAN_END, transaction=source_transaction,
                                       payload=payload, return_code=return_code)

    def _load_data(self, data: dict, payload: dict) -> None:
        payload['return_code'] = 200
        response = None
        source_transaction = self._logger.transaction_event(EventType.SPAN_START, payload=payload,
                                                            source_component="network: Local Insert",
                                                            transaction=self._transaction)
        try:
            response = requests.post(self._local_api_base_url, json=data)
            response.raise_for_status()
            payload['inserted'] = 1
        except Exception as ex:
            payload['return_code']  = 500
            data = {}
            message = f"Exception inserting Network data locally"
            payload["message"] = message
            stack_trace = traceback.format_exc()
            if response:
                data['status_code'] = response.status_code
                data['response.text'] = response.text
            self._logger.message(message=message, exception=ex, stack_trace=stack_trace, data=data,
                                 transaction=source_transaction)
        self._logger.transaction_event(EventType.SPAN_END, transaction=source_transaction,
                                       payload=payload, return_code=payload['return_code'] )


def main():
    load_dotenv()
    config = Config()
    network = NetworkCollector(config)
    network.process()


if __name__ == "__main__":
    main()
