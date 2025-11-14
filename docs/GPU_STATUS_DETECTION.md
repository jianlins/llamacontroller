# GPU 状态检测功能文档

## 概述

GPU 状态检测功能允许 LlamaController 实时监控 NVIDIA GPU 的使用状态,帮助用户了解哪些 GPU 可用于加载模型,哪些正被其他进程占用。

## 功能特性

### 1. GPU 状态分类

系统将每个 GPU 分为三种状态:

- **IDLE (空闲)**: GPU 内存使用低于阈值(默认 30MB),可以安全地用于加载新模型
- **MODEL_LOADED (已加载模型)**: GPU 被控制器加载的模型占用,内存使用超过阈值
- **OCCUPIED_BY_OTHERS (被其他程序占用)**: GPU 被其他程序占用,内存使用超过阈值

### 2. 状态判断逻辑

```
如果 GPU 内存使用 > 阈值:
    如果控制器有该 GPU 的模型映射:
        状态 = MODEL_LOADED
    否则:
        状态 = OCCUPIED_BY_OTHERS
否则:
    状态 = IDLE
```

### 3. 配置选项

在 `config/llamacpp-config.yaml` 中配置:

```yaml
gpu_detection:
  enabled: true                    # 启用 GPU 检测
  memory_threshold_mb: 30          # 内存阈值(MB)
  mock_mode: false                 # 测试模式
  mock_data_path: "data/gpu.txt"   # 测试数据路径
```

### 4. Mock 模式

用于在没有 NVIDIA GPU 或 nvidia-smi 的环境中测试功能:

```yaml
gpu_detection:
  enabled: true
  mock_mode: true
  mock_data_path: "data/gpu.txt"
```

## 架构设计

### 核心模块

#### 1. GpuDetector (`src/llamacontroller/core/gpu_detector.py`)

核心检测模块,负责:
- 执行 nvidia-smi 命令获取 GPU 信息
- 解析 GPU 内存使用和进程信息
- 维护 GPU 到模型的映射关系
- 根据内存阈值判断 GPU 状态

关键方法:
```python
# 检测所有 GPU 状态
detect_gpus() -> List[GpuStatus]

# 设置模型映射
set_model_mapping(gpu_id, model_name)

# 清除模型映射
clear_model_mapping(gpu_id)

# 获取 GPU 数量
get_gpu_count() -> int
```

#### 2. 数据模型 (`src/llamacontroller/models/gpu.py`)

定义 API 响应模型:
- `GpuState`: GPU 状态枚举
- `GpuStatusResponse`: 单个 GPU 状态
- `AllGpuStatusResponse`: 所有 GPU 状态
- `GpuProcessInfoResponse`: GPU 进程信息
- `GpuDetectionConfigResponse`: 检测配置信息

#### 3. 生命周期管理器集成 (`src/llamacontroller/core/lifecycle.py`)

添加方法:
```python
# 检测 GPU 硬件状态
detect_gpu_hardware() -> List[GpuStatus]

# 获取 GPU 检测配置
get_gpu_detection_config() -> GpuDetectionConfigResponse
```

## API 端点

### 1. 获取 GPU 状态

```
GET /gpu/status
```

返回所有 GPU 的当前状态信息。

**响应示例:**
```json
{
  "gpus": [
    {
      "index": 0,
      "state": "idle",
      "model_name": null,
      "process_info": null,
      "select_enabled": true,
      "memory_used": 1,
      "memory_total": 46068
    },
    {
      "index": 1,
      "state": "model_loaded",
      "model_name": "llama-2-7b",
      "process_info": null,
      "select_enabled": true,
      "memory_used": 7500,
      "memory_total": 46068
    }
  ]
}
```

### 2. 获取 GPU 数量

```
GET /gpu/count
```

返回可用 GPU 数量。

**响应示例:**
```json
{
  "count": 2
}
```

### 3. 获取检测配置

```
GET /gpu/config
```

返回 GPU 检测配置信息。

**响应示例:**
```json
{
  "enabled": true,
  "memory_threshold_mb": 30,
  "mock_mode": false,
  "gpu_count": 2,
  "detection_available": true
}
```

## 使用示例

### Python 脚本调用

```python
from llamacontroller.core.gpu_detector import GpuDetector

# 初始化检测器
detector = GpuDetector(
    memory_threshold_mb=30,
    mock_mode=False
)

# 检测 GPU 状态
gpu_statuses = detector.detect_gpus()

for status in gpu_statuses:
    print(f"GPU {status.index}: {status.state.value}")
    print(f"  Memory: {status.memory_used}/{status.memory_total}MiB")
    if status.model_name:
        print(f"  Model: {status.model_name}")
```

### API 调用

```bash
# 登录获取会话
curl -X POST http://localhost:3000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin"}' \
  -c cookies.txt

# 获取 GPU 状态
curl -X GET http://localhost:3000/gpu/status \
  -b cookies.txt
```

## 测试

### 1. 单元测试

运行 GPU 检测器测试:
```bash
python scripts/test_gpu_detection.py
```

### 2. API 测试

运行 GPU API 端点测试:
```bash
python scripts/test_gpu_api.py
```

**注意:** API 测试需要服务器正在运行。

## 故障排除

### nvidia-smi 未找到

如果系统提示找不到 nvidia-smi:

1. 检查 NVIDIA 驱动是否已安装
2. 确认 nvidia-smi 在系统 PATH 中
3. 或启用 mock 模式进行测试

### GPU 检测失败

系统会自动回退到 CPU 模式:
```json
{
  "gpus": [
    {
      "index": -1,
      "state": "idle",
      "model_name": null,
      "select_enabled": true,
      "memory_used": 0,
      "memory_total": 0
    }
  ]
}
```

### Mock 数据格式

`data/gpu.txt` 应包含 nvidia-smi 的完整输出。可以通过以下命令获取:

```bash
nvidia-smi > data/gpu.txt
```

## 集成要点

### 模型加载时更新映射

当通过控制器加载模型时,应调用:
```python
lifecycle.gpu_detector.set_model_mapping(gpu_id, model_name)
```

### 模型卸载时清除映射

当卸载模型时,应调用:
```python
lifecycle.gpu_detector.clear_model_mapping(gpu_id)
```

### Web UI 集成

Web UI 可以定期轮询 `/gpu/status` 端点更新 GPU 状态显示,建议轮询间隔 2-5 秒。

## 性能考虑

- nvidia-smi 执行时间通常 < 100ms
- 建议限制 API 调用频率,避免过于频繁的检测
- Mock 模式下性能更好,适合开发和测试环境

## 未来增强

1. **实时更新**: 使用 WebSocket 推送 GPU 状态变化
2. **历史记录**: 记录 GPU 使用历史,用于分析和优化
3. **告警功能**: GPU 温度过高或内存不足时发出告警
4. **多卡调度**: 智能选择最适合的 GPU 加载模型
5. **AMD GPU 支持**: 扩展支持 AMD GPU (rocm-smi)

## 相关文档

- [设计文档](../design/07-gpu-status-detection.md)
- [多 GPU 支持](./user-manual-05-multi-gpu.md)
- [API 文档](./user-manual-04-api.md)

## 版本历史

- **v0.1.0** (2024-11): 初始实现
  - NVIDIA GPU 状态检测
  - Mock 模式支持
  - REST API 端点
  - 基本的状态判断逻辑
