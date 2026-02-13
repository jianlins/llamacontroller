# Session 009: HTMX Session Timeout Rendering Fix

## Date: 2026-02-13

## Issue
When the webpage dashboard times out and automatically logs off the user, after the user tries to re-login, the webpage is not properly rendered.

## Root Cause Analysis

1. **Auto-refresh mechanism**: The dashboard has HTMX auto-refresh configured with `hx-get="/dashboard/refresh"` triggered every 300 seconds
2. **Session timeout**: When the session expires, the `/dashboard/refresh` endpoint returns a 401 Unauthorized response
3. **HTMX behavior issue**: The original exception handler returned a `RedirectResponse` with 302 status code
4. **Content corruption**: HTMX followed the redirect, received the login page HTML, and swapped it into the `#dashboard-content` div, corrupting the page layout
5. **Post-login issues**: When user re-logged in, the corrupted page structure persisted

## Solution

Modified the HTTP exception handler in `src/llamacontroller/main.py` to:

1. **Detect HTMX requests**: Check for `HX-Request: true` header
2. **Use HX-Redirect header**: For HTMX requests returning 401, use the `HX-Redirect` response header instead of 302 redirect
3. **Return 2xx status**: HTMX requires 2xx status codes to process the `HX-Redirect` header
4. **Smart next URL**: Strip `/refresh` suffix from the URL so users return to `/dashboard` instead of `/dashboard/refresh`

## Code Changes

### `src/llamacontroller/main.py`

```python
# Before: Only handled regular browser redirects
if exc.status_code == status.HTTP_401_UNAUTHORIZED and is_web_ui:
    return RedirectResponse(
        url=f"/login?error=Please login first&next={request.url.path}",
        status_code=status.HTTP_302_FOUND
    )

# After: Handle HTMX requests specially
if exc.status_code == status.HTTP_401_UNAUTHORIZED and is_web_ui:
    # Determine the redirect URL for next parameter
    next_url = request.url.path
    if next_url.endswith("/refresh"):
        next_url = next_url.rsplit("/refresh", 1)[0]
    
    login_url = f"/login?error=Session expired, please login again&next={next_url}"
    
    # For HTMX requests, use HX-Redirect header to trigger full page redirect
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
```

## HTMX Endpoints Affected

All HTMX endpoints that require authentication will now properly redirect to login on session timeout:

- `GET /dashboard/refresh` - Dashboard auto-refresh
- `POST /dashboard/load-model` - Load model action
- `POST /dashboard/unload-model` - Unload model action
- `POST /tokens/create` - Create API token
- `DELETE /tokens/{token_id}` - Delete API token
- `GET /logs/refresh` - Logs auto-refresh

## Technical Notes

- **HX-Redirect vs HX-Location**: We use `HX-Redirect` which performs a full page navigation (equivalent to `window.location.href`), not `HX-Location` which would only update the browser history
- **Status code 200**: HTMX processes `HX-*` headers only for 2xx responses; using 401 would cause HTMX to trigger error events instead
- **Empty content**: The response body is empty since HTMX will immediately redirect the browser

## Testing

To test this fix:
1. Login to the dashboard
2. Wait for session to expire (or manually delete the session cookie)
3. Trigger an HTMX action (wait for auto-refresh or click a button)
4. Browser should redirect to login page (full page, not partial)
5. After logging in, dashboard should render correctly

## Files Modified
- `src/llamacontroller/main.py` - Updated HTTP exception handler
