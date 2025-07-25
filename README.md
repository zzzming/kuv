# KUV - Kubernetes Usage Viewer

A powerful terminal-based UI for monitoring Kubernetes node utilization, similar to k9s but specifically designed for resource optimization. KUV helps cluster administrators quickly identify under-utilized nodes, optimize resource allocation, and reduce infrastructure costs.

## Key Features

### 🖥️ **Modern Terminal Interface**
- **Clean multi-pane layout** with nodes (top) and pods (bottom) for optimal column visibility
- **Responsive design** that adapts to terminal size
- **15 visible nodes** and **10 visible pods** by default with smooth scrolling
- **Professional styling** with borders, colors, and clear data presentation

### 📊 **Advanced Resource Monitoring**
- **Real-time CPU and Memory utilization** with percentage calculations
- **Color-coded indicators** for instant visual feedback:
  - 🟢 **Green**: Under-utilized (<50%) - *Prime candidates for consolidation*
  - 🟡 **Yellow**: Well-utilized (50-80%) - *Optimal resource usage*
  - 🔴 **Red**: Over-utilized (>80%) - *May need scaling or load balancing*
- **Resource requests vs allocatable** comparison for accurate capacity planning
- **Pod-level resource breakdown** for detailed analysis

### ⚡ **Smart Auto-Refresh**
- **8-second auto-refresh** keeps data current without manual intervention
- **Toggle on/off** with `a` key for control during analysis
- **Visual indicators** show when auto-refresh is active with `[AUTO]` status
- **Background updates** don't interrupt navigation or selection

### 🔍 **Powerful Sorting & Navigation**
- **Quick sort hotkeys** for instant data analysis:
  - `2` - Sort by **CPU utilization %** (find under-utilized nodes instantly)
  - `3` - Sort by **Memory utilization %** (identify memory waste)
  - `4` - Sort by **CPU requests** (see resource allocations)
  - `5` - Sort by **Memory requests** (analyze memory distribution)
- **Enhanced navigation** with Page Up/Down, Home/End keys
- **Current position tracking** shows "Node 5/25" in status bar

### 🎯 **Node Analysis & Selection**
- **Interactive node selection** with `d` key to view detailed pod information
- **Comprehensive node information**:
  - Instance type, zone, node group
  - Roles (master/worker), age, Kubernetes version
  - Capacity vs allocatable resources
  - Current utilization percentages
- **Pod details** showing resource requests, limits, and actual usage

### 📈 **Kubernetes Integration**
- **Metrics-server support** for real-time usage data when available
- **Multi-cluster support** via kubeconfig contexts
- **Fallback mode** works without metrics-server using resource requests
- **All namespaces** pod visibility for complete cluster view

## Use Cases

### 💰 **Cost Optimization**
- **Identify over-provisioned nodes** with low CPU/memory utilization
- **Find consolidation opportunities** by spotting nodes with <30% usage
- **Right-size your cluster** based on actual resource consumption
- **Reduce cloud costs** by eliminating unnecessary compute resources

### 🔧 **Capacity Planning**
- **Monitor resource trends** across all nodes
- **Plan for scaling** by identifying nodes approaching capacity
- **Balance workloads** across the cluster
- **Prevent resource starvation** before it impacts applications

### 🐛 **Troubleshooting**
- **Quick cluster health assessment** with color-coded utilization
- **Identify problem nodes** with high resource usage or restarts
- **Drill down into pod details** for specific node issues
- **Real-time monitoring** during incidents

## Prerequisites

- Python 3.11+
- Conda package manager
- Access to a Kubernetes cluster with valid kubeconfig
- Optional: Kubernetes metrics-server for real-time usage data

## Setup Instructions

### 1. Create Conda Environment

```bash
# Create conda environment with Python 3.11
conda create -n kuv python=3.11 -y

# Activate the environment
conda activate kuv
```

### 2. Install uv Package Manager

```bash
# Install uv in the conda environment
conda install -c conda-forge uv -y
```

### 3. Initialize and Setup Project

```bash
# Clone or navigate to the project directory
cd kuv

# Initialize uv project (if starting fresh)
uv init --python 3.11

# Install dependencies
uv sync
```

### 4. Verify Kubernetes Access

Make sure you have a valid kubeconfig:

```bash
# Test cluster access
kubectl cluster-info
kubectl get nodes
```

## Usage

### Running the Application

```bash
# Activate conda environment
conda activate kuv

# Run KUV
python main.py

# Or use uv run (recommended)
uv run python main.py
```

### Complete Keyboard Reference

#### **Navigation**
- `↑/↓` - Navigate table rows
- `Page Up/Page Down` - Fast scroll through nodes
- `Home` - Jump to first node
- `End` - Jump to last node

#### **Node Selection & Analysis**
- `d` - Select highlighted node to view its pods
- `Enter` - Alternative selection method (if working)

#### **Sorting (Critical for finding under-utilized nodes)**
- `1` - Sort by **Node Name** (alphabetical)
- `2` - Sort by **CPU %** ⭐ **Best for finding under-utilized nodes**
- `3` - Sort by **Memory %** ⭐ **Best for finding memory waste**
- `4` - Sort by **CPU Requests** (raw values)
- `5` - Sort by **Memory Requests** (raw values)
- `s` - Cycle through all sort options

#### **Control**
- `r` - Manual refresh (immediate)
- `a` - Toggle auto-refresh on/off (8-second interval)
- `q` - Quit application

### Quick Start Guide

1. **Launch KUV**: `uv run python main.py`
2. **Find under-utilized nodes**: Press `2` to sort by CPU utilization
3. **Look for green percentages**: Nodes with <50% utilization
4. **Analyze specific nodes**: Use `d` to select and view pod details
5. **Check memory usage**: Press `3` to sort by memory utilization
6. **Enable auto-refresh**: Press `a` for live updates

### Interface Layout

```
┌─────────────────────────────────────────────────────────────────┐
│                    KUV - Kubernetes Usage Viewer               │
├─────────────────────────────────────────────────────────────────┤
│ Nodes (15 visible)                                              │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │Name      Status  Role  Age  CPU Req  CPU %   Mem Req  Mem %│ │
│ │node-1    Ready   work  2d   2.1      45.2%   4.2GB    38.1%│ │
│ │node-2    Ready   work  2d   3.8      89.5%   7.1GB    76.3%│ │
│ │...                                                          │ │
│ └─────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│ Pods on node-1 (10 visible)                                    │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │Name           Namespace  Ready  Status   CPU Req   Mem Req │ │
│ │nginx-deploy   default    1/1    Running  100m      128Mi   │ │
│ │api-server     kube-sys   1/1    Running  250m      512Mi   │ │
│ │...                                                          │ │
│ └─────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│ Updated: 14:30:15 | Nodes: 5/25 | Pods: 8 | Sort: CPU% [AUTO] │
└─────────────────────────────────────────────────────────────────┘
```

## Advanced Features

### Auto-Refresh Behavior
- **Preserves selections**: Selected node stays selected during refresh
- **Maintains cursor position**: Your place in the list is preserved
- **Non-blocking**: You can navigate while refresh happens in background
- **Smart updates**: Only refreshes pods if a node is selected

### Sorting Intelligence
- **CPU/Memory % sorting**: Defaults to descending (highest usage first)
- **Press twice**: Reverses sort order (ascending = lowest usage first)
- **Status indication**: Current sort method shown in status bar
- **Persistent**: Sort preference maintained during auto-refresh

## Troubleshooting

### Connection Issues

```bash
# Check kubeconfig
kubectl config current-context
kubectl config view

# Test cluster connectivity
kubectl get nodes
kubectl top nodes  # Requires metrics-server
```

### Missing Metrics

If you see "Usage: N/A" or no real-time data, install metrics-server:

```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# Wait a few minutes, then verify
kubectl top nodes
```

### Performance Issues

For large clusters (>100 nodes):
- Disable auto-refresh with `a` during intensive analysis
- Use sorting to focus on specific node subsets
- Consider filtering by node groups or zones (future feature)

### Environment Issues

```bash
# Recreate conda environment
conda deactivate
conda env remove -n kuv
conda create -n kuv python=3.11 -y
conda activate kuv
conda install -c conda-forge uv -y
uv sync
```

## Development Commands

```bash
# Activate environment
conda activate kuv

# Install development dependencies
uv add --dev pytest black flake8

# Run tests
uv run pytest

# Format code
uv run black .

# Lint code  
uv run flake8 .

# Build package
uv build

# Update dependencies
uv sync --upgrade
```

## Project Structure

```
kuv/
├── main.py            # Main application with TUI implementation
├── pyproject.toml     # Project configuration and dependencies
├── README.md          # This documentation
├── uv.lock            # Dependency lock file
└── .venv/            # Virtual environment (created by uv)
```

## Tips for Effective Node Utilization Analysis

### Finding Under-Utilized Nodes
1. Press `2` to sort by CPU utilization
2. Look for nodes with **green percentages** (<50%)
3. Press `3` to cross-check memory utilization
4. Use `d` to examine what pods are running on low-utilization nodes

### Identifying Optimization Opportunities
- **Nodes with <30% utilization**: Strong candidates for consolidation
- **Nodes with >80% utilization**: May need additional capacity or load balancing
- **Uneven resource usage**: CPU high but memory low (or vice versa) suggests better pod placement needed

### Best Practices
- **Regular monitoring**: Use auto-refresh during normal operations
- **Trend analysis**: Check utilization at different times of day
- **Pod distribution**: Ensure critical workloads aren't concentrated on single nodes
- **Resource requests**: Verify pods have appropriate resource requests set

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes and test thoroughly
4. Update documentation as needed
5. Submit a pull request

## License

Apache License 2.0 - see LICENSE file for details.

---

**Made for Kubernetes administrators who want to optimize their clusters and reduce costs through better resource utilization insights.**