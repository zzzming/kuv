#!/usr/bin/env python3

import asyncio
import time
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, DataTable, Static, Label
from textual.reactive import reactive
from textual.binding import Binding
from rich.text import Text
from rich.console import Console

from kubernetes import client, config
from kubernetes.client.rest import ApiException


@dataclass
class NodeInfo:
    name: str
    ready: bool
    status: str
    roles: List[str]
    age: str
    version: str
    zone: Optional[str]
    node_group: Optional[str]
    instance_type: Optional[str]
    cpu_capacity: float
    memory_capacity: float
    cpu_allocatable: float
    memory_allocatable: float
    cpu_requests: float
    memory_requests: float
    cpu_limits: float
    memory_limits: float
    cpu_usage: Optional[float] = None
    memory_usage: Optional[float] = None


@dataclass
class PodInfo:
    name: str
    namespace: str
    ready: str
    status: str
    restarts: int
    age: str
    ip: str
    node: str
    cpu_requests: float
    memory_requests: float
    cpu_limits: float
    memory_limits: float
    cpu_usage: Optional[float] = None
    memory_usage: Optional[float] = None


class KubernetesClient:
    def __init__(self):
        try:
            config.load_kube_config()
            self.v1 = client.CoreV1Api()
            self.metrics_v1beta1 = client.CustomObjectsApi()
        except Exception as e:
            raise Exception(f"Failed to load kubeconfig: {e}")

    def parse_quantity(self, quantity: str) -> float:
        """Parse Kubernetes quantity strings to float values"""
        if not quantity:
            return 0.0

        units = {
            'Ki': 1024, 'Mi': 1024**2, 'Gi': 1024**3, 'Ti': 1024**4,
            'K': 1000, 'M': 1000**2, 'G': 1000**3, 'T': 1000**4,
            'm': 0.001, 'u': 0.000001, 'n': 0.000000001
        }

        # Handle CPU millicores
        if quantity.endswith('m') and quantity[:-1].isdigit():
            return float(quantity[:-1]) * 0.001

        # Handle memory units
        for unit, multiplier in units.items():
            if quantity.endswith(unit):
                return float(quantity[:-len(unit)]) * multiplier

        # Plain number
        try:
            return float(quantity)
        except ValueError:
            return 0.0

    def get_age(self, timestamp) -> str:
        """Calculate age from timestamp"""
        if not timestamp:
            return "Unknown"
        
        now = datetime.now(timezone.utc)
        created = timestamp.replace(tzinfo=timezone.utc)
        diff = now - created
        
        days = diff.days
        hours = diff.seconds // 3600
        minutes = (diff.seconds % 3600) // 60
        
        if days > 0:
            return f"{days}d"
        elif hours > 0:
            return f"{hours}h"
        else:
            return f"{minutes}m"

    async def get_nodes(self) -> List[NodeInfo]:
        """Fetch node information"""
        try:
            nodes_response = self.v1.list_node()
            pods_response = self.v1.list_pod_for_all_namespaces()
            
            # Try to get node metrics
            node_metrics = {}
            try:
                metrics_response = self.metrics_v1beta1.list_cluster_custom_object(
                    group="metrics.k8s.io",
                    version="v1beta1",
                    plural="nodes"
                )
                for item in metrics_response.get('items', []):
                    node_name = item['metadata']['name']
                    usage = item['usage']
                    node_metrics[node_name] = {
                        'cpu': self.parse_quantity(usage.get('cpu', '0')),
                        'memory': self.parse_quantity(usage.get('memory', '0'))
                    }
            except Exception:
                pass  # Metrics server might not be available

            nodes = []
            for node in nodes_response.items:
                # Calculate pod resources on this node
                node_pods = [pod for pod in pods_response.items 
                           if pod.spec.node_name == node.metadata.name]
                
                cpu_requests = cpu_limits = memory_requests = memory_limits = 0.0
                for pod in node_pods:
                    if pod.spec.containers:
                        for container in pod.spec.containers:
                            if container.resources:
                                if container.resources.requests:
                                    cpu_requests += self.parse_quantity(
                                        container.resources.requests.get('cpu', '0'))
                                    memory_requests += self.parse_quantity(
                                        container.resources.requests.get('memory', '0'))
                                if container.resources.limits:
                                    cpu_limits += self.parse_quantity(
                                        container.resources.limits.get('cpu', '0'))
                                    memory_limits += self.parse_quantity(
                                        container.resources.limits.get('memory', '0'))

                # Node status
                ready = False
                for condition in node.status.conditions or []:
                    if condition.type == "Ready" and condition.status == "True":
                        ready = True
                        break

                # Node roles
                roles = []
                if node.metadata.labels:
                    for label in node.metadata.labels:
                        if label.startswith('node-role.kubernetes.io/'):
                            role = label.split('/')[-1]
                            if role:
                                roles.append(role)

                node_info = NodeInfo(
                    name=node.metadata.name,
                    ready=ready,
                    status="Ready" if ready else "NotReady",
                    roles=roles or ["worker"],
                    age=self.get_age(node.metadata.creation_timestamp),
                    version=node.status.node_info.kubelet_version if node.status.node_info else "Unknown",
                    zone=node.metadata.labels.get('topology.kubernetes.io/zone') if node.metadata.labels else None,
                    node_group=node.metadata.labels.get('eks.amazonaws.com/nodegroup') if node.metadata.labels else None,
                    instance_type=node.metadata.labels.get('node.kubernetes.io/instance-type') if node.metadata.labels else None,
                    cpu_capacity=self.parse_quantity(node.status.capacity.get('cpu', '0') if node.status.capacity else '0'),
                    memory_capacity=self.parse_quantity(node.status.capacity.get('memory', '0') if node.status.capacity else '0'),
                    cpu_allocatable=self.parse_quantity(node.status.allocatable.get('cpu', '0') if node.status.allocatable else '0'),
                    memory_allocatable=self.parse_quantity(node.status.allocatable.get('memory', '0') if node.status.allocatable else '0'),
                    cpu_requests=cpu_requests,
                    memory_requests=memory_requests,
                    cpu_limits=cpu_limits,
                    memory_limits=memory_limits,
                    cpu_usage=node_metrics.get(node.metadata.name, {}).get('cpu'),
                    memory_usage=node_metrics.get(node.metadata.name, {}).get('memory')
                )
                nodes.append(node_info)

            return nodes

        except ApiException as e:
            raise Exception(f"Kubernetes API error: {e}")

    async def get_pods_for_node(self, node_name: str) -> List[PodInfo]:
        """Fetch pods for a specific node"""
        try:
            pods_response = self.v1.list_pod_for_all_namespaces(
                field_selector=f"spec.nodeName={node_name}"
            )

            # Try to get pod metrics
            pod_metrics = {}
            try:
                metrics_response = self.metrics_v1beta1.list_namespaced_custom_object(
                    group="metrics.k8s.io",
                    version="v1beta1",
                    namespace="",
                    plural="pods"
                )
                for item in metrics_response.get('items', []):
                    pod_key = f"{item['metadata']['namespace']}/{item['metadata']['name']}"
                    total_cpu = total_memory = 0.0
                    for container in item.get('containers', []):
                        usage = container.get('usage', {})
                        total_cpu += self.parse_quantity(usage.get('cpu', '0'))
                        total_memory += self.parse_quantity(usage.get('memory', '0'))
                    pod_metrics[pod_key] = {
                        'cpu': total_cpu,
                        'memory': total_memory
                    }
            except Exception:
                pass

            pods = []
            for pod in pods_response.items:
                # Calculate resource requests/limits
                cpu_requests = cpu_limits = memory_requests = memory_limits = 0.0
                if pod.spec.containers:
                    for container in pod.spec.containers:
                        if container.resources:
                            if container.resources.requests:
                                cpu_requests += self.parse_quantity(
                                    container.resources.requests.get('cpu', '0'))
                                memory_requests += self.parse_quantity(
                                    container.resources.requests.get('memory', '0'))
                            if container.resources.limits:
                                cpu_limits += self.parse_quantity(
                                    container.resources.limits.get('cpu', '0'))
                                memory_limits += self.parse_quantity(
                                    container.resources.limits.get('memory', '0'))

                # Ready status
                ready_containers = 0
                total_containers = len(pod.spec.containers) if pod.spec.containers else 0
                if pod.status.container_statuses:
                    ready_containers = sum(1 for cs in pod.status.container_statuses if cs.ready)

                # Restart count
                restarts = 0
                if pod.status.container_statuses:
                    restarts = sum(cs.restart_count for cs in pod.status.container_statuses)

                pod_key = f"{pod.metadata.namespace}/{pod.metadata.name}"
                metrics = pod_metrics.get(pod_key, {})

                pod_info = PodInfo(
                    name=pod.metadata.name,
                    namespace=pod.metadata.namespace,
                    ready=f"{ready_containers}/{total_containers}",
                    status=pod.status.phase or "Unknown",
                    restarts=restarts,
                    age=self.get_age(pod.metadata.creation_timestamp),
                    ip=pod.status.pod_ip or "None",
                    node=pod.spec.node_name or "None",
                    cpu_requests=cpu_requests,
                    memory_requests=memory_requests,
                    cpu_limits=cpu_limits,
                    memory_limits=memory_limits,
                    cpu_usage=metrics.get('cpu'),
                    memory_usage=metrics.get('memory')
                )
                pods.append(pod_info)

            return pods

        except ApiException as e:
            raise Exception(f"Kubernetes API error: {e}")


class NodeTable(DataTable):
    """Table widget for displaying nodes"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cursor_type = "row"
        self.zebra_stripes = True
        
    def on_mount(self) -> None:
        self.add_columns(
            "Name", "Status", "Role", "Age", "Version", 
            "CPU Req", "CPU %", "Mem Req", "Mem %", "Zone"
        )


class PodTable(DataTable):
    """Table widget for displaying pods"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cursor_type = "row"
        self.zebra_stripes = True
        
    def on_mount(self) -> None:
        self.add_columns(
            "Name", "Namespace", "Ready", "Status", "Restarts", 
            "Age", "CPU Req", "Mem Req", "IP"
        )


class KUVApp(App):
    """Kubernetes Usage Viewer TUI Application"""
    
    CSS = """
    Screen {
        layout: grid;
        grid-size: 1 4;
        grid-rows: 3 18 14 3;
    }
    
    .header {
        background: $primary;
        color: $text;
        content-align: center middle;
    }
    
    .nodes {
        background: $surface;
        border: solid $primary;
        height: 100%;
    }
    
    .pods {
        background: $surface;
        border: solid $primary;
        height: 100%;
    }
    
    .status {
        background: $surface;
        border: solid $primary;
        content-align: center middle;
    }
    
    DataTable {
        height: 100%;
        scrollbar-size: 1 1;
        scrollbar-size-horizontal: 1;
        scrollbar-size-vertical: 1;
    }
    
    #nodes-title {
        height: 1;
        content-align: left middle;
        padding: 0 1;
        background: $surface;
    }
    
    #pods-title {
        height: 1;
        content-align: left middle;
        padding: 0 1;
        background: $surface;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("s", "sort_next", "Sort"),
        Binding("d", "select_node", "Details"),
        Binding("1", "sort_name", "Sort Name"),
        Binding("2", "sort_cpu_percent", "Sort CPU%"),
        Binding("3", "sort_mem_percent", "Sort Mem%"),
        Binding("4", "sort_cpu_requests", "Sort CPU Req"),
        Binding("5", "sort_mem_requests", "Sort Mem Req"),
        Binding("pageup", "page_up", "Page Up"),
        Binding("pagedown", "page_down", "Page Down"),
        Binding("home", "go_home", "Top"),
        Binding("end", "go_end", "Bottom"),
        Binding("a", "toggle_auto_refresh", "Auto-refresh"),
    ]

    nodes: reactive[List[NodeInfo]] = reactive(list)
    selected_node: reactive[Optional[NodeInfo]] = reactive(None)
    pods: reactive[List[PodInfo]] = reactive(list)
    status_text: reactive[str] = reactive("Initializing...")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.k8s_client = None
        self.sort_column = "name"
        self.sort_reverse = False
        self.sort_options = ["name", "cpu_percent", "mem_percent", "cpu_requests", "mem_requests"]
        self.current_sort_index = 0
        self.auto_refresh_enabled = True
        self.refresh_timer = None

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        
        with Container(classes="header"):
            yield Static("Kubernetes Usage Viewer (KUV) - Node Utilization Monitor", id="title")
            
        with Container(classes="nodes"):
            yield Static("Nodes", id="nodes-title")
            yield NodeTable(id="node-table")
            
        with Container(classes="pods"):
            yield Static("Pods", id="pods-title")
            yield PodTable(id="pod-table")
            
        with Container(classes="status"):
            yield Static("Initializing...", id="status")
            
        yield Footer()

    async def on_mount(self) -> None:
        """Initialize the application"""
        try:
            self.update_status("Connecting to Kubernetes...")
            self.k8s_client = KubernetesClient()
            self.update_status("Connected to Kubernetes")
            await self.refresh_data()
            # Start auto-refresh timer
            if self.auto_refresh_enabled:
                self.refresh_timer = self.set_interval(8.0, self.auto_refresh)
        except Exception as e:
            self.update_status(f"Error: {e}")

    async def auto_refresh(self) -> None:
        """Auto-refresh data every 8 seconds"""
        if self.auto_refresh_enabled:
            await self.refresh_data(auto=True)

    async def refresh_data(self, auto: bool = False) -> None:
        """Refresh node and pod data"""
        if not self.k8s_client:
            return
            
        try:
            refresh_type = "Auto-refreshing" if auto else "Refreshing"
            self.update_status(f"{refresh_type} data...")
            self.nodes = await self.k8s_client.get_nodes()
            self.update_node_table()
            
            if self.selected_node:
                self.pods = await self.k8s_client.get_pods_for_node(self.selected_node.name)
                self.update_pod_table()
                
            node_table = self.query_one("#node-table", NodeTable)
            current_row = node_table.cursor_row + 1 if node_table.cursor_row >= 0 else 0
            auto_indicator = " [AUTO]" if self.auto_refresh_enabled else ""
            self.update_status(f"Updated: {datetime.now().strftime('%H:%M:%S')} | Nodes: {current_row}/{len(self.nodes)} | Pods: {len(self.pods)} | Sort: {self.sort_column.replace('_', ' ').title()}{auto_indicator}")
        except Exception as e:
            self.update_status(f"Error: {e}")

    async def action_refresh(self) -> None:
        """Manual refresh data"""
        await self.refresh_data()

    def update_status(self, message: str) -> None:
        """Update the status bar"""
        try:
            status_widget = self.query_one("#status", Static)
            status_widget.update(message)
            self.status_text = message
        except Exception:
            self.status_text = message

    def update_node_table(self) -> None:
        """Update the node table with current data"""
        table = self.query_one("#node-table", NodeTable)
        table.clear()
        
        # Sort nodes based on current sort column
        def sort_key(node):
            if self.sort_column == "name":
                return node.name
            elif self.sort_column == "cpu_percent":
                return (node.cpu_requests / node.cpu_allocatable * 100) if node.cpu_allocatable > 0 else 0
            elif self.sort_column == "mem_percent":
                return (node.memory_requests / node.memory_allocatable * 100) if node.memory_allocatable > 0 else 0
            elif self.sort_column == "cpu_requests":
                return node.cpu_requests
            elif self.sort_column == "mem_requests":
                return node.memory_requests
            else:
                return node.name
        
        sorted_nodes = sorted(self.nodes, key=sort_key, reverse=self.sort_reverse)
        
        for node in sorted_nodes:
            cpu_percent = (node.cpu_requests / node.cpu_allocatable * 100) if node.cpu_allocatable > 0 else 0
            mem_percent = (node.memory_requests / node.memory_allocatable * 100) if node.memory_allocatable > 0 else 0
            
            # Format values
            cpu_req = f"{node.cpu_requests:.1f}" if node.cpu_requests >= 1 else f"{node.cpu_requests*1000:.0f}m"
            mem_req = self.format_bytes(node.memory_requests)
            
            # Color coding for utilization
            cpu_color = "green" if cpu_percent < 50 else "yellow" if cpu_percent < 80 else "red"
            mem_color = "green" if mem_percent < 50 else "yellow" if mem_percent < 80 else "red"
            
            table.add_row(
                node.name,
                Text(node.status, style="green" if node.ready else "red"),
                ", ".join(node.roles),
                node.age,
                node.version,
                cpu_req,
                Text(f"{cpu_percent:.1f}%", style=cpu_color),
                mem_req,
                Text(f"{mem_percent:.1f}%", style=mem_color),
                node.zone or "Unknown"
            )

    def update_pod_table(self) -> None:
        """Update the pod table with current data"""
        table = self.query_one("#pod-table", PodTable)
        table.clear()
        
        for pod in self.pods:
            cpu_req = f"{pod.cpu_requests:.1f}" if pod.cpu_requests >= 1 else f"{pod.cpu_requests*1000:.0f}m"
            mem_req = self.format_bytes(pod.memory_requests)
            
            status_color = {
                "Running": "green",
                "Pending": "yellow", 
                "Failed": "red",
                "Succeeded": "blue"
            }.get(pod.status, "white")
            
            table.add_row(
                pod.name,
                pod.namespace,
                pod.ready,
                Text(pod.status, style=status_color),
                str(pod.restarts),
                pod.age,
                cpu_req,
                mem_req,
                pod.ip
            )

    def format_bytes(self, bytes_val: float) -> str:
        """Format bytes to human readable format"""
        if bytes_val == 0:
            return "0B"
        
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        size = bytes_val
        unit_index = 0
        
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
            
        return f"{size:.1f}{units[unit_index]}"

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle node selection"""
        # Update status to show selection is working
        self.update_status(f"Selected row {event.cursor_row} in table {event.data_table.id}")
        
        if event.data_table.id == "node-table" and self.nodes and event.cursor_row < len(self.nodes):
            selected_node = self.nodes[event.cursor_row]
            self.selected_node = selected_node
            
            # Update pods title
            pods_title = self.query_one("#pods-title", Static)
            pods_title.update(f"Pods on {selected_node.name}")
            
            # Update status
            self.update_status(f"Loading pods for {selected_node.name}...")
            
            # Fetch pods for selected node - run async task
            self.run_worker(self.fetch_pods_for_selected_node(selected_node.name))

    async def fetch_pods_for_selected_node(self, node_name: str) -> None:
        """Fetch pods for selected node"""
        try:
            self.pods = await self.k8s_client.get_pods_for_node(node_name)
            self.update_pod_table()
        except Exception as e:
            self.status_text = f"Error fetching pods: {e}"

    async def action_refresh(self) -> None:
        """Refresh data"""
        await self.refresh_data()

    def action_quit(self) -> None:
        """Quit the application"""
        self.exit()

    def action_sort_next(self) -> None:
        """Cycle through sort options"""
        self.current_sort_index = (self.current_sort_index + 1) % len(self.sort_options)
        self.sort_column = self.sort_options[self.current_sort_index]
        self.sort_reverse = False  # Reset to ascending when changing column
        self.status_text = f"Sorting by {self.sort_column.replace('_', ' ').title()}"
        self.update_node_table()

    def action_sort_name(self) -> None:
        """Sort by node name"""
        if self.sort_column == "name":
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = "name"
            self.sort_reverse = False
        self.status_text = f"Sorting by Name ({'Desc' if self.sort_reverse else 'Asc'})"
        self.update_node_table()

    def action_sort_cpu_percent(self) -> None:
        """Sort by CPU percentage"""
        if self.sort_column == "cpu_percent":
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = "cpu_percent"
            self.sort_reverse = True  # Default to descending for utilization
        self.status_text = f"Sorting by CPU% ({'Desc' if self.sort_reverse else 'Asc'})"
        self.update_node_table()

    def action_sort_mem_percent(self) -> None:
        """Sort by Memory percentage"""
        if self.sort_column == "mem_percent":
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = "mem_percent"
            self.sort_reverse = True  # Default to descending for utilization
        self.status_text = f"Sorting by Memory% ({'Desc' if self.sort_reverse else 'Asc'})"
        self.update_node_table()

    def action_sort_cpu_requests(self) -> None:
        """Sort by CPU requests"""
        if self.sort_column == "cpu_requests":
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = "cpu_requests"
            self.sort_reverse = True  # Default to descending for requests
        self.status_text = f"Sorting by CPU Requests ({'Desc' if self.sort_reverse else 'Asc'})"
        self.update_node_table()

    def action_sort_mem_requests(self) -> None:
        """Sort by Memory requests"""
        if self.sort_column == "mem_requests":
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = "mem_requests"
            self.sort_reverse = True  # Default to descending for requests
        self.status_text = f"Sorting by Memory Requests ({'Desc' if self.sort_reverse else 'Asc'})"
        self.update_node_table()

    def action_select_node(self) -> None:
        """Select the currently highlighted node to show its pods"""
        node_table = self.query_one("#node-table", NodeTable)
        if node_table.cursor_row >= 0 and self.nodes and node_table.cursor_row < len(self.nodes):
            selected_node = self.nodes[node_table.cursor_row]
            self.selected_node = selected_node
            
            # Update pods title
            pods_title = self.query_one("#pods-title", Static)
            pods_title.update(f"Pods on {selected_node.name}")
            
            # Update status
            self.status_text = f"Loading pods for {selected_node.name}..."
            
            # Fetch pods for selected node - run async task
            self.run_worker(self.fetch_pods_for_selected_node(selected_node.name))
        else:
            self.status_text = "No node selected. Use arrow keys to highlight a node first."

    def action_page_up(self) -> None:
        """Scroll page up in node table"""
        node_table = self.query_one("#node-table", NodeTable)
        node_table.action_page_up()

    def action_page_down(self) -> None:
        """Scroll page down in node table"""
        node_table = self.query_one("#node-table", NodeTable)
        node_table.action_page_down()

    def action_go_home(self) -> None:
        """Jump to top of node table"""
        node_table = self.query_one("#node-table", NodeTable)
        if node_table.row_count > 0:
            node_table.cursor_row = 0

    def action_go_end(self) -> None:
        """Jump to bottom of node table"""
        node_table = self.query_one("#node-table", NodeTable)
        if node_table.row_count > 0:
            node_table.cursor_row = node_table.row_count - 1

    def action_toggle_auto_refresh(self) -> None:
        """Toggle auto-refresh on/off"""
        self.auto_refresh_enabled = not self.auto_refresh_enabled
        
        if self.auto_refresh_enabled:
            # Start auto refresh
            self.refresh_timer = self.set_interval(8.0, self.auto_refresh)
            self.update_status("Auto-refresh enabled (8s interval)")
        else:
            # Stop auto refresh
            if self.refresh_timer:
                self.refresh_timer.stop()
                self.refresh_timer = None
            self.update_status("Auto-refresh disabled")


def main():
    """Main entry point"""
    app = KUVApp()
    app.run()


if __name__ == "__main__":
    main()