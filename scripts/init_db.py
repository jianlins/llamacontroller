"""
初始化数据库脚本

创建所有数据库表并从 auth-config.yaml 创建初始用户
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from llamacontroller.db.base import init_db, get_db
from llamacontroller.auth.utils import hash_password
from llamacontroller.db import crud
from llamacontroller.core.config import ConfigManager

def sync_users_from_config():
    """从 auth-config.yaml 同步用户到数据库"""
    db = next(get_db())
    
    try:
        # 加载配置
        config_dir = project_root / "config"
        config_manager = ConfigManager(config_dir=str(config_dir))
        config_manager.load_config()
        auth_config = config_manager.auth
        
        print(f"从配置文件加载了 {len(auth_config.users)} 个用户")
        
        # 同步每个用户
        for user_config in auth_config.users:
            # 检查用户是否已存在
            existing_user = crud.get_user_by_username(db, user_config.username)
            
            if existing_user is not None:
                print(f"✓ 用户已存在: {user_config.username}")
                # 可选：更新密码（如果配置中的密码是明文，我们假设它可能已更改）
                # 注意：这里我们不更新密码，因为用户可能已经在系统中修改了密码
                # 如果需要强制同步，取消下面两行的注释：
                # password_hash = hash_password(user_config.password)
                # existing_user.password_hash = password_hash
                # crud.update_user(db, existing_user)
                continue
            
            # 创建新用户
            password_hash = hash_password(user_config.password)
            
            user = crud.create_user(
                db,
                username=user_config.username,
                password_hash=password_hash,
                role=user_config.role
            )
            
            print(f"✓ 创建用户: {user.username} (角色: {user.role})")
            if user_config.password in ["admin123", "password", "12345"]:
                print(f"  ⚠️  用户 '{user.username}' 使用默认密码，请立即修改！")
        
    except Exception as e:
        print(f"✗ 同步用户失败: {e}")
        raise
    finally:
        db.close()

def main():
    """主函数"""
    print("=== LlamaController 数据库初始化 ===\n")
    
    # 确保 data 目录存在
    data_dir = project_root / "data"
    data_dir.mkdir(exist_ok=True)
    print(f"✓ 数据目录: {data_dir}")
    
    # 初始化数据库（创建所有表）
    try:
        init_db()
        print("✓ 数据库表创建成功")
    except Exception as e:
        print(f"✗ 数据库初始化失败: {e}")
        return 1
    
    # 从配置文件同步用户
    try:
        sync_users_from_config()
    except Exception as e:
        print(f"✗ 同步用户失败: {e}")
        return 1
    
    print("\n=== 初始化完成 ===")
    print("\n下一步:")
    print("1. 启动服务器: python -m src.llamacontroller.main")
    print("2. 使用默认凭据登录: admin / admin123")
    print("3. 立即修改默认密码")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
