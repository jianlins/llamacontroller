# Mock nvidia-smi for Testing

这个目录包含用于测试 GPU 检测功能的模拟 nvidia-smi 脚本和测试数据。

## 文件说明

### nvidia-smi.bat
模拟的 nvidia-smi 命令脚本，用于在没有真实 NVIDIA GPU 的机器上测试。

### gpu_output.txt
默认的 nvidia-smi 输出数据（两个 GPU，一个空闲，一个被占用）。

### scenarios/
包含不同测试场景的数据文件：

- **all_idle.txt** - 所有 GPU 都空闲（内存使用 < 30MB）
- **all_occupied.txt** - 所有 GPU 都被占用，包含进程信息
- **mixed_status.txt** - 混合状态：GPU 0 空闲，GPU 1 被占用
- **single_gpu.txt** - 单 GPU 场景，显示多个进程占用

## 使用方法

### 方法 1: 临时添加到 PATH（推荐用于测试）

在 Windows 命令提示符或 PowerShell 中：

```cmd
# 将 mock 目录添加到 PATH 前面（当前会话有效）
set PATH=C:\Users\VHASLCShiJ\Projects\VSCodeProjects\llamacontroller\tests\mock;%PATH%

# 验证 mock nvidia-smi 是否生效
nvidia-smi

# 运行测试
python scripts/test_gpu_detection.py
```

PowerShell:
```powershell
# 将 mock 目录添加到 PATH 前面
$env:PATH = "C:\Users\VHASLCShiJ\Projects\VSCodeProjects\llamacontroller\tests\mock;$env:PATH"

# 验证
nvidia-smi

# 运行测试
python scripts/test_gpu_detection.py
```

### 方法 2: 使用环境变量切换测试场景

```cmd
# 使用特定的测试场景
set NVIDIA_SMI_MOCK_FILE=C:\Users\VHASLCShiJ\Projects\VSCodeProjects\llamacontroller\tests\mock\scenarios\all_idle.txt
nvidia-smi

# 切换到另一个场景
set NVIDIA_SMI_MOCK_FILE=C:\Users\VHASLCShiJ\Projects\VSCodeProjects\llamacontroller\tests\mock\scenarios\all_occupied.txt
nvidia-smi
```

### 方法 3: 在代码中使用 mock 模式

GpuDetector 类本身支持 mock 模式：

```python
from llamacontroller.core.gpu_detector import GpuDetector

# 方式 1: 使用 mock 模式，指定数据文件
detector = GpuDetector(
    memory_threshold_mb=30,
    mock_mode=True,
    mock_data_path="tests/mock/scenarios/all_idle.txt"
)

# 方式 2: 使用真实的 nvidia-smi（但会调用我们的 mock 脚本）
# 前提是已将 tests/mock 添加到 PATH
detector = GpuDetector(memory_threshold_mb=30)

# 检测 GPU
statuses = detector.detect_gpus()
for status in statuses:
    print(f"GPU {status.index}: {status.state.value}")
```

## 测试场景说明

### 1. all_idle.txt
```
GPU 0: 1MiB used (空闲)
GPU 1: 2MiB used (空闲)
```
预期结果：两个 GPU 都应该显示为 IDLE，都可以被选择。

### 2. all_occupied.txt
```
GPU 0: 8192MiB used (python.exe, PID 12345)
GPU 1: 12288MiB used (llama-server.exe, PID 23456)
```
预期结果：两个 GPU 都应该显示为 OCCUPIED_BY_OTHERS，不可选择，显示进程信息。

### 3. mixed_status.txt
```
GPU 0: 1MiB used (空闲)
GPU 1: 363MiB used (被占用，无进程信息)
```
预期结果：GPU 0 空闲可选，GPU 1 被占用不可选。

### 4. single_gpu.txt
```
GPU 0: 1024MiB used (dwm.exe + chrome.exe)
```
预期结果：单个 GPU 被占用，显示多个进程信息。

## 快速测试脚本示例

创建一个测试脚本来验证所有场景：

```python
# test_all_scenarios.py
import os
from pathlib import Path
from llamacontroller.core.gpu_detector import GpuDetector

scenarios = [
    "all_idle.txt",
    "all_occupied.txt", 
    "mixed_status.txt",
    "single_gpu.txt"
]

base_path = Path("tests/mock/scenarios")

for scenario in scenarios:
    print(f"\n{'='*60}")
    print(f"Testing scenario: {scenario}")
    print('='*60)
    
    detector = GpuDetector(
        memory_threshold_mb=30,
        mock_mode=True,
        mock_data_path=str(base_path / scenario)
    )
    
    statuses = detector.detect_gpus()
    
    for status in statuses:
        print(f"\nGPU {status.index}:")
        print(f"  State: {status.state.value}")
        print(f"  Memory: {status.memory_used}/{status.memory_total} MiB")
        print(f"  Selectable: {status.select_enabled}")
        if status.model_name:
            print(f"  Model: {status.model_name}")
        if status.process_info:
            print(f"  Processes:")
            for proc in status.process_info:
                print(f"    - PID {proc.pid}: {proc.process_name} ({proc.used_memory} MiB)")
```

运行测试：
```bash
python test_all_scenarios.py
```

## 注意事项

1. **PATH 优先级**：确保 mock 目录在系统 nvidia-smi 之前，否则会调用真实的 nvidia-smi
2. **临时性**：使用 `set PATH=...` 只在当前命令窗口有效，关闭窗口后失效
3. **测试完成后**：记得移除 mock 目录从 PATH，或关闭测试用的命令窗口
4. **验证**：使用 `where nvidia-smi`（CMD）或 `Get-Command nvidia-smi`（PowerShell）查看实际调用的是哪个版本

## 恢复真实 nvidia-smi

如果需要恢复使用真实的 nvidia-smi：

```cmd
# 关闭当前命令窗口，或者
# 重新打开一个新的命令窗口（没有设置临时 PATH）

# 或者显式重置 PATH（复杂，不推荐）
```

最简单的方法是关闭测试窗口，打开新窗口即可恢复正常。
