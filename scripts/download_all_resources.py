"""
下载离线环境所需的所有资源文件。
此脚本会下载Web UI和API文档所需的所有JavaScript和CSS库。
"""
import urllib.request
import ssl
from pathlib import Path
from typing import List, Dict

# 基础目录
static_dir = Path(__file__).parent.parent / "src" / "llamacontroller" / "web" / "static"
js_dir = static_dir / "js"
css_dir = static_dir / "css"

# 确保目录存在
js_dir.mkdir(parents=True, exist_ok=True)
css_dir.mkdir(parents=True, exist_ok=True)

# 所有需要下载的资源
RESOURCES = [
    # Web UI 资源
    {
        "name": "HTMX 1.9.10",
        "url": "https://unpkg.com/htmx.org@1.9.10/dist/htmx.min.js",
        "path": js_dir / "htmx-1.9.10.min.js"
    },
    {
        "name": "Alpine.js 3.14.1",
        "url": "https://cdn.jsdelivr.net/npm/alpinejs@3.14.1/dist/cdn.min.js",
        "path": js_dir / "alpinejs-3.14.1.min.js"
    },
    {
        "name": "Tailwind CSS",
        "url": "https://cdn.tailwindcss.com/3.4.1",
        "path": js_dir / "tailwindcss.js"
    },
    
    # API 文档资源 - Swagger UI
    {
        "name": "Swagger UI Bundle",
        "url": "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui-bundle.js",
        "path": js_dir / "swagger-ui-bundle.js"
    },
    {
        "name": "Swagger UI Standalone Preset",
        "url": "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui-standalone-preset.js",
        "path": js_dir / "swagger-ui-standalone-preset.js"
    },
    {
        "name": "Swagger UI CSS",
        "url": "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui.css",
        "path": css_dir / "swagger-ui.css"
    },
    
    # API 文档资源 - ReDoc
    {
        "name": "ReDoc Standalone",
        "url": "https://cdn.jsdelivr.net/npm/redoc@2.1.3/bundles/redoc.standalone.js",
        "path": js_dir / "redoc.standalone.js"
    }
]

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

def download_file(name: str, url: str, dest: Path) -> bool:
    """
    从URL下载文件到目标路径。
    
    Returns:
        True if successful, False otherwise
    """
    print(f"正在下载: {name}")
    print(f"  URL: {url}")
    
    try:
        # 创建未验证的SSL上下文用于下载公共资源
        context = ssl._create_unverified_context()
        with urllib.request.urlopen(url, context=context, timeout=30) as response:
            content = response.read()
            dest.write_bytes(content)
            size_str = format_size(len(content))
            print(f"  ✓ 已保存: {dest.relative_to(Path.cwd())} ({size_str})")
            return True
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False

def main():
    """主下载流程。"""
    print("=" * 70)
    print("下载离线环境所需资源")
    print("=" * 70)
    print()
    print(f"目标目录: {static_dir}")
    print(f"需要下载 {len(RESOURCES)} 个文件")
    print()
    
    success_count = 0
    failed_resources = []
    
    for i, resource in enumerate(RESOURCES, 1):
        print(f"[{i}/{len(RESOURCES)}] ", end="")
        
        if download_file(resource["name"], resource["url"], resource["path"]):
            success_count += 1
        else:
            failed_resources.append(resource["name"])
        
        print()
    
    print("=" * 70)
    print(f"下载完成: {success_count}/{len(RESOURCES)} 成功")
    
    if failed_resources:
        print()
        print("失败的资源:")
        for name in failed_resources:
            print(f"  - {name}")
        print()
        print("您可以手动下载失败的资源,或稍后重试。")
        return 1
    else:
        print()
        print("✓ 所有资源已成功下载!")
        print()
        print("下一步:")
        print("1. 运行验证脚本确认: python scripts/verify_air_gap_resources.py")
        print("2. 启动应用测试: python run.py")
        print("3. 在断网状态下访问 http://localhost:3000 验证离线功能")
        return 0

if __name__ == "__main__":
    exit(main())
