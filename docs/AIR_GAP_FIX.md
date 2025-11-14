# Air-Gap Machine Fix

## Problem Identified

The web application and API documentation were loading external resources from CDNs, which would fail on air-gapped (offline) machines:

### Web UI Issues
1. **Tailwind CSS** - from `https://cdn.tailwindcss.com`
2. **HTMX 1.9.10** - from `https://unpkg.com/htmx.org@1.9.10`
3. **Alpine.js 3.x** - from `https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js`

### API Documentation Issues
4. **Swagger UI** - FastAPI's default `/docs` endpoint loads resources from CDN
5. **ReDoc** - FastAPI's default `/redoc` endpoint loads resources from CDN

Additionally, the FastAPI application was missing static file serving configuration, which caused the error:
```
starlette.routing.NoMatchFound: No route exists for name "static" and params "path".
```

## Solution Applied

### 1. Downloaded Local Copies

All required libraries and resources have been downloaded and saved locally:

**Web UI Libraries** (`src/llamacontroller/web/static/js/`):
- `htmx-1.9.10.min.js` (47,755 bytes)
- `alpinejs-3.14.1.min.js` (44,659 bytes)
- `tailwindcss.js` (407,279 bytes)

**API Documentation Resources**:
- `src/llamacontroller/web/static/js/swagger-ui-bundle.js` (1,385,226 bytes)
- `src/llamacontroller/web/static/js/swagger-ui-standalone-preset.js` (230,640 bytes)
- `src/llamacontroller/web/static/css/swagger-ui.css` (151,211 bytes)
- `src/llamacontroller/web/static/js/redoc.standalone.js` (870,155 bytes)

**Download Script**: `scripts/download_swagger_resources.py` - Can be used to re-download API documentation resources if needed.

### 2. Updated Templates

Modified `src/llamacontroller/web/templates/base.html` to load from local files instead of CDNs:

**Before:**
```html
<!-- Tailwind CSS -->
<script src="https://cdn.tailwindcss.com"></script>

<!-- HTMX -->
<script src="https://unpkg.com/htmx.org@1.9.10"></script>

<!-- Alpine.js -->
<script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>
```

**After:**
```html
<!-- Tailwind CSS (Local) -->
<script src="{{ url_for('static', path='/js/tailwindcss.js') }}"></script>

<!-- HTMX (Local) -->
<script src="{{ url_for('static', path='/js/htmx-1.9.10.min.js') }}"></script>

<!-- Alpine.js (Local) -->
<script defer src="{{ url_for('static', path='/js/alpinejs-3.14.1.min.js') }}"></script>
```

### 3. Configured Static File Serving

Modified `src/llamacontroller/main.py` to mount the static files directory:

**Added imports:**
```python
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
```

**Added static file mounting:**
```python
# Mount static files directory
static_dir = Path(__file__).parent / "web" / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
```

### 4. Configured Custom API Documentation Endpoints

Modified `src/llamacontroller/main.py` to use local resources for Swagger UI and ReDoc:

**Disabled default docs:**
```python
app = FastAPI(
    title="LlamaController",
    description="WebUI-based management system for llama.cpp model lifecycle with Ollama API compatibility",
    version="0.1.0",
    lifespan=lifespan,
    docs_url=None,  # Disable default docs
    redoc_url=None,  # Disable default redoc
)
```

**Added custom endpoints:**
```python
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    """Custom Swagger UI using local resources for air-gap environments."""
    return get_swagger_ui_html(
        openapi_url=app.openapi_url or "/openapi.json",
        title=f"{app.title} - Swagger UI",
        swagger_js_url="/static/js/swagger-ui-bundle.js",
        swagger_css_url="/static/css/swagger-ui.css",
        swagger_ui_parameters={"persistAuthorization": True},
    )

@app.get("/redoc", include_in_schema=False)
async def custom_redoc_html():
    """Custom ReDoc using local resources for air-gap environments."""
    return get_redoc_html(
        openapi_url=app.openapi_url or "/openapi.json",
        title=f"{app.title} - ReDoc",
        redoc_js_url="/static/js/redoc.standalone.js",
    )
```

This configuration allows the FastAPI application to serve files from `/static` and enables the `url_for('static', ...)` function in templates.

## Testing

To verify the fix works on an air-gapped machine:

1. Start the application
2. Disconnect from the internet
3. Access the web interface at `http://localhost:3000`
4. Test the following pages:
   - Web UI: `http://localhost:3000/login`, `/dashboard`, `/tokens`, `/logs`
   - API Documentation: `http://localhost:3000/docs` (Swagger UI)
   - API Documentation: `http://localhost:3000/redoc` (ReDoc)
5. All pages should render correctly without any missing styles or functionality

## Files Modified

- `src/llamacontroller/web/templates/base.html` - Updated CDN URLs to local references
- `src/llamacontroller/main.py` - Added static file serving and custom API docs configuration

## Files Added

**Web UI:**
- `src/llamacontroller/web/static/js/htmx-1.9.10.min.js`
- `src/llamacontroller/web/static/js/alpinejs-3.14.1.min.js`
- `src/llamacontroller/web/static/js/tailwindcss.js`

**API Documentation:**
- `src/llamacontroller/web/static/js/swagger-ui-bundle.js`
- `src/llamacontroller/web/static/js/swagger-ui-standalone-preset.js`
- `src/llamacontroller/web/static/css/swagger-ui.css`
- `src/llamacontroller/web/static/js/redoc.standalone.js`

**Utility:**
- `scripts/download_swagger_resources.py` - Script to download/update API documentation resources

## Notes

- The Tailwind CSS Play CDN script is suitable for development/prototyping but includes the full compiler (~400KB). For production, consider using the Tailwind CLI to generate a smaller, optimized CSS file.
- All child templates (dashboard.html, login.html, logs.html, tokens.html) inherit from base.html, so they will automatically use the local resources.
- The inline JavaScript in tokens.html for token generation uses browser-native APIs (crypto.getRandomValues, btoa) and will work offline.
- Swagger UI and ReDoc are fully functional offline with all interactive features (Try it out, authentication, etc.)

## Re-downloading Resources

If you need to update the API documentation resources to newer versions:

1. Edit `scripts/download_swagger_resources.py` to update version numbers in URLs
2. Run the script:
   ```bash
   python scripts/download_swagger_resources.py
   ```

## Future Improvements (Optional)

For production optimization:

1. **Tailwind CSS**: Use Tailwind CLI to build a static CSS file:
   ```bash
   npx tailwindcss -o static/css/tailwind.min.css --minify
   ```
   Then replace the script tag with a link to the CSS file.

2. **Minification**: The current files are already minified, but you could further optimize by removing unused CSS/JS.

3. **Versioning**: Consider adding version numbers to filenames (e.g., `tailwind-4.0.0.min.css`) for cache busting during updates.

4. **Swagger UI Preset**: The `swagger-ui-standalone-preset.js` is currently downloaded but not used. It's included for potential future use or if you want to customize the Swagger UI layout.
