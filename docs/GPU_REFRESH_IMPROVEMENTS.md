# GPU Refresh and Load Protection Improvements

## 概述

本文档记录了对GPU状态刷新和模型加载保护机制的改进。

## 实施的改进

### 1. 自动刷新间隔调整

**从 5 秒改为 5 分钟**

- **文件**: `src/llamacontroller/web/templates/dashboard.html`
- **更改**:
  - HTMX触发器: `hx-trigger="every 5s"` → `hx-trigger="every 300s"`
  - 显示标签: `Active (5s)` → `Active (5m)`
- **原因**: 降低服务器负载,减少不必要的频繁刷新

### 2. 加载模型前的GPU状态检查

**实现预加载GPU状态验证**

- **文件**: `src/llamacontroller/web/routes.py`
- **函数**: `load_model_ui()`
- **实现**:
  ```python
  # 在加载前刷新GPU状态
  hardware_gpu_status = await lifecycle_manager.detect_gpu_hardware()
  
  # 验证选定的GPU未被占用
  selected_gpus = [int(g.strip()) for g in gpu_id.split(',') if g.strip().isdigit()]
  for gpu_idx in selected_gpus:
      if gpu_idx < len(hardware_gpu_status.gpus):
          gpu_info = hardware_gpu_status.gpus[gpu_idx]
          if gpu_info.state == 'occupied_by_others':
              raise Exception(f"GPU {gpu_idx} is occupied by another process...")
  ```
- **效果**: 防止在GPU被外部进程占用时加载模型

### 3. GPU按钮禁用逻辑增强

**动态禁用已占用或正在运行的GPU选择按钮**

- **文件**: `src/llamacontroller/web/templates/partials/model_list.html`
- **实现**:
  ```jinja2
  {% set gpu_occupied = hw_gpu and hw_gpu.state == 'occupied_by_others' %}
  {% set gpu_running = gpu_statuses and gpu_statuses.get('gpu' ~ gpu_idx) %}
  {% set gpu_used_in_multi = gpu_statuses and gpu_statuses.get('both') and (gpu_idx == 0 or gpu_idx == 1) %}
  {% set is_disabled = gpu_occupied or gpu_running or gpu_used_in_multi %}
  
  <button type="button" {% if is_disabled %}disabled{% endif %}>
      GPU {{ gpu_idx }}{% if gpu_occupied %} 🔒{% elif gpu_running or gpu_used_in_multi %} ⚡{% endif %}
  </button>
  ```
- **状态指示器**:
  - 🔒 = 被外部进程占用
  - ⚡ = 正在运行模型
- **禁用条件**:
  - GPU被外部进程占用 (`occupied_by_others`)
  - GPU正在运行模型 (`model_loaded`)
  - GPU被用于多GPU模式 (`both` 状态下的GPU 0或1)

### 4. 模型卸载后自动重新启用按钮

**卸载后自动刷新状态**

- **文件**: `src/llamacontroller/web/routes.py`
- **函数**: `unload_model_ui()`
- **机制**: 
  - 卸载模型后自动调用 `detect_gpu_hardware()`
  - 返回更新后的 `dashboard_content.html` 模板
  - HTMX自动更新整个仪表板内容
  - GPU按钮状态自动反映新的空闲状态

## 设计文档更新

**文件**: `design/07-gpu-status-detection.md`

新增章节:

### 5. Model Load Protection

详细描述了:
- 加载前GPU状态检查流程
- 动态按钮状态管理
- 多GPU场景下的按钮禁用逻辑
- 模型卸载后的按钮重新启用机制

## 用户体验改进

### 之前
- 每5秒自动刷新,可能造成服务器负载过高
- 用户可能在GPU被占用后仍然选择它
- 按钮状态更新可能不同步

### 之后
- 每5分钟自动刷新,降低服务器负载
- 加载前自动验证GPU可用性
- 实时显示GPU占用状态:
  - 外部占用显示 🔒
  - 模型运行显示 ⚡
- 按钮根据实际状态自动启用/禁用
- 卸载后立即反映可用状态

## 测试

创建了测试脚本: `scripts/test_gpu_refresh_improvements.py`

测试内容:
1. GPU硬件检测(预加载刷新模拟)
2. 模型加载的GPU状态检查
3. 带预检查的模型加载
4. 加载后的GPU状态验证
5. GPU按钮状态验证(应该被禁用)
6. 模型卸载(按钮应该重新启用)

## 技术细节

### 刷新机制
- **自动刷新**: HTMX轮询 `GET /dashboard/refresh` (每300秒)
- **手动刷新**: 用户操作触发(加载/卸载模型)
- **预加载刷新**: 在 `load_model_ui()` 中调用 `detect_gpu_hardware()`

### 状态同步
- GPU硬件状态 (nvidia-smi)
- 已加载模型状态 (lifecycle_manager.gpu_instances)
- 模板变量传递 (gpu_statuses, hardware_gpu_status)

### 前端状态管理
- Alpine.js 管理 `selectedGpus` 数组
- Jinja2 模板逻辑计算按钮禁用状态
- 动态CSS类控制视觉反馈

## 兼容性

所有更改向后兼容,不影响现有API和功能。

## 下一步改进建议

1. 添加用户可配置的自动刷新间隔
2. 实现WebSocket实时推送GPU状态更新
3. 添加GPU内存使用趋势图表
4. 支持自定义GPU内存阈值配置

## 相关文件

### 修改的文件
- `src/llamacontroller/web/templates/dashboard.html`
- `src/llamacontroller/web/routes.py`
- `src/llamacontroller/web/templates/partials/model_list.html`
- `design/07-gpu-status-detection.md`

### 新增的文件
- `scripts/test_gpu_refresh_improvements.py`
- `docs/GPU_REFRESH_IMPROVEMENTS.md` (本文档)

## 版本信息

- 实施日期: 2025-11-14
- 影响范围: Web UI, GPU管理, 模型生命周期管理
