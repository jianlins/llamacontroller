"""
Download Swagger UI and ReDoc resources for air-gap environments.
"""
import urllib.request
import ssl
from pathlib import Path

# Base directory for static files
static_dir = Path(__file__).parent.parent / "src" / "llamacontroller" / "web" / "static"
js_dir = static_dir / "js"
css_dir = static_dir / "css"

# Ensure directories exist
js_dir.mkdir(parents=True, exist_ok=True)
css_dir.mkdir(parents=True, exist_ok=True)

# Resources to download
resources = [
    # Swagger UI
    {
        "url": "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui-bundle.js",
        "path": js_dir / "swagger-ui-bundle.js"
    },
    {
        "url": "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui-standalone-preset.js",
        "path": js_dir / "swagger-ui-standalone-preset.js"
    },
    {
        "url": "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui.css",
        "path": css_dir / "swagger-ui.css"
    },
    # ReDoc
    {
        "url": "https://cdn.jsdelivr.net/npm/redoc@2.1.3/bundles/redoc.standalone.js",
        "path": js_dir / "redoc.standalone.js"
    }
]

def download_file(url: str, dest: Path):
    """Download a file from URL to destination path."""
    print(f"Downloading {url}...")
    try:
        # Create unverified SSL context for downloading public resources
        context = ssl._create_unverified_context()
        with urllib.request.urlopen(url, context=context, timeout=30) as response:
            content = response.read()
            dest.write_bytes(content)
            print(f"  ✓ Saved to {dest} ({len(content):,} bytes)")
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        raise

def main():
    """Download all resources."""
    print("Downloading Swagger UI and ReDoc resources for air-gap deployment...\n")
    
    for resource in resources:
        download_file(resource["url"], resource["path"])
    
    print("\n✓ All resources downloaded successfully!")
    print("\nFiles saved:")
    for resource in resources:
        print(f"  - {resource['path']}")

if __name__ == "__main__":
    main()
