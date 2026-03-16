"""
Database CRUD operations
"""
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timedelta
import secrets
import hashlib

from llamacontroller.db.models import User, APIToken, Session as DBSession, AuditLog

# ==================== User CRUD ====================

def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """Get user by ID"""
    return db.query(User).filter(User.id == user_id).first()

def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """Get user by username"""
    return db.query(User).filter(User.username == username).first()

def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
    """Get list of users"""
    return db.query(User).offset(skip).limit(limit).all()

def create_user(db: Session, username: str, password_hash: str, role: str = "user") -> User:
    """Create new user"""
    user = User(
        username=username,
        password_hash=password_hash,
        role=role
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def update_user(db: Session, user: User) -> User:
    """Update user"""
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    return user

def delete_user(db: Session, user: User) -> None:
    """Delete user"""
    db.delete(user)
    db.commit()

def sync_users_from_config(db: Session, auth_config) -> dict:
    """
    Synchronize users from auth configuration to database
    
    Args:
        db: Database session
        auth_config: AuthConfig object from configuration
    
    Returns:
        dict: Statistics about sync operation (created, updated, total)
    """
    from llamacontroller.auth.utils import hash_password
    
    stats = {"created": 0, "existing": 0, "total": len(auth_config.users)}
    
    for user_config in auth_config.users:
        existing_user = get_user_by_username(db, user_config.username)
        
        if existing_user is not None:
            stats["existing"] += 1
            # User exists - we don't update password to avoid overwriting user changes
            # If you want to force sync passwords, uncomment the following lines:
            # password_hash = hash_password(user_config.password)
            # existing_user.password_hash = password_hash
            # existing_user.role = user_config.role
            # update_user(db, existing_user)
        else:
            # Create new user from config
            password_hash = hash_password(user_config.password)
            create_user(
                db,
                username=user_config.username,
                password_hash=password_hash,
                role=user_config.role
            )
            stats["created"] += 1
    
    return stats

def increment_failed_login(db: Session, user: User, lockout_duration: int = 300) -> User:
    """
    Increment failed login count
    
    Args:
        db: Database session
        user: User object
        lockout_duration: Lockout duration in seconds, default 5 minutes
    """
    user.failed_login_attempts += 1
    
    # Lock account if failed attempts reach 5
    if user.failed_login_attempts >= 5:
        user.locked_until = datetime.utcnow() + timedelta(seconds=lockout_duration)
    
    db.commit()
    db.refresh(user)
    return user

def reset_failed_login(db: Session, user: User) -> User:
    """Reset failed login count"""
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()
    db.refresh(user)
    return user

# ==================== API Token CRUD ====================

def get_api_token_by_id(db: Session, token_id: int) -> Optional[APIToken]:
    """Get token by ID"""
    return db.query(APIToken).filter(APIToken.id == token_id).first()

def get_api_token_by_hash(db: Session, token_hash: str) -> Optional[APIToken]:
    """Get token by hash value"""
    return db.query(APIToken).filter(APIToken.token_hash == token_hash).first()

def get_user_api_tokens(db: Session, user_id: int) -> List[APIToken]:
    """Get all tokens for a user"""
    return db.query(APIToken).filter(APIToken.user_id == user_id).all()

def create_api_token(
    db: Session,
    user_id: int,
    name: str,
    expires_days: Optional[int] = None,
    custom_token: Optional[str] = None
) -> tuple[APIToken, str]:
    """
    Create API token
    
    Args:
        db: Database session
        user_id: User ID
        name: Token name
        expires_days: Expiry days (optional)
        custom_token: Custom token value (optional, auto-generated if not provided)
    
    Returns:
        tuple[APIToken, str]: (database record, raw token)
    """
    # Use custom token or generate random token
    if custom_token:
        raw_token = custom_token
    else:
        # Generate recommended length token (32 bytes = 43 chars base64)
        raw_token = secrets.token_urlsafe(32)
    
    # Calculate hash for storage
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    
    # Calculate expiration time
    expires_at = None
    if expires_days is not None:
        expires_at = datetime.utcnow() + timedelta(days=expires_days)
    
    # Create database record
    api_token = APIToken(
        user_id=user_id,
        token_hash=token_hash,
        name=name,
        expires_at=expires_at
    )
    
    db.add(api_token)
    db.commit()
    db.refresh(api_token)
    
    return api_token, raw_token

def generate_token(length: int = 32) -> str:
    """
    Generate recommended random token
    
    Args:
        length: Byte length (default 32 bytes = ~43 characters)
    
    Returns:
        str: URL-safe base64 encoded token
    """
    return secrets.token_urlsafe(length)

def update_api_token_last_used(db: Session, token: APIToken) -> APIToken:
    """Update token last used time"""
    token.last_used_at = datetime.utcnow()
    db.commit()
    db.refresh(token)
    return token

def update_api_token(db: Session, token: APIToken) -> APIToken:
    """Update token"""
    db.commit()
    db.refresh(token)
    return token

def delete_api_token(db: Session, token: APIToken) -> None:
    """Delete token"""
    db.delete(token)
    db.commit()

def verify_api_token(db: Session, raw_token: str) -> Optional[APIToken]:
    """
    Verify API token
    
    Args:
        db: Database session
        raw_token: Raw token string
    
    Returns:
        APIToken if valid, otherwise None
    """
    # Calculate hash
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    
    # Find token
    token = get_api_token_by_hash(db, token_hash)
    
    if token is None:
        return None
    
    # Check if valid
    if not token.is_valid():
        return None
    
    # Update last used time
    update_api_token_last_used(db, token)
    
    return token

# ==================== Session CRUD ====================

def get_session_by_id(db: Session, session_id: str) -> Optional[DBSession]:
    """Get session by session ID"""
    return db.query(DBSession).filter(DBSession.session_id == session_id).first()

def get_user_sessions(db: Session, user_id: int) -> List[DBSession]:
    """Get all sessions for a user"""
    return db.query(DBSession).filter(DBSession.user_id == user_id).all()

def create_session(
    db: Session,
    user_id: int,
    timeout_seconds: int = 3600,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
) -> DBSession:
    """Create session"""
    session_id = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(seconds=timeout_seconds)
    
    session = DBSession(
        session_id=session_id,
        user_id=user_id,
        expires_at=expires_at,
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    db.add(session)
    db.commit()
    db.refresh(session)
    
    return session

def delete_session(db: Session, session: DBSession) -> None:
    """Delete session"""
    db.delete(session)
    db.commit()

def delete_expired_sessions(db: Session) -> int:
    """Delete all expired sessions"""
    count = db.query(DBSession).filter(
        DBSession.expires_at < datetime.utcnow()
    ).delete()
    db.commit()
    return count

def verify_session(db: Session, session_id: str) -> Optional[DBSession]:
    """
    Verify session
    
    Returns:
        DBSession if valid, otherwise None
    """
    session = get_session_by_id(db, session_id)
    
    if session is None:
        return None
    
    if session.is_expired():
        delete_session(db, session)
        return None
    
    return session

# ==================== Audit Log CRUD ====================

def create_audit_log(
    db: Session,
    action: str,
    success: bool = True,
    user_id: Optional[int] = None,
    resource: Optional[str] = None,
    details: Optional[str] = None,
    ip_address: Optional[str] = None
) -> AuditLog:
    """Create audit log"""
    log = AuditLog(
        user_id=user_id,
        action=action,
        resource=resource,
        details=details,
        ip_address=ip_address,
        success=success
    )
    
    db.add(log)
    db.commit()
    db.refresh(log)
    
    return log

def get_audit_logs(
    db: Session,
    user_id: Optional[int] = None,
    action: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> List[AuditLog]:
    """Get audit logs"""
    query = db.query(AuditLog)
    
    if user_id is not None:
        query = query.filter(AuditLog.user_id == user_id)
    
    if action is not None:
        query = query.filter(AuditLog.action == action)
    
    return query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit).all()

def delete_old_audit_logs(db: Session, days: int = 90) -> int:
    """Delete old audit logs"""
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    count = db.query(AuditLog).filter(
        AuditLog.created_at < cutoff_date
    ).delete()
    db.commit()
    return count
