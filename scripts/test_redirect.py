#!/usr/bin/env python3
"""
测试登录超时和无效URL重定向功能

这个脚本测试：
1. 未登录时访问受保护页面应重定向到登录页
2. 访问无效URL应重定向到登录页
3. 登录后应重定向到原始请求的页面
"""

import requests
import sys
from urllib.parse import urlparse, parse_qs

BASE_URL = "http://localhost:3000"

def test_protected_page_redirect():
    """测试访问受保护页面时的重定向"""
    print("\n=== 测试1: 访问受保护页面（未登录） ===")
    
    # 不带认证信息访问 dashboard
    response = requests.get(f"{BASE_URL}/dashboard", allow_redirects=False)
    
    if response.status_code == 302:
        location = response.headers.get("Location", "")
        print(f"✓ 状态码: {response.status_code} (重定向)")
        print(f"✓ 重定向到: {location}")
        
        # 检查是否重定向到登录页面并包含错误信息
        if "/login" in location and "error" in location:
            print("✓ 正确重定向到登录页面并显示错误信息")
            
            # 检查是否包含 next 参数
            parsed = urlparse(location)
            query = parse_qs(parsed.query)
            if "next" in query and "/dashboard" in query["next"][0]:
                print(f"✓ 包含 next 参数: {query['next'][0]}")
                return True
            else:
                print("✗ 缺少 next 参数")
                return False
        else:
            print("✗ 重定向目标不正确")
            return False
    else:
        print(f"✗ 状态码: {response.status_code} (应为 302)")
        return False

def test_invalid_url_redirect():
    """测试访问无效URL时的重定向"""
    print("\n=== 测试2: 访问无效URL ===")
    
    # 访问不存在的页面
    response = requests.get(
        f"{BASE_URL}/nonexistent-page",
        headers={"Accept": "text/html"},
        allow_redirects=False
    )
    
    if response.status_code == 302:
        location = response.headers.get("Location", "")
        print(f"✓ 状态码: {response.status_code} (重定向)")
        print(f"✓ 重定向到: {location}")
        
        if "/login" in location and "error" in location:
            print("✓ 正确重定向到登录页面并显示错误信息")
            return True
        else:
            print("✗ 重定向目标不正确")
            return False
    else:
        print(f"✗ 状态码: {response.status_code} (应为 302)")
        return False

def test_login_with_next():
    """测试登录后重定向到原始页面"""
    print("\n=== 测试3: 登录后重定向到原始页面 ===")
    
    # 首先获取登录页面（带 next 参数）
    response = requests.get(
        f"{BASE_URL}/login?next=/tokens&error=请先登录",
        allow_redirects=False
    )
    
    if response.status_code == 200:
        print("✓ 成功获取登录页面")
        
        # 检查页面内容是否包含隐藏的 next 字段
        if 'name="next"' in response.text and 'value="/tokens"' in response.text:
            print("✓ 登录表单包含 next 参数")
            return True
        else:
            print("✗ 登录表单缺少 next 参数")
            return False
    else:
        print(f"✗ 状态码: {response.status_code} (应为 200)")
        return False

def test_tokens_page_redirect():
    """测试访问 tokens 页面的重定向"""
    print("\n=== 测试4: 访问 tokens 页面（未登录） ===")
    
    response = requests.get(f"{BASE_URL}/tokens", allow_redirects=False)
    
    if response.status_code == 302:
        location = response.headers.get("Location", "")
        print(f"✓ 状态码: {response.status_code} (重定向)")
        print(f"✓ 重定向到: {location}")
        
        if "/login" in location:
            parsed = urlparse(location)
            query = parse_qs(parsed.query)
            if "next" in query and "/tokens" in query["next"][0]:
                print(f"✓ 包含正确的 next 参数: {query['next'][0]}")
                return True
            else:
                print("✗ next 参数不正确")
                return False
        else:
            print("✗ 重定向目标不正确")
            return False
    else:
        print(f"✗ 状态码: {response.status_code} (应为 302)")
        return False

def test_api_endpoints_return_json():
    """测试 API 端点返回 JSON 而不是重定向"""
    print("\n=== 测试5: API 端点返回 JSON 错误 ===")
    
    response = requests.get(
        f"{BASE_URL}/api/v1/models/status",
        headers={"Accept": "application/json"},
        allow_redirects=False
    )
    
    print(f"状态码: {response.status_code}")
    
    # API 端点应返回 401 JSON 响应，而不是重定向
    if response.status_code == 401:
        try:
            data = response.json()
            print(f"✓ 返回 JSON 响应: {data}")
            return True
        except:
            print("✗ 响应不是有效的 JSON")
            return False
    else:
        print(f"✗ 状态码应为 401，实际为: {response.status_code}")
        return False

def main():
    """运行所有测试"""
    print("=" * 60)
    print("LlamaController 重定向功能测试")
    print("=" * 60)
    print(f"\n测试目标: {BASE_URL}")
    print("\n确保服务器正在运行...")
    
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✓ 服务器运行正常\n")
        else:
            print(f"✗ 服务器响应异常: {response.status_code}")
            sys.exit(1)
    except Exception as e:
        print(f"✗ 无法连接到服务器: {e}")
        print("\n请先启动服务器:")
        print("  python run.py")
        sys.exit(1)
    
    # 运行测试
    results = []
    results.append(("受保护页面重定向", test_protected_page_redirect()))
    results.append(("无效URL重定向", test_invalid_url_redirect()))
    results.append(("登录页面 next 参数", test_login_with_next()))
    results.append(("Tokens页面重定向", test_tokens_page_redirect()))
    results.append(("API端点返回JSON", test_api_endpoints_return_json()))
    
    # 显示结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{status} - {name}")
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n✓ 所有测试通过！")
        sys.exit(0)
    else:
        print(f"\n✗ {total - passed} 个测试失败")
        sys.exit(1)

if __name__ == "__main__":
    main()
