"""
生成Web UI模板HTML内容的脚本
一次性填充所有模板文件
"""

import os
from pathlib import Path

# 模板基础路径
TEMPLATE_DIR = Path("src/llamacontroller/web/templates")

# 模板内容定义
TEMPLATES = {
    "login.html": """{% extends "base.html" %}
{% block title %}登录 - LlamaController{% endblock %}
{% block content %}
<div class="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4">
    <div class="max-w-md w-full space-y-8">
        <div><h2 class="text-center text-3xl font-bold text-gray-900">LlamaController</h2>
            <p class="mt-2 text-center text-sm text-gray-600">登录以管理 llama.cpp 模型</p></div>
        {% if error %}<div class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">{{ error }}</div>{% endif %}
        <form method="POST" action="/login" class="mt-8 space-y-6">
            <div class="rounded-md shadow-sm -space-y-px">
                <div><input id="username" name="username" type="text" required class="appearance-none rounded-t-md relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm" placeholder="用户名"></div>
                <div><input id="password" name="password" type="password" required class="appearance-none rounded-b-md relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm" placeholder="密码"></div>
            </div>
            <button type="submit" class="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700">登录</button>
        </form>
    </div>
</div>
{% endblock %}""",

    "dashboard.html": """{% extends "base.html" %}
{% block title %}仪表板 - LlamaController{% endblock %}
{% block content %}
<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
    <div class="mb-8"><h1 class="text-3xl font-bold text-gray-900">模型管理仪表板</h1>
        <p class="mt-2 text-gray-600">管理和切换 llama.cpp 模型</p></div>
    <div id="model-status-container" hx-get="/dashboard" hx-trigger="load" hx-swap="innerHTML">
        {% include 'partials/model_status.html' %}
    </div>
    <div class="mt-8 bg-white shadow overflow-hidden sm:rounded-lg">
        <div class="px-4 py-5 sm:px-6"><h3 class="text-lg font-medium text-gray-900">可用模型</h3></div>
        <div class="border-t border-gray-200">
            <ul class="divide-y divide-gray-200">
                {% for model in available_models %}
                <li class="px-4 py-4">
                    <div class="flex items-center justify-between">
                        <div class="flex-1">
                            <p class="text-sm font-medium text-indigo-600">{{ model.name }}</p>
                            <p class="text-sm text-gray-500">ID: {{ model.id }}</p>
                            <p class="text-xs text-gray-400 mt-1">{{ model.metadata.description }}</p>
                        </div>
                        <div class="ml-4">
                            {% if current_model and current_model.id == model.id %}
                            <span class="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800">运行中</span>
                            {% else %}
                            <button hx-post="/dashboard/load-model" hx-vals='{"model_id": "{{ model.id }}"}' hx-target="#model-status-container" class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700">加载模型</button>
                            {% endif %}
                        </div>
                    </div>
                </li>
                {% endfor %}
            </ul>
        </div>
    </div>
</div>
{% endblock %}""",

    "tokens.html": """{% extends "base.html" %}
{% block title %}API令牌管理 - LlamaController{% endblock %}
{% block content %}
<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
    <div class="mb-8"><h1 class="text-3xl font-bold text-gray-900">API 令牌管理</h1>
        <p class="mt-2 text-gray-600">创建和管理 API 访问令牌</p></div>
    <div class="bg-white shadow sm:rounded-lg mb-6">
        <div class="px-4 py-5 sm:p-6"><h3 class="text-lg font-medium text-gray-900 mb-4">创建新令牌</h3>
            <form hx-post="/tokens/create" hx-target="#token-list" class="space-y-4">
                <div><label class="block text-sm font-medium text-gray-700">令牌名称</label>
                    <input type="text" name="token_name" required class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm" placeholder="例如: 我的应用令牌"></div>
                <div><label class="block text-sm font-medium text-gray-700">过期天数（可选）</label>
                    <input type="number" name="expires_days" class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm" placeholder="留空表示永不过期"></div>
                <button type="submit" class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700">创建令牌</button>
            </form>
        </div>
    </div>
    <div id="token-list">{% include 'partials/token_list.html' %}</div>
</div>
{% endblock %}""",

    "logs.html": """{% extends "base.html" %}
{% block title %}系统日志 - LlamaController{% endblock %}
{% block content %}
<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
    <div class="mb-8 flex justify-between items-center">
        <div><h1 class="text-3xl font-bold text-gray-900">System Log</h1>
            <p class="mt-2 text-gray-600">查看 llama.cpp 服务器日志</p></div>
        <button hx-get="/logs/refresh" hx-target="#logs-content" class="inline-flex items-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50">刷新日志</button>
    </div>
    <div id="logs-content" hx-get="/logs/refresh" hx-trigger="load">{% include 'partials/logs_content.html' %}</div>
</div>
{% endblock %}""",

    "partials/model_status.html": """<div class="bg-white shadow sm:rounded-lg">
    <div class="px-4 py-5 sm:p-6">
        <h3 class="text-lg font-medium text-gray-900 mb-4">Current Model Status</h3>
        {% if current_model %}
        <div class="bg-green-50 border border-green-200 rounded-md p-4">
            <div class="flex items-center justify-between">
                <div>
                    <p class="text-sm font-medium text-green-800">Model loaded</p>
                    <p class="text-lg font-bold text-green-900 mt-1">{{ current_model.name }}</p>
                    <p class="text-sm text-green-700 mt-1">ID: {{ current_model.id }}</p>
                </div>
                <div class="flex space-x-2">
                    <button hx-post="/dashboard/unload-model" hx-target="#model-status-container" class="inline-flex items-center px-3 py-2 border border-transparent text-sm font-medium rounded-md text-red-700 bg-red-100 hover:bg-red-200">卸载模型</button>
                </div>
            </div>
        </div>
        {% else %}
        <div class="bg-yellow-50 border border-yellow-200 rounded-md p-4">
            <p class="text-sm font-medium text-yellow-800">No Model Loaded Currently</p>
            <p class="text-sm text-yellow-700 mt-1">Please select a model to load from the list below</p>
        </div>
        {% endif %}
    </div>
</div>""",

    "partials/token_list.html": """<div class="bg-white shadow overflow-hidden sm:rounded-md">
    <ul class="divide-y divide-gray-200">
        {% for token in tokens %}
        <li class="px-4 py-4">
            <div class="flex items-center justify-between">
                <div class="flex-1">
                    <p class="text-sm font-medium text-gray-900">{{ token.name }}</p>
                    <p class="text-xs text-gray-500 mt-1">创建于: {{ token.created_at.strftime('%Y-%m-%d %H:%M') }}</p>
                    {% if token.last_used_at %}<p class="text-xs text-gray-500">最后使用: {{ token.last_used_at.strftime('%Y-%m-%d %H:%M') }}</p>{% endif %}
                    {% if token.expires_at %}<p class="text-xs text-gray-500">过期于: {{ token.expires_at.strftime('%Y-%m-%d %H:%M') }}</p>{% endif %}
                </div>
                <div class="ml-4 flex items-center space-x-2">
                    {% if token.is_active %}
                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">激活</span>
                    {% else %}
                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">停用</span>
                    {% endif %}
                    <button hx-delete="/tokens/{{ token.id }}" hx-target="#token-list" hx-confirm="确定要删除此令牌吗？" class="inline-flex items-center px-3 py-1 border border-transparent text-sm font-medium rounded-md text-red-700 bg-red-100 hover:bg-red-200">删除</button>
                </div>
            </div>
        </li>
        {% else %}
        <li class="px-4 py-4 text-sm text-gray-500 text-center">暂无API令牌</li>
        {% endfor %}
    </ul>
</div>""",

    "partials/logs_content.html": """<div class="bg-gray-900 rounded-lg shadow-lg p-4">
    <pre class="text-green-400 text-sm font-mono overflow-x-auto">{% if logs %}{% for line in logs %}{{ line }}
{% endfor %}{% else %}暂无日志数据{% endif %}</pre>
</div>"""
}


def main():
    """生成所有模板文件"""
    print("开始生成Web UI模板...")
    
    for filename, content in TEMPLATES.items():
        filepath = TEMPLATE_DIR / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✓ 已生成: {filepath}")
    
    print(f"\n完成! 共生成 {len(TEMPLATES)} 个模板文件")


if __name__ == "__main__":
    main()
