# GPU Mock Testing Guide

本指南说明如何在没有真实 GPU 的机器上测试 GPU 状态检测功能。

## 配置说明

### 启用 Mock 模式

在 `config/llamacpp-config.yaml` 中设置：

```yaml
gpu_detection:
  enabled: true
  memory_threshold_mb: 30  # GPU 被视为占用的内存阈值（MB）
  mock_mode: true  # 启用 mock 模式，使用模拟数据而不是真实的 nvidia-smi
  mock_data_path: "tests/mock/gpu_output.txt"  # mock 数据文件路径
```

### Mock 数据文件

系统使用 `tests/mock/gpu_output.txt` 作为默认的 mock 数据。该文件包含模拟的 nvidia-smi 输出：

- **GPU 0**: 1MiB 内存使用（低于阈值 30MB）→ 显示为 **Idle**
- **GPU 1**: 363MiB 内存使用（高于阈值 30MB）→ 显示为 **Occupied**

## 不同场景测试

`tests/mock/scenarios/` 目录包含不同的测试场景：

### 1. mixed_status.txt
- GPU 0: Idle (1MiB)
- GPU 1: Occupied (363MiB)

### 2. all_idle.txt
- GPU 0: Idle (1MiB)
- GPU 1: Idle (2MiB)

### 3. all_occupied.txt
- GPU 0: Occupied (20480MiB)
- GPU 1: Occupied (18432MiB)

### 4. single_gpu.txt
- GPU 0: Idle (1MiB)
- 仅一个 GPU

## 切换测试场景

要使用不同的场景，修改 `config/llamacpp-config.yaml`：

```yaml
mock_data_path: "tests/mock/scenarios/all_occupied.txt"
```

然后重启服务器。

## 启动服务器

### 方法 1: 直接启动（推荐用于 mock 模式）
```powershell
python run.py
```

### 方法 2: 使用启动脚本（用于 PATH 方式）
```powershell
.\start_with_mock_gpu.ps1
```

## 验证 GPU 状态

1. 启动服务器后，访问 http://localhost:3000
2. 登录到仪表板
3. 查看 "GPU Status" 部分

### 预期显示（使用默认 gpu_output.txt）

- **GPU 0**: 
  - 状态: 灰色背景
  - 标签: "Idle"
  - 内存: 1MiB / 46068MiB

- **GPU 1**: 
  - 状态: 黄色背景 ⚠️
  - 标签: "Occupied"
  - 信息: "Occupied by someone else"
  - 内存: 363MiB / 46068MiB

## 日志验证

启动时应看到以下日志：

```
GPU Detector initialized: threshold=30MB, mock_mode=True
ModelLifecycleManager initialized with multi-GPU support
```

访问仪表板时，不应再看到 "nvidia-smi not found" 错误。

## 切换回真实 GPU 模式

在有真实 GPU 的机器上，将配置改回：

```yaml
gpu_detection:
  enabled: true
  memory_threshold_mb: 30
  mock_mode: false  # 禁用 mock 模式
  mock_data_path: "tests/mock/gpu_output.txt"
```

## 故障排查

### 问题: 仍然显示 "nvidia-smi not found"

**原因**: `mock_mode: false` 时系统会尝试运行真实的 nvidia-smi

**解决**: 确保 `mock_mode: true` 在配置文件中

### 问题: GPU 1 没有显示为 Occupied

**原因**: 可能使用了错误的 mock 数据文件

**解决**: 
1. 检查 `mock_data_path` 路径是否正确
2. 检查文件内容是否包含 GPU 1 的高内存使用数据
3. 确认 `memory_threshold_mb` 设置（默认 30MB）

### 问题: 所有 GPU 都显示为 Idle

**原因**: `memory_threshold_mb` 设置过高

**解决**: 降低阈值，例如改为 30MB
