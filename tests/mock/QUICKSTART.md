# 快速开始：使用 Mock nvidia-smi 测试

## 最简单的测试方法（3 步）

### 1️⃣ 打开命令提示符并临时添加 mock 到 PATH

```cmd
cd C:\Users\VHASLCShiJ\Projects\VSCodeProjects\llamacontroller
set PATH=%CD%\tests\mock;%PATH%
```

### 2️⃣ 验证 mock 是否生效

```cmd
nvidia-smi
```

你应该看到模拟的 GPU 输出（2个 NVIDIA A40，一个空闲一个被占用）。

### 3️⃣ 运行测试

```cmd
# 运行综合测试（测试所有场景）
python tests/test_all_scenarios.py

# 或运行现有的 GPU 检测测试
python scripts/test_gpu_detection.py
```

## 测试不同场景

### 使用环境变量切换场景：

```cmd
# 测试所有 GPU 空闲场景
set NVIDIA_SMI_MOCK_FILE=%CD%\tests\mock\scenarios\all_idle.txt
nvidia-smi
python scripts/test_gpu_detection.py

# 测试所有 GPU 被占用场景
set NVIDIA_SMI_MOCK_FILE=%CD%\tests\mock\scenarios\all_occupied.txt
nvidia-smi
python scripts/test_gpu_detection.py

# 测试混合状态场景
set NVIDIA_SMI_MOCK_FILE=%CD%\tests\mock\scenarios\mixed_status.txt
nvidia-smi
python scripts/test_gpu_detection.py

# 清除环境变量，恢复默认场景
set NVIDIA_SMI_MOCK_FILE=
```

## 在代码中使用

不需要修改 PATH，直接在代码中使用 mock 模式：

```python
from llamacontroller.core.gpu_detector import GpuDetector

# 创建使用 mock 数据的检测器
detector = GpuDetector(
    memory_threshold_mb=30,
    mock_mode=True,
    mock_data_path="tests/mock/scenarios/all_idle.txt"
)

# 检测 GPU
statuses = detector.detect_gpus()
for status in statuses:
    print(f"GPU {status.index}: {status.state.value}")
```

## 测试完成后恢复

关闭当前命令窗口或打开新窗口即可恢复正常（临时 PATH 设置会自动失效）。

## PowerShell 用户

```powershell
# 设置 PATH
cd C:\Users\VHASLCShiJ\Projects\VSCodeProjects\llamacontroller
$env:PATH = "$PWD\tests\mock;$env:PATH"

# 验证
nvidia-smi

# 运行测试
python tests/test_all_scenarios.py

# 切换场景
$env:NVIDIA_SMI_MOCK_FILE = "$PWD\tests\mock\scenarios\all_idle.txt"
nvidia-smi
```

## 常见问题

**Q: 运行 nvidia-smi 后看到真实的 GPU 输出怎么办？**

A: 说明系统的 nvidia-smi 在 PATH 中的优先级更高。确保使用完整的命令：

```cmd
set PATH=C:\Users\VHASLCShiJ\Projects\VSCodeProjects\llamacontroller\tests\mock;%PATH%
```

注意 mock 路径在 `%PATH%` **之前**。

**Q: 如何确认使用的是哪个 nvidia-smi？**

A: 使用 `where nvidia-smi` 命令查看：

```cmd
where nvidia-smi
```

第一行应该显示 mock 目录的路径。

**Q: 测试完成后如何恢复？**

A: 最简单的方法是关闭当前命令窗口，打开新窗口。临时的 PATH 设置不会保留到新窗口。

## 更多信息

详细文档请查看 `tests/mock/README.md`
