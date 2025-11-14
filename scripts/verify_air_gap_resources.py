"""
验证离线环境所需的所有资源是否齐全。
此脚本检查Web UI和API UI所需的所有本地资源文件。
"""
from pathlib import Path
from typing import List, Tuple

# 基础目录
static_dir = Path(__file__).parent.parent / "src" / "llamacontroller" / "web" / "static"
js_dir = static_dir / "js"
css_dir = static_dir / "css"

# 必需的资源文件
REQUIRED_RESOURCES = [
    # Web UI 资源
    ("js/htmx-1.9.10.min.js", "HTMX - Web UI交互"),
    ("js/alpinejs-3.14.1.min.js", "Alpine.js - Web UI响应式"),
    ("js/tailwindcss.js", "Tailwind CSS - Web UI样式"),
    
    # API 文档资源 (Swagger UI)
    ("js/swagger-ui-bundle.js", "Swagger UI Bundle"),
    ("js/swagger-ui-standalone-preset.js", "Swagger UI Preset"),
    ("css/swagger-ui.css", "Swagger UI 样式"),
    
    # API 文档资源 (ReDoc)
    ("js/redoc.standalone.js", "ReDoc Standalone"),
]

def check_resource(rel_path: str, description: str) -> Tuple[bool, str, int]:
    """
    检查单个资源文件。
    
    Returns:
        (exists, full_path, size_in_bytes)
    """
    full_path = static_dir / rel_path
    exists = full_path.exists()
    size = full_path.stat().st_size if exists else 0
    return exists, str(full_path), size

def format_size(size_bytes: int) -> str:
    """格式化文件大小显示。"""
    if size_bytes == 0:
        return "0 B"
    
    units = ['B', 'KB', 'MB']
    unit_index = 0
    size = float(size_bytes)
    
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    return f"{size:.2f} {units[unit_index]}"

def main():
    """主验证流程。"""
    import sys
    import os
    def safe_print(s=""):
        try:
            sys.stdout.buffer.write((str(s) + "\n").encode("utf-8"))
        except Exception:
            print(s)
    if os.name == "nt":
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleOutputCP(65001)
    safe_print("=" * 70)
    safe_print("离线环境资源验证")
    safe_print("=" * 70)
    safe_print("")
    
    all_present = True
    missing_resources = []
    present_resources = []
    
    for rel_path, description in REQUIRED_RESOURCES:
        exists, full_path, size = check_resource(rel_path, description)
        
        if exists:
            present_resources.append((rel_path, description, size))
            status = "✓"
            size_str = format_size(size)
            safe_print(f"{status} {description:<35} {size_str:>12}")
        else:
            missing_resources.append((rel_path, description))
            all_present = False
            status = "✗"
            safe_print(f"{status} {description:<35} {'缺失':>12}")
    
    safe_print("")
    safe_print("=" * 70)
    
    if all_present:
        safe_print("✓ 所有资源文件齐全!")
        safe_print("")
        total_size = sum(size for _, _, size in present_resources)
        safe_print(f"总大小: {format_size(total_size)}")
        safe_print("")
        safe_print("您的应用已准备好在离线环境中运行。")
        safe_print("")
        safe_print("测试步骤:")
        safe_print("1. 启动应用: python run.py")
        safe_print("2. 断开网络连接")
        safe_print("3. 访问以下页面验证:")
        safe_print("   - Web UI: http://localhost:3000/login")
        safe_print("   - Dashboard: http://localhost:3000/dashboard")
        safe_print("   - Swagger UI: http://localhost:3000/docs")
        safe_print("   - ReDoc: http://localhost:3000/redoc")
        return 0
    else:
        safe_print("✗ 发现缺失的资源文件!")
        safe_print("")
        safe_print("缺失的资源:")
        for rel_path, description in missing_resources:
            safe_print(f"  - {description} ({rel_path})")
        safe_print("")
        safe_print("修复方法:")
        safe_print("1. 运行下载脚本获取所有资源:")
        safe_print("   python scripts/download_all_resources.py")
        safe_print("")
        safe_print("2. 或手动下载缺失的资源文件")
        return 1

if __name__ == "__main__":
    exit(main())
