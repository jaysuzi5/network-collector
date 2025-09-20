import socket
import json
import requests
import speedtest
import subprocess


def get_status_endpoint() -> dict:
    router_ip = "192.168.86.1"
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

        status = {
            "uptime_days": uptime_days,
            "uptime_hours": uptime_hours,
            "uptime_minutes": uptime_minutes,
            "led_status": json_response["system"]["ledAnimation"],
            "online": json_response["wan"]["online"],
            "ip_method": json_response["wan"]["ipMethod"].upper(),
            "ip_address": json_response["wan"]["localIpAddress"],
            "gateway": json_response["wan"]["gatewayIpAddress"],
            "local_ip_address": json_response["wan"]["localIpAddress"],
            "lease_days": lease_days,
            "lease_hours": lease_hours,
            "lease_minutes": lease_minutes,
            "dns_servers": ", ".join(json_response["wan"]["nameServers"]),
            "ethernet_link": json_response["wan"]["ethernetLink"],
            "update_required": json_response["software"]["updateRequired"]
        }
    except requests.exceptions.HTTPError as ex:
        status = {
            "Error": ex
        }
    except requests.exceptions.RequestException as ex:
        status = {
            "Error": ex
        }

    return status

def check_dns(host="kubernetes.default.svc.cluster.local"):
    print("🔍 DNS Resolution Test")
    try:
        ip = socket.gethostbyname(host)
        print(f"✅ {host} resolved to {ip}")
        return True
    except Exception as e:
        print(f"❌ DNS resolution failed for {host}: {e}")
        return False


def check_latency(host="kubernetes.default.svc.cluster.local", count=4):
    print("\n📡 Latency Test (ping)")
    try:
        result = subprocess.run(
            ["ping", "-c", str(count), host],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print("✅ Ping successful:")
            print(result.stdout)
            return True
        else:
            print("❌ Ping failed:")
            print(result.stderr)
            return False
    except FileNotFoundError:
        print("⚠️ 'ping' not installed in container")
        return False


def check_throughput(server="iperf-server", duration=5):
    print("\n🚀 Throughput Test (iperf3)")
    try:
        result = subprocess.run(
            ["iperf3", "-c", server, "-J", "-t", str(duration)],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            bps = data['end']['sum_received']['bits_per_second']
            print(f"✅ Download: {bps / 1e6:.2f} Mbps")
            return True
        else:
            print("❌ iperf3 test failed:")
            print(result.stderr)
            return False
    except FileNotFoundError:
        print("⚠️ iperf3 not installed in container")
        return False


if __name__ == "__main__":
    print("=== Kubernetes Network Health Check ===\n")
    check_dns()
    check_latency()
    # Requires an iperf3 server pod (see instructions below)
    # check_throughput("iperf-server")



def collect_internet_speed():
    st = speedtest.Speedtest()

    print("Finding best server...")
    st.get_best_server()

    print("Measuring download speed...")
    download_speed = st.download() / 1_000_000  # Convert from bits/s to Mbps
    print("Measuring upload speed...")
    upload_speed = st.upload() / 1_000_000      # Convert from bits/s to Mbps
    ping_result = st.results.ping

    status = {
        'download': download_speed,
        'upload': upload_speed,
        'ping': ping_result
    }
    return status


def main():
    print('------------------------------------------------')
    print('get_status')
    print('------------------------------------------------')
    status = get_status_endpoint()
    print(status)
    print('------------------------------------------------')
    print('check dns')
    print('------------------------------------------------')
    status = check_dns()
    print(status)
    print('------------------------------------------------')
    print('check througput')
    print('------------------------------------------------')
    status = check_throughput()
    print(status)
    print('------------------------------------------------')
    print('check latency')
    print('------------------------------------------------')
    status = check_latency()
    print(status)
    print('------------------------------------------------')
    print('internet')
    print('------------------------------------------------')
    status = collect_internet_speed()
    print(status)
    print('------------------------------------------------')

if __name__ == "__main__":
    main()

