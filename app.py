import os
from flask import Flask, request, redirect, url_for, flash, session, jsonify, render_template_string
import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "your-cyberpunk-secret-key")

# --- Neon PostgreSQL 連線與初始化 ---
def get_db_connection():
    DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://user:pass@ep-host.neon.tech/neondb?sslmode=require")
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    # 用戶表
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role VARCHAR(20) DEFAULT 'employee'
        );
    ''')
    # 任務表
    cur.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id SERIAL PRIMARY KEY,
            title VARCHAR(100) NOT NULL,
            description TEXT,
            status VARCHAR(20) DEFAULT 'todo',
            priority VARCHAR(10) DEFAULT 'medium',
            assigned_to INTEGER REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            due_date DATE
        );
    ''')
    # 建立預設帳號
    cur.execute("SELECT * FROM users WHERE username='admin'")
    if not cur.fetchone():
        cur.execute("INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
                    ('admin', generate_password_hash('admin123'), 'admin'))
        cur.execute("INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
                    ('member01', generate_password_hash('member123'), 'employee'))
    conn.commit()
    cur.close()
    conn.close()

try:
    init_db()
except Exception as e:
    print("Database init error:", e)


# --- HTML 內嵌模板定義 (明亮、華麗、多色彩炫風) ---

# 1. 活潑明亮登入頁
LOGIN_HTML = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <title>工作看板 // 登入中心</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { background: linear-gradient(135deg, #f5f7fa 0%, #e4e8f0 100%); }
        .vibrant-glow { box-shadow: 0 15px 35px rgba(99, 102, 241, 0.15); }
    </style>
</head>
<body class="min-h-screen flex items-center justify-center p-4">
    <div class="w-full max-w-md p-8 rounded-3xl bg-white border border-white/60 shadow-2xl vibrant-glow backdrop-blur-lg">
        <div class="text-center mb-8">
            <div class="inline-flex h-14 w-14 rounded-2xl bg-gradient-to-tr from-pink-500 via-purple-500 to-indigo-500 items-center justify-center mb-4 shadow-md shadow-purple-500/20">
                <span class="text-white font-black text-2xl">✨</span>
            </div>
            <h2 class="text-2xl font-black text-slate-800 tracking-wider font-sans">PulseFlow 工作空間</h2>
            <p class="text-xs text-slate-400 mt-1.5 font-medium tracking-widest">TASK MANAGEMENT SYSTEM</p>
        </div>

        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}
            {% for category, message in messages %}
              <div class="p-3 mb-4 text-xs font-semibold rounded-xl bg-rose-50 border border-rose-100 text-rose-500 text-center">{{ message }}</div>
            {% endfor %}
          {% endif %}
        {% endwith %}

        <form method="POST" action="/login" class="space-y-5">
            <div>
                <label class="block text-xs font-bold text-slate-500 mb-1.5 ml-1">帳號 USERNAME</label>
                <input type="text" name="username" placeholder="請輸入使用者帳號" required 
                       class="w-full bg-slate-50 border border-slate-200 rounded-xl p-3.5 text-sm text-slate-700 placeholder-slate-400 focus:outline-none focus:border-indigo-500 focus:bg-white focus:ring-2 focus:ring-indigo-100 transition-all">
            </div>
            <div>
                <label class="block text-xs font-bold text-slate-500 mb-1.5 ml-1">密碼 PASSWORD</label>
                <input type="password" name="password" placeholder="請輸入密碼" required 
                       class="w-full bg-slate-50 border border-slate-200 rounded-xl p-3.5 text-sm text-slate-700 placeholder-slate-400 focus:outline-none focus:border-indigo-500 focus:bg-white focus:ring-2 focus:ring-indigo-100 transition-all">
            </div>
            <button type="submit" class="w-full bg-gradient-to-r from-pink-500 via-purple-500 to-indigo-600 text-white font-bold p-3.5 rounded-xl hover:opacity-95 transition-all shadow-lg shadow-indigo-500/20 text-sm tracking-wider mt-2">
                登入系統 ENTER
            </button>
        </form>
    </div>
</body>
</html>
"""

# 2. 前台員工看板介面
EMPLOYEE_HTML = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <title>✨ 工作看板 // PulseFlow</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        body { background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%); color: #334155; }
        .light-glass { background: rgba(255, 255, 255, 0.75); backdrop-filter: blur(16px); border: 1px solid rgba(255, 255, 255, 0.6); }
        .glow-todo { box-shadow: 0 10px 25px -5px rgba(244, 63, 94, 0.12), 0 8px 10px -6px rgba(244, 63, 94, 0.08); }
        .glow-progress { box-shadow: 0 10px 25px -5px rgba(14, 165, 233, 0.12), 0 8px 10px -6px rgba(14, 165, 233, 0.08); }
        .glow-done { box-shadow: 0 10px 25px -5px rgba(16, 185, 129, 0.12), 0 8px 10px -6px rgba(16, 185, 129, 0.08); }
    </style>
</head>
<body class="p-4 md:p-8 font-sans antialiased">

    <div class="max-w-6xl mx-auto flex justify-between items-center mb-10 light-glass rounded-2xl p-4 px-6 shadow-xl shadow-slate-200/50">
        <div class="flex items-center gap-3.5">
            <div class="h-11 w-11 rounded-xl bg-gradient-to-tr from-pink-500 via-purple-500 to-indigo-500 flex items-center justify-center shadow-md shadow-purple-500/20">
                <i class="fa-solid fa-sparkles text-white text-lg"></i>
            </div>
            <div>
                <h1 class="text-lg font-black tracking-wider text-slate-800">PulseFlow 看板</h1>
                <p class="text-xs text-indigo-600 font-semibold">員工夥伴: @{{ session['username'] }}</p>
            </div>
        </div>
        <a href="/logout" class="text-xs font-bold bg-slate-100 hover:bg-rose-50 text-slate-600 hover:text-rose-600 p-2.5 px-4 rounded-xl transition-all border border-slate-200/60 shadow-sm">
            安全登出 <i class="fa-solid fa-arrow-right-from-bracket ml-1"></i>
        </a>
    </div>

    <div class="max-w-6xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-6">
        
        <div class="space-y-4">
            <div class="flex items-center justify-between px-2">
                <span class="text-xs font-extrabold tracking-wider text-rose-500 bg-rose-50 p-1.5 px-3 rounded-xl border border-rose-100/80"><i class="fa-solid fa-bolt mr-1"></i> 待處理 BACKLOG</span>
                <span class="bg-rose-500 text-white text-xs font-bold px-2.5 py-0.5 rounded-full shadow-sm shadow-rose-500/20" id="c-todo">0</span>
            </div>
            <div class="space-y-4" id="col-todo">
                {% for task in tasks if task.status == 'todo' %}
                    <div class="light-glass glow-todo border-t-4 border-t-rose-400 p-5 rounded-2xl relative group transition-all duration-300 hover:scale-[1.01] hover:shadow-2xl hover:shadow-rose-500/10 bg-white">
                        <div class="flex justify-between items-start mb-2.5">
                            <span class="text-[10px] font-bold px-2 py-0.5 rounded-md bg-rose-50 text-rose-600 border border-rose-100">{{ task.priority | upper }}</span>
                            <span class="text-[11px] font-medium text-slate-400"><i class="fa-regular fa-calendar-days mr-1 text-slate-400"></i>{{ task.due_date or '無期限' }}</span>
                        </div>
                        <h3 class="text-sm font-bold text-slate-800 mb-1.5">{{ task.title }}</h3>
                        <p class="text-xs text-slate-500 leading-relaxed mb-4">{{ task.description or '無描述資訊。' }}</p>
                        <div class="flex gap-2 border-t border-slate-100 pt-3.5 justify-end">
                            <button type="button" onclick="moveTask({{ task.id }}, 'in_progress')" class="cursor-pointer text-xs font-bold p-2 px-4 rounded-xl bg-gradient-to-r from-indigo-500 to-blue-600 text-white hover:opacity-90 transition-all shadow-md shadow-indigo-500/10 active:scale-95">
                                🚀 開始執行
                            </button>
                        </div>
                    </div>
                {% endfor %}
            </div>
        </div>

        <div class="space-y-4">
            <div class="flex items-center justify-between px-2">
                <span class="text-xs font-extrabold tracking-wider text-sky-600 bg-sky-50 p-1.5 px-3 rounded-xl border border-sky-100/80"><i class="fa-solid fa-hourglass-half mr-1"></i> 執行中 PROCESSING</span>
                <span class="bg-sky-500 text-white text-xs font-bold px-2.5 py-0.5 rounded-full shadow-sm shadow-sky-500/20" id="c-progress">0</span>
            </div>
            <div class="space-y-4" id="col-in_progress">
                {% for task in tasks if task.status == 'in_progress' %}
                    <div class="light-glass glow-progress border-t-4 border-t-sky-400 p-5 rounded-2xl relative group transition-all duration-300 hover:scale-[1.01] hover:shadow-2xl hover:shadow-sky-500/10 bg-white">
                        <div class="flex justify-between items-start mb-2.5">
                            <span class="text-[10px] font-bold px-2 py-0.5 rounded-md bg-sky-50 text-sky-600 border border-sky-100">{{ task.priority | upper }}</span>
                            <span class="text-[11px] font-medium text-slate-400"><i class="fa-regular fa-calendar-days mr-1 text-slate-400"></i>{{ task.due_date or '無期限' }}</span>
                        </div>
                        <h3 class="text-sm font-bold text-slate-800 mb-1.5">{{ task.title }}</h3>
                        <p class="text-xs text-slate-500 leading-relaxed mb-4">{{ task.description or '無描述資訊。' }}</p>
                        <div class="flex gap-2 border-t border-slate-100 pt-3.5 justify-end">
                            <button type="button" onclick="moveTask({{ task.id }}, 'todo')" class="cursor-pointer text-xs font-semibold p-1.5 px-3 rounded-xl bg-slate-100 text-slate-600 hover:bg-rose-50 hover:text-rose-500 transition-all border border-slate-200/50">↩ 退回</button>
                            <button type="button" onclick="moveTask({{ task.id }}, 'done')" class="cursor-pointer text-xs font-bold p-1.5 px-3.5 rounded-xl bg-gradient-to-r from-emerald-400 to-teal-500 text-white hover:opacity-90 transition-all shadow-md shadow-emerald-500/10">✓ 回報完成</button>
                        </div>
                    </div>
                {% endfor %}
            </div>
        </div>

        <div class="space-y-4">
            <div class="flex items-center justify-between px-2">
                <span class="text-xs font-extrabold tracking-wider text-emerald-600 bg-emerald-50 p-1.5 px-3 rounded-xl border border-emerald-100/80"><i class="fa-solid fa-circle-check mr-1"></i> 已完結 COMPLETED</span>
                <span class="bg-emerald-500 text-white text-xs font-bold px-2.5 py-0.5 rounded-full shadow-sm shadow-emerald-500/20" id="c-done">0</span>
            </div>
            <div class="space-y-4" id="col-done">
                {% for task in tasks if task.status == 'done' %}
                    <div class="light-glass glow-done border-t-4 border-t-emerald-400 p-5 rounded-2xl relative group opacity-75 transition-all duration-300 bg-slate-50/50">
                        <div class="flex justify-between items-start mb-2.5">
                            <span class="text-[10px] font-bold px-2 py-0.5 rounded-md bg-slate-200 text-slate-500">{{ task.priority | upper }}</span>
                            <span class="text-[11px] font-medium text-slate-400"><i class="fa-regular fa-calendar-days mr-1 text-slate-300"></i>{{ task.due_date or '無期限' }}</span>
                        </div>
                        <h3 class="text-sm font-bold text-slate-400 mb-1.5 line-through">{{ task.title }}</h3>
                        <p class="text-xs text-slate-400 leading-relaxed mb-4">{{ task.description or '' }}</p>
                        <div class="flex gap-2 border-t border-slate-200/60 pt-3.5 justify-end">
                            <button type="button" onclick="moveTask({{ task.id }}, 'in_progress')" class="cursor-pointer text-xs font-semibold p-1.5 px-3 rounded-xl bg-white text-slate-500 hover:text-sky-500 hover:border-sky-200 transition-all border border-slate-200 shadow-sm">重啟任務</button>
                        </div>
                    </div>
                {% endfor %}
            </div>
        </div>

    </div>

    <script>
        async function moveTask(taskId, newStatus) {
            try {
                const response = await fetch('/api/task/' + taskId + '/status', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
                    body: JSON.stringify({ status: newStatus })
                });
                if(response.ok) { window.location.reload(); return; }
                const errData = await response.json();
                alert('變更失敗: ' + (errData.error || '未知錯誤'));
            } catch(e) {
                alert('網頁連線異常，請重新整理頁面再試！');
            }
        }
        function updateCounters() {
            const todoCol = document.getElementById('col-todo');
            const progressCol = document.getElementById('col-in_progress');
            const doneCol = document.getElementById('col-done');
            if(todoCol) document.getElementById('c-todo').innerText = todoCol.children.length;
            if(progressCol) document.getElementById('c-progress').innerText = progressCol.children.length;
            if(doneCol) document.getElementById('c-done').innerText = doneCol.children.length;
        }
        window.addEventListener('DOMContentLoaded', updateCounters);
    </script>
</body>
</html>
"""

# 3. 後台管理控制中心 (全面新增員工 CRUD 面板)
ADMIN_HTML = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <title>⚙️ Control Center // 後台管理</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        body { background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%); color: #334155; }
        .light-glass { background: rgba(255, 255, 255, 0.8); backdrop-filter: blur(16px); border: 1px solid rgba(255, 255, 255, 0.5); }
    </style>
</head>
<body class="p-4 md:p-8 font-sans">

    <div class="max-w-7xl mx-auto flex justify-between items-center mb-8 border-b border-slate-200 pb-6">
        <div>
            <h1 class="text-xl font-black text-slate-800 flex items-center gap-2">
                <i class="fa-solid fa-sliders text-indigo-500"></i> PulseFlow 核心調度後台
            </h1>
            <p class="text-xs text-slate-400 mt-1 font-medium">任務全局監控 ＆ 全體員工帳號 CRUD 整合系統</p>
        </div>
        <div class="flex gap-3">
            <a href="/dashboard" class="bg-gradient-to-r from-indigo-500 to-purple-600 text-white text-xs font-bold p-3 px-5 rounded-xl transition-all shadow-md shadow-indigo-500/10 hover:opacity-95">切換前台看板</a>
            <a href="/logout" class="bg-slate-200 hover:bg-slate-300 text-slate-700 text-xs font-semibold p-3 px-4 rounded-xl transition-all">登出</a>
        </div>
    </div>

    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}
        <div class="max-w-7xl mx-auto mb-6">
        {% for category, message in messages %}
          <div class="p-3.5 text-xs font-bold rounded-xl {% if category=='success' %} bg-emerald-50 border border-emerald-200 text-emerald-600 {% else %} bg-rose-50 border border-rose-200 text-rose-600 {% endif %}">{{ message }}</div>
        {% endfor %}
        </div>
      {% endif %}
    {% endwith %}

    <div class="max-w-7xl mx-auto grid grid-cols-3 gap-4 mb-8">
        <div class="light-glass p-4 rounded-2xl shadow-sm border-l-4 border-l-indigo-500 bg-white">
            <p class="text-[11px] font-bold text-slate-400 uppercase tracking-wider">總任務監控量</p>
            <p class="text-2xl font-black text-slate-800 mt-1">{{ stats.total or 0 }} <span class="text-xs text-slate-400 font-normal">件</span></p>
        </div>
        <div class="light-glass p-4 rounded-2xl shadow-sm border-l-4 border-l-emerald-500 bg-white">
            <p class="text-[11px] font-bold text-emerald-600 uppercase tracking-wider">已完結任務</p>
            <p class="text-2xl font-black text-emerald-600 mt-1">{{ stats.done or 0 }} <span class="text-xs text-slate-400 font-normal">件</span></p>
        </div>
        <div class="light-glass p-4 rounded-2xl shadow-sm border-l-4 border-l-purple-500 bg-white">
            <p class="text-[11px] font-bold text-purple-600 uppercase tracking-wider">在職內部員工</p>
            <p class="text-2xl font-black text-purple-600 mt-1">{{ employees | length }} <span class="text-xs text-slate-400 font-normal">人</span></p>
        </div>
    </div>

    <div class="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-3 gap-8 mb-12">
        <div class="light-glass p-6 rounded-2xl shadow-lg bg-white h-fit">
            <h2 class="text-sm font-black text-slate-800 mb-4 flex items-center gap-2 border-b border-slate-100 pb-3">
                <i class="fa-solid fa-circle-plus text-pink-500 text-base"></i> 發布並指派新任務
            </h2>
            <form action="/admin/task/create" method="POST" class="space-y-4 text-xs font-medium">
                <div>
                    <label class="block font-bold text-slate-600 mb-1.5">任務主旨 *</label>
                    <input type="text" name="title" required placeholder="請輸入任務名稱" class="w-full bg-slate-50 border border-slate-200 rounded-xl p-2.5 text-slate-700 focus:outline-none focus:border-indigo-500 focus:bg-white transition-all">
                </div>
                <div>
                    <label class="block font-bold text-slate-600 mb-1.5">細節敘述</label>
                    <textarea name="description" rows="2" placeholder="請填寫執行細節..." class="w-full bg-slate-50 border border-slate-200 rounded-xl p-2.5 text-slate-700 focus:outline-none focus:border-indigo-500 focus:bg-white transition-all"></textarea>
                </div>
                <div class="grid grid-cols-2 gap-4">
                    <div>
                        <label class="block font-bold text-slate-600 mb-1.5">優先程度</label>
                        <select name="priority" class="w-full bg-slate-50 border border-slate-200 rounded-xl p-2.5 text-slate-700 focus:outline-none focus:border-indigo-500">
                            <option value="low">低優先 (Low)</option>
                            <option value="medium" selected>普通 (Medium)</option>
                            <option value="high">緊急 (High)</option>
                        </select>
                    </div>
                    <div>
                        <label class="block font-bold text-slate-600 mb-1.5">指派專屬成員</label>
                        <select name="assigned_to" class="w-full bg-slate-50 border border-slate-200 rounded-xl p-2.5 text-slate-700 focus:outline-none focus:border-indigo-500">
                            <option value="">-- 公開大廳待領取 --</option>
                            {% for emp in employees %}
                                <option value="{{ emp.id }}">@{{ emp.username }}</option>
                            {% endfor %}
                        </select>
                    </div>
                </div>
                <div>
                    <label class="block font-bold text-slate-600 mb-1.5">截止死線</label>
                    <input type="date" name="due_date" class="w-full bg-slate-50 border border-slate-200 rounded-xl p-2.5 text-slate-700 focus:outline-none focus:border-indigo-500">
                </div>
                <button type="submit" class="w-full bg-gradient-to-r from-pink-500 via-purple-500 to-indigo-600 hover:opacity-95 text-white font-bold p-3 rounded-xl transition-all shadow-md mt-1 text-sm">
                    發布並派單
                </button>
            </form>
        </div>

        <div class="lg:col-span-2 light-glass p-6 rounded-2xl shadow-lg bg-white overflow-x-auto">
            <h2 class="text-sm font-black text-slate-800 mb-4 flex items-center gap-2 border-b border-slate-100 pb-3">
                <i class="fa-solid fa-list-check text-indigo-500 text-base"></i> 全局任務即時監控
            </h2>
            <table class="w-full text-left text-xs text-slate-600">
                <thead class="bg-slate-50 text-slate-500 font-bold border-b border-slate-100">
                    <tr>
                        <th class="p-3">核心任務</th>
                        <th class="p-3">擔當夥伴</th>
                        <th class="p-3">目前進度</th>
                        <th class="p-3">優先級</th>
                        <th class="p-3 text-center">管理</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-slate-100">
                    {% for task in tasks %}
                    <tr class="hover:bg-slate-50/60 transition-all">
                        <td class="p-3">
                            <div class="font-bold text-slate-800 text-sm">{{ task.title }}</div>
                            <div class="text-[11px] text-slate-400 mt-0.5 max-w-[220px] truncate">{{ task.description or '...' }}</div>
                        </td>
                        <td class="p-3 font-semibold text-indigo-600">@{{ task.assignee or '開放領取' }}</td>
                        <td class="p-3">
                            {% if task.status == 'todo' %}
                                <span class="bg-rose-50 text-rose-500 font-bold p-1 px-2 rounded border border-rose-100 text-[11px]">待處理</span>
                            {% elif task.status == 'in_progress' %}
                                <span class="bg-sky-50 text-sky-600 font-bold p-1 px-2 rounded border border-sky-100 text-[11px]">執行中</span>
                            {% else %}
                                <span class="bg-emerald-50 text-emerald-600 font-bold p-1 px-2 rounded border border-emerald-100 text-[11px]">已結案</span>
                            {% endif %}
                        </td>
                        <td class="p-3 font-bold text-slate-400">{{ task.priority | upper }}</td>
                        <td class="p-3 text-center">
                            <form action="/admin/task/delete/{{ task.id }}" method="POST" onsubmit="return confirm('確定移除此任務？')" class="inline">
                                <button type="submit" class="text-slate-400 hover:text-rose-500 transition-all p-1"><i class="fa-regular fa-trash-can"></i></button>
                            </form>
                        </td>
                    </tr>
                    {% else %}
                    <tr><td colspan="5" class="p-6 text-center text-slate-400">系統中目前沒有任何任務</td></tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>

    <div class="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div class="light-glass p-6 rounded-2xl shadow-lg bg-white h-fit border-t-4 border-t-purple-400">
            <h2 class="text-sm font-black text-slate-800 mb-4 flex items-center gap-2 border-b border-slate-100 pb-3">
                <i class="fa-solid fa-user-plus text-purple-500 text-base"></i> <span id="emp-form-title">新增員工帳號</span>
            </h2>
            <form id="employee-form" action="/admin/employee/create" method="POST" class="space-y-4 text-xs font-medium">
                <input type="hidden" id="emp-id" name="employee_id" value="">
                
                <div>
                    <label class="block font-bold text-slate-600 mb-1.5">登入帳號 Username *</label>
                    <input type="text" id="emp-username" name="username" required placeholder="例如: siri_lin" class="w-full bg-slate-50 border border-slate-200 rounded-xl p-2.5 text-slate-700 focus:outline-none focus:border-purple-500 focus:bg-white transition-all">
                </div>
                <div>
                    <label class="block font-bold text-slate-600 mb-1.5">
                        登入密碼 Password <span id="pwd-hint" class="text-slate-400 font-normal">(設定新帳號初始密碼)</span> *
                    </label>
                    <input type="password" id="emp-password" name="password" required placeholder="請輸入密碼" class="w-full bg-slate-50 border border-slate-200 rounded-xl p-2.5 text-slate-700 focus:outline-none focus:border-purple-500 focus:bg-white transition-all">
                </div>
                
                <div class="flex gap-2 pt-2">
                    <button type="submit" id="emp-submit-btn" class="flex-1 bg-gradient-to-r from-purple-500 to-indigo-600 text-white font-bold p-3 rounded-xl transition-all shadow-md text-sm">
                        確認新增建立
                    </button>
                    <button type="button" id="emp-cancel-btn" onclick="resetEmployeeForm()" class="hidden bg-slate-100 hover:bg-slate-200 text-slate-600 font-bold p-3 rounded-xl transition-all text-xs">
                        取消編輯
                    </button>
                </div>
            </form>
        </div>

        <div class="lg:col-span-2 light-glass p-6 rounded-2xl shadow-lg bg-white overflow-x-auto border-t-4 border-t-indigo-400">
            <h2 class="text-sm font-black text-slate-800 mb-4 flex items-center gap-2 border-b border-slate-100 pb-3">
                <i class="fa-solid fa-users-gear text-indigo-500 text-base"></i> 企業現有在職員工名冊
            </h2>
            <table class="w-full text-left text-xs text-slate-600">
                <thead class="bg-slate-50 text-slate-500 font-bold border-b border-slate-100">
                    <tr>
                        <th class="p-3.5">員工ID</th>
                        <th class="p-3.5">內部使用者帳號</th>
                        <th class="p-3.5">權限類別</th>
                        <th class="p-3.5 text-center">操作管理</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-slate-100">
                    {% for emp in employees %}
                    <tr class="hover:bg-slate-50/60 transition-all">
                        <td class="p-3.5 font-mono text-slate-400">#{{ emp.id }}</td>
                        <td class="p-3.5 font-bold text-slate-800">
                            <span class="inline-block h-2 w-2 rounded-full bg-emerald-400 mr-2"></span>@{{ emp.username }}
                        </td>
                        <td class="p-3.5">
                            <span class="bg-purple-50 text-purple-600 border border-purple-100 font-semibold p-1 px-2.5 rounded-full text-[11px]">內部職員</span>
                        </td>
                        <td class="p-3.5 text-center flex items-center justify-center gap-4">
                            <button type="button" onclick="startEditEmployee({{ emp.id }}, '{{ emp.username }}')" class="text-indigo-500 hover:text-indigo-700 font-bold transition-all flex items-center gap-1">
                                <i class="fa-regular fa-pen-to-square"></i> 編輯
                            </button>
                            
                            <form action="/admin/employee/delete/{{ emp.id }}" method="POST" onsubmit="return confirm('警告！刪除此員工帳號會將原本指派給他的任務釋放為「未指派」狀態，確定移除此人？')" class="inline">
                                <button type="submit" class="text-slate-400 hover:text-rose-500 font-bold transition-all flex items-center gap-1">
                                    <i class="fa-regular fa-trash-can"></i> 註銷
                                </button>
                            </form>
                        </td>
                    </tr>
                    {% else %}
                    <tr><td colspan="4" class="p-6 text-center text-slate-400">目前尚無登記任何員工帳號</td></tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>

    <script>
        function startEditEmployee(id, username) {
            document.getElementById('emp-form-title').innerText = "編輯員工資料 // 重設密碼";
            document.getElementById('emp-id').value = id;
            document.getElementById('emp-username').value = username;
            
            // 變更表單發送的後端路徑為 Update 機制
            document.getElementById('employee-form').action = "/admin/employee/update";
            
            // 調整密碼輸入要求：更新時不強迫更改密碼
            document.getElementById('emp-password').required = false;
            document.getElementById('emp-password').placeholder = "若不修改密碼請留空";
            document.getElementById('pwd-hint').innerHTML = "(要重設密碼請輸入新密碼，不改留空)";
            
            document.getElementById('emp-submit-btn').innerText = "儲存變更資料";
            document.getElementById('emp-submit-btn').className = "flex-1 bg-gradient-to-r from-indigo-500 to-sky-500 text-white font-bold p-3 rounded-xl transition-all shadow-md text-sm";
            document.getElementById('emp-cancel-btn').classList.remove('hidden');
        }

        function resetEmployeeForm() {
            document.getElementById('emp-form-title').innerText = "新增員工帳號";
            document.getElementById('emp-id').value = "";
            document.getElementById('employee-form').reset();
            
            document.getElementById('employee-form').action = "/admin/employee/create";
            document.getElementById('emp-password').required = true;
            document.getElementById('emp-password').placeholder = "請輸入密碼";
            document.getElementById('pwd-hint').innerHTML = "(設定新帳號初始密碼)";
            
            document.getElementById('emp-submit-btn').innerText = "確認新增建立";
            document.getElementById('emp-submit-btn').className = "w-full bg-gradient-to-r from-purple-500 to-indigo-600 text-white font-bold p-3 rounded-xl transition-all shadow-md text-sm";
            document.getElementById('emp-cancel-btn').classList.add('hidden');
        }
    </script>

</body>
</html>
"""


# --- Flask 路由控制邏輯 ---

@app.route('/')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('admin_dashboard') if session.get('role') == 'admin' else url_for('employee_dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        cur.close()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            return redirect(url_for('home'))
        else:
            flash('帳號密碼不正確', 'danger')
    return render_template_string(LOGIN_HTML)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def employee_dashboard():
    if 'user_id' not in session or session.get('role') != 'employee':
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT * FROM tasks 
        WHERE assigned_to = %s OR assigned_to IS NULL 
        ORDER BY due_date ASC, id DESC
    ''', (session['user_id'],))
    tasks = cur.fetchall()
    cur.close()
    conn.close()
    
    return render_template_string(EMPLOYEE_HTML, tasks=tasks)

@app.route('/api/task/<int:task_id>/status', methods=['POST'])
def update_task_status(task_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json(force=True) or {}
    new_status = data.get('status')
    
    if not new_status:
        return jsonify({'error': 'Missing status field'}), 400
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        if session.get('role') == 'admin':
            cur.execute("UPDATE tasks SET status = %s WHERE id = %s", (new_status, task_id))
        else:
            cur.execute('''
                UPDATE tasks 
                SET status = %s, assigned_to = %s 
                WHERE id = %s
            ''', (new_status, session['user_id'], task_id))
        
        conn.commit()
        updated = cur.rowcount
        cur.close()
        conn.close()
        
        if updated > 0:
            return jsonify({'success': True, 'message': 'Status updated successfully'})
        else:
            return jsonify({'error': 'Task not found in system'}), 400
            
    except Exception as db_err:
        if conn:
            conn.rollback()
        return jsonify({'error': f'Database error: {str(db_err)}'}), 400


# --- 【後台核心】管理者控制台與 CRUD 功能 ---

@app.route('/admin')
def admin_dashboard():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # 1. 撈取全部任務
    cur.execute('''
        SELECT t.*, u.username as assignee 
        FROM tasks t 
        LEFT JOIN users u ON t.assigned_to = u.id 
        ORDER BY t.id DESC
    ''')
    tasks = cur.fetchall()
    
    # 2. 撈取全體內部員工名冊 (Read)
    cur.execute("SELECT id, username FROM users WHERE role = 'employee' ORDER BY id DESC")
    employees = cur.fetchall()
    
    # 3. 數據統計
    cur.execute("SELECT COUNT(*) as total, SUM(CASE WHEN status='done' THEN 1 ELSE 0 END) as done FROM tasks")
    stats = cur.fetchone()
    
    cur.close()
    conn.close()
    
    return render_template_string(ADMIN_HTML, tasks=tasks, employees=employees, stats=stats)

# 【後台任務 CRUD】建立
@app.route('/admin/task/create', methods=['POST'])
def create_task():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    
    title = request.form['title']
    description = request.form['description']
    priority = request.form['priority']
    assigned_to = request.form['assigned_to'] or None
    due_date = request.form['due_date'] or None
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO tasks (title, description, priority, assigned_to, due_date)
        VALUES (%s, %s, %s, %s, %s)
    ''', (title, description, priority, assigned_to, due_date))
    conn.commit()
    cur.close()
    conn.close()
    flash('任務指派成功！', 'success')
    return redirect(url_for('admin_dashboard'))

# 【後台任務 CRUD】刪除
@app.route('/admin/task/delete/<int:task_id>', methods=['POST'])
def delete_task(task_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
    conn.commit()
    cur.close()
    conn.close()
    flash('任務已成功刪除。', 'success')
    return redirect(url_for('admin_dashboard'))


# --- ✨ 追加模組：員工帳號 (Employee CRUD) 控制器路由 ---

# 1. 【員工 CRUD - Create】新增內部夥伴
@app.route('/admin/employee/create', methods=['POST'])
def admin_create_employee():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    
    username = request.form['username'].strip()
    password = request.form['password']
    
    if not username or not password:
        flash('帳號或密碼欄位不可為空！', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # 檢查是否有重複名稱
        cur.execute("SELECT id FROM users WHERE username = %s", (username,))
        if cur.fetchone():
            flash(f'此帳號名稱 "@{username}" 已被佔用，請換個名字！', 'danger')
        else:
            hashed_pwd = generate_password_hash(password)
            cur.execute("INSERT INTO users (username, password, role) VALUES (%s, %s, 'employee')", (username, hashed_pwd))
            conn.commit()
            flash(f'成功新增內部夥伴: @{username}！', 'success')
    except Exception as e:
        flash(f'系統異常: {str(e)}', 'danger')
    finally:
        cur.close()
        conn.close()
        
    return redirect(url_for('admin_dashboard'))

# 2. 【員工 CRUD - Update】修改基本資料與重設密碼
@app.route('/admin/employee/update', methods=['POST'])
def admin_update_employee():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    
    emp_id = request.form.get('employee_id')
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    
    if not emp_id or not username:
        flash('資料損毀，更新失敗！', 'danger')
        return redirect(url_for('admin_dashboard'))
        
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        if password:
            # 管理員輸入了新密碼 -> 同步更新使用者名稱與新密碼
            hashed_pwd = generate_password_hash(password)
            cur.execute("UPDATE users SET username = %s, password = %s WHERE id = %s AND role='employee'", (username, hashed_pwd, emp_id))
        else:
            # 密碼留空 -> 只更新使用者帳號名稱
            cur.execute("UPDATE users SET username = %s WHERE id = %s AND role='employee'", (username, emp_id))
            
        conn.commit()
        flash('員工資料與憑證已成功儲存變更。', 'success')
    except Exception as e:
        flash(f'更新出錯（可能名稱與他人衝突）: {str(e)}', 'danger')
    finally:
        cur.close()
        conn.close()
        
    return redirect(url_for('admin_dashboard'))

# 3. 【員工 CRUD - Delete】註銷移除帳號
@app.route('/admin/employee/delete/<int:emp_id>', methods=['POST'])
def admin_delete_employee():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # 執行刪除（受限於 tasks 表的 FOREIGN KEY ... REFERENCES users(id) ON DELETE SET NULL，
        # 該職員原本持有的任務將會被自動設為 NULL 放回大廳，不會造成資料庫潰散，非常安全！）
        cur.execute("DELETE FROM users WHERE id = %s AND role = 'employee'", (emp_id,))
        conn.commit()
        flash('該員工帳號已成功自系統內註銷移除。', 'success')
    except Exception as e:
        flash(f'註銷失敗: {str(e)}', 'danger')
    finally:
        cur.close()
        conn.close()
        
    return redirect(url_for('admin_dashboard'))


if __name__ == '__main__':
    app.run(debug=True)