"""
Web UI Routes for LlamaController

Provides web-based interface for managing llama.cpp models.
Uses HTMX for dynamic interactions and Jinja2 for server-side rendering.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Request, Depends, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..auth.dependencies import get_current_user_from_session, get_optional_user_from_session
from ..auth.service import AuthService
from ..db.base import get_db
from ..db.models import User
from ..api.dependencies import get_lifecycle_manager
from ..core.lifecycle import ModelLifecycleManager

# Initialize logger
logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(tags=["Web UI"])

# Initialize templates
templates = Jinja2Templates(directory="src/llamacontroller/web/templates")


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def root(
    request: Request,
    user: Optional[User] = Depends(get_optional_user_from_session)
):
    """Root endpoint - redirect to dashboard if logged in, otherwise to login."""
    if user:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)


@router.get("/login", response_class=HTMLResponse, include_in_schema=False)
async def login_page(
    request: Request,
    error: Optional[str] = None,
    next: Optional[str] = None
):
    """Display login page."""
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "error": error,
            "next": next
        }
    )


@router.post("/login", include_in_schema=False)
async def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    next: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Process login form submission."""
    from ..auth.utils import get_client_ip, get_user_agent
    
    auth_service = AuthService(db)
    
    # Get request info
    ip_address = get_client_ip(request)
    user_agent = get_user_agent(request)
    
    # Authenticate user
    success, error_msg, user = auth_service.authenticate_user(username, password, ip_address)
    if not success or user is None:
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "error": error_msg or "Invalid username or password",
                "username": username,
                "next": next
            },
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    
    # Create session
    login_response = auth_service.create_session(user, ip_address, user_agent)
    
    # Determine redirect URL - use next parameter if valid, otherwise dashboard
    redirect_url = "/dashboard"
    if next and next.startswith("/") and not next.startswith("//"):
        # Only allow relative URLs starting with / but not //
        # This prevents open redirect vulnerabilities
        redirect_url = next
    
    # Set session cookie
    response = RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        key="session_id",
        value=login_response.session_id,
        httponly=True,
        max_age=3600,  # 1 hour
        samesite="lax"
    )
    
    return response


@router.get("/logout", include_in_schema=False)
async def logout(
    request: Request,
    db: Session = Depends(get_db)
):
    """Logout user and destroy session."""
    from ..auth.utils import get_client_ip
    
    session_id = request.cookies.get("session_id")
    if session_id:
        auth_service = AuthService(db)
        ip_address = get_client_ip(request)
        auth_service.logout(session_id, ip_address)
    
    response = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    response.delete_cookie(key="session_id")
    return response


@router.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
async def dashboard(
    request: Request,
    user: User = Depends(get_current_user_from_session),
    lifecycle_manager: ModelLifecycleManager = Depends(get_lifecycle_manager)
):
    """Display main dashboard."""
    # Get current model status
    status_info = await lifecycle_manager.get_status()
    
    # Get GPU statuses (for multi-GPU support)
    gpu_statuses = await lifecycle_manager.get_all_gpu_statuses()
    
    # Get hardware GPU detection status
    hardware_gpu_status = await lifecycle_manager.detect_gpu_hardware()
    
    # Get available models
    available_models = lifecycle_manager.config_manager.models.models
    
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": user,
            "status": status_info,
            "gpu_statuses": gpu_statuses,
            "hardware_gpu_status": hardware_gpu_status,
            "available_models": available_models,
            "active_page": "dashboard"
        }
    )


@router.post("/dashboard/load-model", include_in_schema=False)
async def load_model_ui(
    request: Request,
    model_id: str = Form(...),
    gpu_id: str = Form("0"),  # GPU ID from form (comma-separated: "0", "1", or "0,1")
    user: User = Depends(get_current_user_from_session),
    lifecycle_manager: ModelLifecycleManager = Depends(get_lifecycle_manager)
):
    """Load a model on specified GPU(s) (HTMX endpoint)."""
    try:
        # Refresh GPU status before loading to ensure accurate occupancy detection
        hardware_gpu_status = await lifecycle_manager.detect_gpu_hardware()
        
        # Verify selected GPU(s) are not occupied
        selected_gpus = [int(g.strip()) for g in gpu_id.split(',') if g.strip().isdigit()]
        for gpu_idx in selected_gpus:
            if gpu_idx < len(hardware_gpu_status.gpus):
                gpu_info = hardware_gpu_status.gpus[gpu_idx]
                if gpu_info.state == 'occupied_by_others':
                    raise Exception(f"GPU {gpu_idx} is occupied by another process. Please refresh and select an available GPU.")
        
        # Load model on specified GPU
        result = await lifecycle_manager.load_model(model_id, gpu_id)
        
        # Get updated GPU statuses and available models
        gpu_statuses = await lifecycle_manager.get_all_gpu_statuses()
        hardware_gpu_status = await lifecycle_manager.detect_gpu_hardware()
        status_info = await lifecycle_manager.get_status()
        available_models = lifecycle_manager.config_manager.models.models
        
        return templates.TemplateResponse(
            "partials/dashboard_content.html",
            {
                "request": request,
                "status": status_info,
                "gpu_statuses": gpu_statuses,
                "hardware_gpu_status": hardware_gpu_status,
                "available_models": available_models,
                "message": result.message,
                "message_type": "success"
            }
        )
    except Exception as e:
        gpu_statuses = await lifecycle_manager.get_all_gpu_statuses()
        hardware_gpu_status = await lifecycle_manager.detect_gpu_hardware()
        status_info = await lifecycle_manager.get_status()
        available_models = lifecycle_manager.config_manager.models.models
        
        # Get server logs to help diagnose the error (if any adapter exists)
        server_logs = []
        
        return templates.TemplateResponse(
            "partials/dashboard_content.html",
            {
                "request": request,
                "status": status_info,
                "gpu_statuses": gpu_statuses,
                "hardware_gpu_status": hardware_gpu_status,
                "available_models": available_models,
                "message": f"Failed to load model: {str(e)}",
                "message_type": "error",
                "server_logs": server_logs
            }
        )


@router.post("/dashboard/unload-model", include_in_schema=False)
async def unload_model_ui(
    request: Request,
    gpu_id: str = Form(...),  # GPU ID to unload from
    user: User = Depends(get_current_user_from_session),
    lifecycle_manager: ModelLifecycleManager = Depends(get_lifecycle_manager)
):
    """Unload model from specified GPU(s) (HTMX endpoint)."""
    try:
        await lifecycle_manager.unload_model(gpu_id)
        
        # Get updated GPU statuses and available models
        gpu_statuses = await lifecycle_manager.get_all_gpu_statuses()
        hardware_gpu_status = await lifecycle_manager.detect_gpu_hardware()
        status_info = await lifecycle_manager.get_status()
        available_models = lifecycle_manager.config_manager.models.models
        
        return templates.TemplateResponse(
            "partials/dashboard_content.html",
            {
                "request": request,
                "status": status_info,
                "gpu_statuses": gpu_statuses,
                "hardware_gpu_status": hardware_gpu_status,
                "available_models": available_models,
                "message": f"Successfully unloaded model from GPU {gpu_id}",
                "message_type": "success"
            }
        )
    except Exception as e:
        gpu_statuses = await lifecycle_manager.get_all_gpu_statuses()
        hardware_gpu_status = await lifecycle_manager.detect_gpu_hardware()
        status_info = await lifecycle_manager.get_status()
        available_models = lifecycle_manager.config_manager.models.models
        return templates.TemplateResponse(
            "partials/dashboard_content.html",
            {
                "request": request,
                "status": status_info,
                "gpu_statuses": gpu_statuses,
                "hardware_gpu_status": hardware_gpu_status,
                "available_models": available_models,
                "message": f"Failed to unload model from GPU {gpu_id}: {str(e)}",
                "message_type": "error"
            }
        )


@router.get("/dashboard/refresh", include_in_schema=False)
async def refresh_dashboard(
    request: Request,
    user: User = Depends(get_current_user_from_session),
    lifecycle_manager: ModelLifecycleManager = Depends(get_lifecycle_manager)
):
    """Refresh dashboard content (HTMX endpoint for auto-refresh)."""
    # Get current model status
    status_info = await lifecycle_manager.get_status()
    
    # Get GPU statuses (for multi-GPU support)
    gpu_statuses = await lifecycle_manager.get_all_gpu_statuses()
    
    # Get hardware GPU detection status
    hardware_gpu_status = await lifecycle_manager.detect_gpu_hardware()
    
    # Get available models
    available_models = lifecycle_manager.config_manager.models.models
    
    return templates.TemplateResponse(
        "partials/dashboard_content.html",
        {
            "request": request,
            "status": status_info,
            "gpu_statuses": gpu_statuses,
            "hardware_gpu_status": hardware_gpu_status,
            "available_models": available_models
        }
    )

@router.post("/dashboard/switch-model", include_in_schema=False)
async def switch_model_ui(
    request: Request,
    model_id: str = Form(...),
    user: User = Depends(get_current_user_from_session),
    lifecycle_manager: ModelLifecycleManager = Depends(get_lifecycle_manager)
):
    """Switch to a different model (HTMX endpoint)."""
    try:
        result = await lifecycle_manager.switch_model(model_id)
        status_info = await lifecycle_manager.get_status()
        
        return templates.TemplateResponse(
            "partials/model_status.html",
            {
                "request": request,
                "status": status_info,
                "message": f"Successfully switched to model: {model_id}",
                "message_type": "success"
            }
        )
    except Exception as e:
        status_info = await lifecycle_manager.get_status()
        return templates.TemplateResponse(
            "partials/model_status.html",
            {
                "request": request,
                "status": status_info,
                "message": f"Failed to switch model: {str(e)}",
                "message_type": "error"
            }
        )


@router.get("/tokens", response_class=HTMLResponse, include_in_schema=False)
async def tokens_page(
    request: Request,
    user: User = Depends(get_current_user_from_session),
    db: Session = Depends(get_db)
):
    """Display token management page."""
    from ..db import crud
    
    # Get user's tokens
    tokens = crud.get_user_api_tokens(db, user.id)
    
    return templates.TemplateResponse(
        "tokens.html",
        {
            "request": request,
            "user": user,
            "tokens": tokens,
            "active_page": "tokens"
        }
    )


@router.post("/tokens/create", include_in_schema=False)
async def create_token_ui(
    request: Request,
    token_name: str = Form(...),
    token_value: Optional[str] = Form(None),
    expires_days: Optional[str] = Form(None),
    user: User = Depends(get_current_user_from_session),
    db: Session = Depends(get_db)
):
    """Create a new API token (HTMX endpoint)."""
    from ..db import crud
    
    try:
        # Convert expires_days to int if provided and not empty
        expires_days_int = None
        if expires_days and expires_days.strip():
            try:
                expires_days_int = int(expires_days)
                if expires_days_int <= 0 or expires_days_int > 365:
                    raise ValueError("Expiry days must be between 1 and 365")
            except ValueError as e:
                tokens = crud.get_user_api_tokens(db, user.id)
                return templates.TemplateResponse(
                    "partials/token_list.html",
                    {
                        "request": request,
                        "tokens": tokens,
                        "message": f"Invalid expiry days: {str(e)}",
                        "message_type": "error"
                    }
                )
        
        # Get custom token value if provided
        custom_token = None
        if token_value and token_value.strip():
            custom_token = token_value.strip()
        
        # Create token
        token_obj, plain_token = crud.create_api_token(
            db, user.id, token_name, expires_days_int, custom_token
        )
        
        # Get updated token list
        tokens = crud.get_user_api_tokens(db, user.id)
        
        return templates.TemplateResponse(
            "partials/token_list.html",
            {
                "request": request,
                "tokens": tokens,
                "new_token": plain_token,
                "message": f"Token '{token_name}' created successfully. Please copy it now, it won't be shown again!",
                "message_type": "success"
            }
        )
    except Exception as e:
        tokens = crud.get_user_api_tokens(db, user.id)
        return templates.TemplateResponse(
            "partials/token_list.html",
            {
                "request": request,
                "tokens": tokens,
                "message": f"Failed to create token: {str(e)}",
                "message_type": "error"
            }
        )


@router.delete("/tokens/{token_id}", include_in_schema=False)
async def delete_token_ui(
    request: Request,
    token_id: int,
    user: User = Depends(get_current_user_from_session),
    db: Session = Depends(get_db)
):
    """Delete an API token (HTMX endpoint)."""
    from ..db import crud
    
    try:
        # Get token and verify ownership
        token = crud.get_api_token_by_id(db, token_id)
        if not token or token.user_id != user.id:
            raise HTTPException(status_code=404, detail="Token not found")
        
        # Delete token
        crud.delete_api_token(db, token)
        
        # Get updated token list
        tokens = crud.get_user_api_tokens(db, user.id)
        
        return templates.TemplateResponse(
            "partials/token_list.html",
            {
                "request": request,
                "tokens": tokens,
                "message": "Token deleted successfully",
                "message_type": "success"
            }
        )
    except Exception as e:
        tokens = crud.get_user_api_tokens(db, user.id)
        return templates.TemplateResponse(
            "partials/token_list.html",
            {
                "request": request,
                "tokens": tokens,
                "message": f"Failed to delete token: {str(e)}",
                "message_type": "error"
            }
        )


@router.get("/logs", response_class=HTMLResponse, include_in_schema=False)
async def logs_page(
    request: Request,
    user: User = Depends(get_current_user_from_session),
    lifecycle_manager: ModelLifecycleManager = Depends(get_lifecycle_manager)
):
    """Display logs viewer page."""
    # Get recent logs from any loaded GPU instance
    try:
        # Debug: Check what GPU instances are loaded
        loaded_gpus = list(lifecycle_manager.gpu_instances.keys())
        logger.info(f"Logs page - Loaded GPU instances: {loaded_gpus}")
        
        logs = await lifecycle_manager.get_server_logs(gpu_id=None, lines=100)
        logger.info(f"Logs page - Retrieved {len(logs)} log lines")
    except Exception as e:
        logger.error(f"Error fetching logs: {e}", exc_info=True)
        logs = [f"Error fetching logs: {str(e)}"]
    
    return templates.TemplateResponse(
        "logs.html",
        {
            "request": request,
            "user": user,
            "logs": logs,
            "active_page": "logs"
        }
    )


@router.get("/logs/refresh", include_in_schema=False)
async def refresh_logs(
    request: Request,
    user: User = Depends(get_current_user_from_session),
    lifecycle_manager: ModelLifecycleManager = Depends(get_lifecycle_manager)
):
    """Refresh logs (HTMX endpoint)."""
    try:
        logs = await lifecycle_manager.get_server_logs(gpu_id=None, lines=100)
    except Exception as e:
        logs = [f"Error fetching logs: {str(e)}"]
    
    return templates.TemplateResponse(
        "partials/logs_content.html",
        {
            "request": request,
            "logs": logs
        }
    )

@router.get("/api-ui", include_in_schema=False)
async def api_ui_redirect(
    request: Request,
    user: User = Depends(get_current_user_from_session)
):
    """Redirect to FastAPI interactive API documentation."""
    return RedirectResponse(url="/docs", status_code=status.HTTP_302_FOUND)
