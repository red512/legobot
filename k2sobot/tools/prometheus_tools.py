"""
Prometheus monitoring tools for DevOps and R&D teams
Provides easy access to cluster metrics and monitoring data
"""
import os
import logging
import requests
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)

# Prometheus server URL - can be overridden by environment variable
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://localhost:9090")


def _query_prometheus(query: str, time: Optional[str] = None) -> Optional[Dict]:
    """Helper function to query Prometheus"""
    try:
        url = f"{PROMETHEUS_URL}/api/v1/query"
        params = {"query": query}
        if time:
            params["time"] = time

        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()

        if data.get("status") == "success":
            return data.get("data", {})
        else:
            logger.error(f"Prometheus query failed: {data}")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to query Prometheus: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error querying Prometheus: {e}")
        return None


def check_prometheus_health():
    """Check if Prometheus is healthy and responding"""
    try:
        response = requests.get(f"{PROMETHEUS_URL}/-/healthy", timeout=3)
        if response.status_code == 200:
            # Try to get Prometheus build info
            build_info = _query_prometheus("prometheus_build_info")
            if build_info and build_info.get("result"):
                version = build_info["result"][0]["metric"].get("version", "unknown")
                return f"✅ Prometheus is healthy! Version: {version}"
            return "✅ Prometheus is healthy and responding!"
        else:
            return f"⚠️ Prometheus returned status code: {response.status_code}"
    except requests.exceptions.RequestException:
        return "❌ Cannot connect to Prometheus. Please check if it's running."
    except Exception as e:
        return f"❌ Error checking Prometheus health: {str(e)}"


def get_resource_usage(resource_type="memory"):
    """Get current cluster resource usage (CPU or memory)"""
    if resource_type.lower() == "memory":
        query = """
        (1 - (sum(node_memory_MemAvailable_bytes) / sum(node_memory_MemTotal_bytes))) * 100
        """
        resource_name = "Memory"
    elif resource_type.lower() == "cpu":
        query = """
        (1 - avg(rate(node_cpu_seconds_total{mode="idle"}[5m]))) * 100
        """
        resource_name = "CPU"
    else:
        return f"❌ Unknown resource type: {resource_type}. Use 'cpu' or 'memory'."

    result = _query_prometheus(query)
    if result and result.get("result"):
        try:
            value = float(result["result"][0]["value"][1])
            return f"📊 Cluster {resource_name} Usage: {value:.1f}%"
        except (KeyError, IndexError, ValueError):
            return f"⚠️ Could not parse {resource_name.lower()} usage data"
    return f"❌ No {resource_name.lower()} usage data available"


def get_top_pods_by_resource(resource="memory", limit=5):
    """Get top pods by resource consumption"""
    if resource.lower() == "memory":
        query = """
        topk(%d,
            sum(container_memory_working_set_bytes{pod!=""}) by (namespace, pod)
        )
        """ % limit
        unit = "bytes"
        resource_name = "Memory"
    elif resource.lower() == "cpu":
        query = """
        topk(%d,
            sum(rate(container_cpu_usage_seconds_total{pod!=""}[5m])) by (namespace, pod)
        )
        """ % limit
        unit = "cores"
        resource_name = "CPU"
    else:
        return f"❌ Unknown resource: {resource}. Use 'cpu' or 'memory'."

    result = _query_prometheus(query)
    if not result or not result.get("result"):
        return f"❌ No {resource_name.lower()} usage data available"

    output = [f"🏆 Top {limit} Pods by {resource_name} Usage:"]
    output.append("")

    for i, item in enumerate(result["result"], 1):
        namespace = item["metric"].get("namespace", "unknown")
        pod = item["metric"].get("pod", "unknown")
        value = float(item["value"][1])

        if resource.lower() == "memory":
            # Convert bytes to human readable
            value_str = _format_bytes(value)
        else:
            value_str = f"{value:.3f} {unit}"

        output.append(f"{i}. {namespace}/{pod}: {value_str}")

    return "\n".join(output)


def check_pod_restarts(namespace="all", threshold=5):
    """Check for pods with high restart counts"""
    if namespace == "all":
        query = f"""
        kube_pod_container_status_restarts_total > {threshold}
        """
    else:
        query = f"""
        kube_pod_container_status_restarts_total{{namespace="{namespace}"}} > {threshold}
        """

    result = _query_prometheus(query)
    if not result or not result.get("result"):
        return f"✅ No pods with more than {threshold} restarts found"

    output = [f"⚠️ Pods with more than {threshold} restarts:"]
    output.append("")

    for item in result["result"]:
        namespace = item["metric"].get("namespace", "unknown")
        pod = item["metric"].get("pod", "unknown")
        container = item["metric"].get("container", "unknown")
        restarts = int(float(item["value"][1]))
        output.append(f"• {namespace}/{pod} ({container}): {restarts} restarts")

    return "\n".join(output)


def get_namespace_metrics(namespace="default"):
    """Get resource usage summary for a namespace"""
    output = [f"📊 Namespace Metrics: {namespace}"]
    output.append("")

    # CPU usage
    cpu_query = f"""
    sum(rate(container_cpu_usage_seconds_total{{namespace="{namespace}"}}[5m]))
    """
    cpu_result = _query_prometheus(cpu_query)
    if cpu_result and cpu_result.get("result"):
        cpu_cores = float(cpu_result["result"][0]["value"][1])
        output.append(f"CPU: {cpu_cores:.3f} cores")

    # Memory usage
    mem_query = f"""
    sum(container_memory_working_set_bytes{{namespace="{namespace}"}})
    """
    mem_result = _query_prometheus(mem_query)
    if mem_result and mem_result.get("result"):
        mem_bytes = float(mem_result["result"][0]["value"][1])
        output.append(f"Memory: {_format_bytes(mem_bytes)}")

    # Pod count
    pod_query = f"""
    count(kube_pod_info{{namespace="{namespace}"}})
    """
    pod_result = _query_prometheus(pod_query)
    if pod_result and pod_result.get("result"):
        pod_count = int(float(pod_result["result"][0]["value"][1]))
        output.append(f"Pods: {pod_count}")

    # Container count
    container_query = f"""
    count(kube_pod_container_info{{namespace="{namespace}"}})
    """
    container_result = _query_prometheus(container_query)
    if container_result and container_result.get("result"):
        container_count = int(float(container_result["result"][0]["value"][1]))
        output.append(f"Containers: {container_count}")

    if len(output) == 2:  # Only header and empty line
        return f"❌ No metrics available for namespace: {namespace}"

    return "\n".join(output)


def check_node_health():
    """Check for nodes under pressure or with issues"""
    output = []
    issues_found = False

    # Check memory pressure
    mem_pressure_query = """
    kube_node_status_condition{condition="MemoryPressure", status="true"} == 1
    """
    mem_result = _query_prometheus(mem_pressure_query)
    if mem_result and mem_result.get("result"):
        if not issues_found:
            output.append("⚠️ Node Health Issues:")
            output.append("")
            issues_found = True
        output.append("Memory Pressure:")
        for item in mem_result["result"]:
            node = item["metric"].get("node", "unknown")
            output.append(f"  • {node}")

    # Check disk pressure
    disk_pressure_query = """
    kube_node_status_condition{condition="DiskPressure", status="true"} == 1
    """
    disk_result = _query_prometheus(disk_pressure_query)
    if disk_result and disk_result.get("result"):
        if not issues_found:
            output.append("⚠️ Node Health Issues:")
            output.append("")
            issues_found = True
        output.append("Disk Pressure:")
        for item in disk_result["result"]:
            node = item["metric"].get("node", "unknown")
            output.append(f"  • {node}")

    # Check not ready nodes
    not_ready_query = """
    kube_node_status_condition{condition="Ready", status="false"} == 1
    """
    not_ready_result = _query_prometheus(not_ready_query)
    if not_ready_result and not_ready_result.get("result"):
        if not issues_found:
            output.append("⚠️ Node Health Issues:")
            output.append("")
            issues_found = True
        output.append("Not Ready:")
        for item in not_ready_result["result"]:
            node = item["metric"].get("node", "unknown")
            output.append(f"  • {node}")

    if not issues_found:
        # Get node count for confirmation
        node_count_query = "count(kube_node_info)"
        count_result = _query_prometheus(node_count_query)
        if count_result and count_result.get("result"):
            count = int(float(count_result["result"][0]["value"][1]))
            return f"✅ All {count} nodes are healthy!"
        return "✅ All nodes appear healthy!"

    return "\n".join(output)


def get_service_response_time(service_name, percentile=95):
    """Get response time for a service (requires service to export http_request_duration metrics)"""
    query = f"""
    histogram_quantile({percentile/100},
        sum(rate(http_request_duration_seconds_bucket{{service="{service_name}"}}[5m])) by (le)
    )
    """

    result = _query_prometheus(query)
    if result and result.get("result"):
        try:
            response_time_sec = float(result["result"][0]["value"][1])
            response_time_ms = response_time_sec * 1000
            return f"📈 {service_name} p{percentile} response time: {response_time_ms:.1f}ms"
        except (KeyError, IndexError, ValueError):
            pass

    # Try alternative metric names
    alt_query = f"""
    histogram_quantile({percentile/100},
        sum(rate(http_server_request_duration_seconds_bucket{{service="{service_name}"}}[5m])) by (le)
    )
    """
    result = _query_prometheus(alt_query)
    if result and result.get("result"):
        try:
            response_time_sec = float(result["result"][0]["value"][1])
            response_time_ms = response_time_sec * 1000
            return f"📈 {service_name} p{percentile} response time: {response_time_ms:.1f}ms"
        except (KeyError, IndexError, ValueError):
            pass

    return f"❌ No response time metrics available for service: {service_name}"


def get_error_rate(service_name=None, time_range="5m"):
    """Get error rate for services (5xx responses)"""
    if service_name:
        query = f"""
        sum(rate(http_requests_total{{service="{service_name}", status=~"5.."}}[{time_range}])) /
        sum(rate(http_requests_total{{service="{service_name}"}}[{time_range}])) * 100
        """
        scope = f"service '{service_name}'"
    else:
        query = f"""
        sum(rate(http_requests_total{{status=~"5.."}}[{time_range}])) /
        sum(rate(http_requests_total[{time_range}])) * 100
        """
        scope = "cluster-wide"

    result = _query_prometheus(query)
    if result and result.get("result"):
        try:
            error_rate = float(result["result"][0]["value"][1])
            if error_rate > 5:
                emoji = "🔴"
            elif error_rate > 1:
                emoji = "🟡"
            else:
                emoji = "🟢"
            return f"{emoji} Error rate ({scope}): {error_rate:.2f}% over {time_range}"
        except (KeyError, IndexError, ValueError):
            pass

    return f"❌ No error rate data available for {scope}"


def _format_bytes(bytes_value):
    """Helper function to format bytes to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.1f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.1f} PB"