"""
LlamaController FastAPI application entry point.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from fastapi.exceptions import HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html

from .api import management, ollama, auth, tokens, users, gpu
from .web import routes as web_routes
from .api.dependencies import initialize_managers
from .utils.logging import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting LlamaController...")
    
    try:
        # Initialize managers
        initialize_managers(config_dir="./config")
        logger.info("Managers initialized successfully")
        
        # Sync users from auth-config.yaml to database
        from .api.dependencies import get_config_manager
        from .db.base import SessionLocal
        from .db import crud
        
        config_manager = get_config_manager()
        db = SessionLocal()
        try:
            stats = crud.sync_users_from_config(db, config_manager.auth)
            logger.info(
                f"User sync completed: {stats['created']} created, "
                f"{stats['existing']} existing, {stats['total']} total"
            )
        except Exception as e:
            logger.error(f"Failed to sync users from config: {e}")
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Failed to initialize managers: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down LlamaController...")

# Create FastAPI application with custom docs URLs for air-gap environments
app = FastAPI(
    title="LlamaController",
    description="WebUI-based management system for llama.cpp model lifecycle with Ollama API compatibility",
    version="0.1.0",
    lifespan=lifespan,
    docs_url=None,  # Disable default docs
    redoc_url=None,  # Disable default redoc
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files directory
static_dir = Path(__file__).parent / "web" / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Include routers
# Web UI routes (must be first for / to work)
app.include_router(web_routes.router)

# API routes
app.include_router(auth.router)
app.include_router(tokens.router)
app.include_router(users.router)
app.include_router(management.router)
app.include_router(gpu.router)
app.include_router(ollama.router)

@app.get("/")
async def root():
    """Root endpoint with API information."""
    from .api.dependencies import get_lifecycle_manager
    
    # Get current server status
    lifecycle = get_lifecycle_manager()
    status = await lifecycle.get_status()
    
    response = {
        "name": "LlamaController",
        "version": "0.1.0",
        "description": "llama.cpp model lifecycle management with Ollama API compatibility",
        "endpoints": {
            "management": "/api/v1",
            "ollama_compatible": "/api",
            "docs": "/docs",
            "openapi": "/openapi.json"
        }
    }
    
    # Add llama-server URL if running
    if status.status == "running" and status.host and status.port:
        response["llama_server"] = {
            "status": "running",
            "url": f"http://{status.host}:{status.port}",
            "web_interface": f"http://{status.host}:{status.port}",
            "model": status.model_name or status.model_id
        }
    else:
        response["llama_server"] = {
            "status": "stopped",
            "message": "Load a model to start llama-server"
        }
    
    return response

@app.get("/health")
async def health():
    """Basic health check endpoint."""
    return {"status": "ok"}

@app.get("/test-gpu-detection")
async def test_gpu_detection():
    """Test GPU detection without authentication (for debugging)."""
    print("[DEBUG] /test-gpu-detection endpoint called!")
    from .api.dependencies import get_lifecycle_manager
    
    try:
        lifecycle = get_lifecycle_manager()
        print("[DEBUG] Got lifecycle manager, calling detect_gpu_hardware()...")
        hardware_gpu_status = await lifecycle.detect_gpu_hardware()
        print(f"[DEBUG] detect_gpu_hardware() completed, gpu_count={hardware_gpu_status.gpu_count}")
        
        return {
            "status": "success",
            "gpu_count": hardware_gpu_status.gpu_count,
            "detection_enabled": hardware_gpu_status.detection_enabled,
            "gpus": [
                {
                    "index": gpu.index,
                    "state": gpu.state,
                    "model_name": gpu.model_name,
                    "memory_used": gpu.memory_used,
                    "memory_total": gpu.memory_total
                }
                for gpu in hardware_gpu_status.gpus
            ]
        }
    except Exception as e:
        print(f"[ERROR] test_gpu_detection failed: {e}")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "error": str(e)
        }

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

# Exception handler for 401 Unauthorized - redirect to login for web UI
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Handle HTTP exceptions.
    
    For 401 Unauthorized on web UI routes, redirect to login page.
    For HTMX requests, use HX-Redirect header to trigger full page redirect.
    For API routes, return JSON response.
    """
    # Check if this is an HTMX request
    is_htmx_request = request.headers.get("HX-Request") == "true"
    
    # Check if this is a web UI request (not API)
    is_web_ui = (
        request.url.path.startswith("/dashboard") or
        request.url.path.startswith("/tokens") or
        request.url.path.startswith("/logs") or
        (request.url.path == "/" and "text/html" in request.headers.get("accept", ""))
    )
    
    # For 401 on web UI, redirect to login
    if exc.status_code == status.HTTP_401_UNAUTHORIZED and is_web_ui:
        # Determine the redirect URL for next parameter
        # For HTMX refresh requests, redirect to the main page (e.g., /dashboard) not the refresh endpoint
        next_url = request.url.path
        if next_url.endswith("/refresh"):
            next_url = next_url.rsplit("/refresh", 1)[0]
        
        login_url = f"/login?error=Session expired, please login again&next={next_url}"
        
        logger.info(f"Redirecting unauthorized request to login: {request.url.path} (HTMX: {is_htmx_request})")
        
        # For HTMX requests, use HX-Redirect header to trigger full page redirect
        # instead of content swap which would corrupt the page layout
        if is_htmx_request:
            return HTMLResponse(
                content="",
                status_code=200,  # HTMX requires 2xx status to process HX-Redirect
                headers={"HX-Redirect": login_url}
            )
        
        return RedirectResponse(
            url=login_url,
            status_code=status.HTTP_302_FOUND
        )
    
    # For API routes or other status codes, return JSON
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers
    )

# Exception handler for 404 Not Found - redirect to login for web UI
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """
    Handle 404 Not Found errors.
    
    For web UI requests, redirect to login page.
    For API requests, return JSON response.
    """
    # Check if this is likely a web UI request (browser)
    accept_header = request.headers.get("accept", "")
    is_browser_request = "text/html" in accept_header
    is_api_request = (
        request.url.path.startswith("/api/") or
        request.url.path.startswith("/v1/") or
        "application/json" in accept_header
    )
    
    # For browser requests to non-API paths, redirect to login
    if is_browser_request and not is_api_request:
        logger.info(f"Redirecting 404 request to login: {request.url.path}")
        return RedirectResponse(
            url="/login?error=Page not found",
            status_code=status.HTTP_302_FOUND
        )
    
    # For API requests, return JSON 404
    return JSONResponse(
        status_code=404,
        content={"detail": "Not found"}
    )

# Exception handler for uncaught exceptions
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Handle uncaught exceptions globally."""
    logger.error(f"Uncaught exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "llamacontroller.main:app",
        host="0.0.0.0",
        port=3000,
        reload=True,
        log_level="info"
    )
