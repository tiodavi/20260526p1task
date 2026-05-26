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
            status VARCHAR(20) DEFAULT 'todo', -- 'todo', 'in_progress', 'done'
            priority VARCHAR(10) DEFAULT 'medium', -- 'low', 'medium', 'high'
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


# --- HTML 內嵌模板定義 (年輕人喜愛的極簡暗黑/潮流霓虹風) ---

# 1. 潮流登入頁
LOGIN_HTML = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <title>ENTER THE FLOW // 登入</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { background-color: #0B0F19; }
        .glow-btn { box-shadow: 0 0 20px rgba(99, 102, 241, 0.4); }
    </style>
</head>
<body class="min-h-screen flex items-center justify-center p-4">
    <div class="w-full max-w-md p-8 rounded-3xl bg-slate-800/50 border border-white/5 shadow-2xl backdrop-blur-md">
        <div class="text-center mb-8">
            <div class="inline-flex h-12 w-12 rounded-2xl bg-gradient-to-tr from-indigo-500 to-purple-500 items-center justify-center mb-4">
                <span class="text-white font-black text-xl">⚡</span>
            </div>
            <h2 class="text-2xl font-black text-white tracking-widest font-mono">PULSE_FLOW</h2>
            <p class="text-xs text-gray-500 mt-1">TASK MANAGEMENT SYSTEM</p>
        </div>

        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}
            {% for category, message in messages %}
              <div class="p-3 mb-4 text-xs rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-center">{{ message }}</div>
            {% endfor %}
          {% endif %}
        {% endwith %}

        <form method="POST" action="/login" class="space-y-5">
            <div>
                <input type="text" name="username" placeholder="USERNAME" required 
                       class="w-full bg-slate-900/80 border border-slate-700/60 rounded-xl p-3.5 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all">
            </div>
            <div>
                <input type="password" name="password" placeholder="PASSWORD" required 
                       class="w-full bg-slate-900/80 border border-slate-700/60 rounded-xl p-3.5 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all">
            </div>
            <button type="submit" class="w-full bg-gradient-to-r from-indigo-500 to-purple-600 text-white font-bold p-3.5 rounded-xl hover:opacity-90 transition-all glow-btn text-sm tracking-wider">
                SIGN_IN
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
    <title>⚡ Workspace // PulseFlow</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        body { background-color: #0B0F19; color: #E2E8F0; }
        .glass { background: rgba(30, 41, 59, 0.45); backdrop-filter: blur(12px); border: 1px solid rgba(255,255,255,0.04); }
        .glow-todo { box-shadow: 0 0 15px rgba(239, 68, 68, 0.08); }
        .glow-progress { box-shadow: 0 0 15px rgba(245, 158, 11, 0.08); }
        .glow-done { box-shadow: 0 0 15px rgba(16, 185, 129, 0.08); }
    </style>
</head>
<body class="p-4 md:p-8 font-sans antialiased">

    <div class="max-w-6xl mx-auto flex justify-between items-center mb-10 glass rounded-2xl p-4 px-6 shadow-2xl">
        <div class="flex items-center gap-3">
            <div class="h-10 w-10 rounded-xl bg-gradient-to-tr from-indigo-500 to-purple-500 flex items-center justify-center shadow-lg shadow-indigo-500/20">
                <i class="fa-solid fa-bolt text-white"></i>
            </div>
            <div>
                <h1 class="text-base font-black tracking-wider text-white font-mono">PULSE_FLOW</h1>
                <p class="text-xs text-indigo-400 font-mono">@{{ session['username'] }} <span class="text-gray-600">(Employee)</span></p>
            </div>
        </div>
        <a href="/logout" class="text-xs font-mono bg-white/5 hover:bg-red-500/20 text-gray-400 hover:text-red-400 border border-white/5 p-2 px-4 rounded-xl transition-all">
            LOGOUT <i class="fa-solid fa-arrow-right-from-bracket ml-1"></i>
        </a>
    </div>

    <div class="max-w-6xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-6">
        
        <div class="space-y-4">
            <div class="flex items-center justify-between px-2 font-mono">
                <span class="text-xs font-bold tracking-widest text-red-400">⚡ BACKLOG / TODO</span>
                <span class="bg-red-500/10 text-red-400 text-xs px-2 py-0.5 rounded-full border border-red-500/10" id="c-todo">0</span>
            </div>
            <div class="space-y-4 font-sans" id="col-todo">
                {% for task in tasks if task.status == 'todo' %}
                    <div class="glass glow-todo border border-red-500/20 p-5 rounded-2xl relative group transition-all duration-300 hover:scale-[1.01]">
                        <div class="flex justify-between items-start mb-2">
                            <span class="text-[10px] px-2 py-0.5 rounded bg-red-500/10 text-red-400 font-mono">{{ task.priority | upper }}</span>
                            <span class="text-[11px] text-gray-500 font-mono"><i class="fa-regular fa-calendar mr-1"></i>{{ task.due_date or 'No Due' }}</span>
                        </div>
                        <h3 class="text-sm font-bold text-white mb-1">{{ task.title }}</h3>
                        <p class="text-xs text-gray-400 leading-relaxed mb-4">{{ task.description or '無描述。' }}</p>
                        <div class="flex gap-2 border-t border-white/5 pt-3 justify-end">
                            <button type="button" onclick="moveTask({{ task.id }}, 'in_progress')" class="cursor-pointer text-[11px] font-medium p-1 px-2.5 rounded-lg bg-indigo-500/10 text-indigo-400 hover:bg-indigo-500 hover:text-white transition-all">🚀 開始執行</button>
                        </div>
                    </div>
                {% endfor %}
            </div>
        </div>

        <div class="space-y-4">
            <div class="flex items-center justify-between px-2 font-mono">
                <span class="text-xs font-bold tracking-widest text-amber-400">⏳ IN_PROGRESS</span>
                <span class="bg-amber-500/10 text-amber-400 text-xs px-2 py-0.5 rounded-full border border-amber-500/10" id="c-progress">0</span>
            </div>
            <div class="space-y-4 font-sans" id="col-in_progress">
                {% for task in tasks if task.status == 'in_progress' %}
                    <div class="glass glow-progress border border-amber-500/20 p-5 rounded-2xl relative group transition-all duration-300 hover:scale-[1.01]">
                        <div class="flex justify-between items-start mb-2">
                            <span class="text-[10px] px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 font-mono">{{ task.priority | upper }}</span>
                            <span class="text-[11px] text-gray-500 font-mono"><i class="fa-regular fa-calendar mr-1"></i>{{ task.due_date or 'No Due' }}</span>
                        </div>
                        <h3 class="text-sm font-bold text-white mb-1">{{ task.title }}</h3>
                        <p class="text-xs text-gray-400 leading-relaxed mb-4">{{ task.description or '無描述。' }}</p>
                        <div class="flex gap-2 border-t border-white/5 pt-3 justify-end">
                            <button type="button" onclick="moveTask({{ task.id }}, 'todo')" class="cursor-pointer text-[11px] font-medium p-1 px-2.5 rounded-lg bg-white/5 text-gray-400 hover:bg-red-500/20 hover:text-red-400 transition-all">↩ 退回</button>
                            <button type="button" onclick="moveTask({{ task.id }}, 'done')" class="cursor-pointer text-[11px] font-medium p-1 px-2.5 rounded-lg bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500 hover:text-white transition-all">✓ 回報完成</button>
                        </div>
                    </div>
                {% endfor %}
            </div>
        </div>

        <div class="space-y-4">
            <div class="flex items-center justify-between px-2 font-mono">
                <span class="text-xs font-bold tracking-widest text-emerald-400">✨ COMPLETED</span>
                <span class="bg-emerald-500/10 text-emerald-400 text-xs px-2 py-0.5 rounded-full border border-emerald-500/10" id="c-done">0</span>
            </div>
            <div class="space-y-4 font-sans" id="col-done">
                {% for task in tasks if task.status == 'done' %}
                    <div class="glass glow-done border border-emerald-500/20 p-5 rounded-2xl relative group opacity-70 transition-all duration-300">
                        <div class="flex justify-between items-start mb-2">
                            <span class="text-[10px] px-2 py-0.5 rounded bg-gray-800 text-gray-500 font-mono">{{ task.priority | upper }}</span>
                            <span class="text-[11px] text-gray-600 font-mono"><i class="fa-regular fa-calendar mr-1"></i>{{ task.due_date or 'No Due' }}</span>
                        </div>
                        <h3 class="text-sm font-bold text-gray-400 mb-1 line-through">{{ task.title }}</h3>
                        <p class="text-xs text-gray-500 leading-relaxed mb-4">{{ task.description or '' }}</p>
                        <div class="flex gap-2 border-t border-white/5 pt-3 justify-end">
                            <button type="button" onclick="moveTask({{ task.id }}, 'in_progress')" class="cursor-pointer text-[11px] font-medium p-1 px-2.5 rounded-lg bg-white/5 text-gray-500 hover:text-amber-400 transition-all">重启任務</button>
                        </div>
                    </div>
                {% endfor %}
            </div>
        </div>

    </div>

    <script>
        async function moveTask(taskId, newStatus) {
            try {
                const response = await fetch(`/api/task/${taskId}/status`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ status: newStatus })
                });
                if(response.ok) { 
                    window.location.reload(); 
                    return;
                }
                alert('任務變更失敗，請重試！');
            } catch(e) {
                alert('網路錯誤，請稍後重試！');
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

# 3. 後台管理控制中心
ADMIN_HTML = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <title>⚙️ Control Center // 後台管理</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        body { background-color: #0B0F19; color: #E2E8F0; }
        .glass { background: rgba(30, 41, 59, 0.45); backdrop-filter: blur(12px); border: 1px solid rgba(255,255,255,0.04); }
    </style>
</head>
<body class="p-4 md:p-8 font-sans">

    <div class="max-w-7xl mx-auto flex justify-between items-center mb-8 border-b border-slate-800 pb-6">
        <div>
            <h1 class="text-xl font-black text-white font-mono flex items-center gap-2">
                <i class="fa-solid fa-sliders text-indigo-400"></i> CONTROL_CENTER
            </h1>
            <p class="text-xs text-gray-400 mt-1">即時發派任務與全體進度監控中心</p>
        </div>
        <div class="flex gap-3">
            <a href="/dashboard" class="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold p-2.5 px-4 rounded-xl transition-all">切換前台看板</a>
            <a href="/logout" class="bg-slate-800 hover:bg-slate-700 text-gray-300 text-xs p-2.5 px-4 rounded-xl">登出</a>
        </div>
    </div>

    <div class="max-w-7xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <div class="glass p-4 rounded-2xl">
            <p class="text-[10px] font-bold text-gray-400 uppercase font-mono">總控任務量</p>
            <p class="text-2xl font-black text-white mt-1 font-mono">{{ stats.total or 0 }}</p>
        </div>
        <div class="glass p-4 rounded-2xl border-l-2 border-l-emerald-500/50">
            <p class="text-[10px] font-bold text-emerald-400 uppercase font-mono">已完結關閉</p>
            <p class="text-2xl font-black text-emerald-400 mt-1 font-mono">{{ stats.done or 0 }}</p>
        </div>
    </div>

    <div class="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        <div class="glass p-6 rounded-2xl shadow-xl h-fit">
            <h2 class="text-sm font-bold text-white mb-4 flex items-center gap-2 font-mono">
                <i class="fa-solid fa-circle-plus text-emerald-400"></i> CREATE_NEW_TASK
            </h2>
            <form action="/admin/task/create" method="POST" class="space-y-4 text-xs">
                <div>
                    <label class="block font-bold text-gray-400 mb-1">任務主旨 *</label>
                    <input type="text" name="title" required class="w-full bg-slate-900 border border-slate-700/60 rounded-xl p-2.5 text-white focus:outline-none focus:border-indigo-500">
                </div>
                <div>
                    <label class="block font-bold text-gray-400 mb-1">細節敘述</label>
                    <textarea name="description" rows="3" class="w-full bg-slate-900 border border-slate-700/60 rounded-xl p-2.5 text-white focus:outline-none focus:border-indigo-500"></textarea>
                </div>
                <div class="grid grid-cols-2 gap-4">
                    <div>
                        <label class="block font-bold text-gray-400 mb-1">優先程度</label>
                        <select name="priority" class="w-full bg-slate-900 border border-slate-700/60 rounded-xl p-2.5 text-white">
                            <option value="low">Low</option>
                            <option value="medium" selected>Medium</option>
                            <option value="high">High</option>
                        </select>
                    </div>
                    <div>
                        <label class="block font-bold text-gray-400 mb-1">指派擔當者</label>
                        <select name="assigned_to" class="w-full bg-slate-900 border border-slate-700/60 rounded-xl p-2.5 text-white">
                            <option value="">-- 待領取 --</option>
                            {% for emp in employees %}
                                <option value="{{ emp.id }}">@{{ emp.username }}</option>
                            {% endfor %}
                        </select>
                    </div>
                </div>
                <div>
                    <label class="block font-bold text-gray-400 mb-1">截止死線</label>
                    <input type="date" name="due_date" class="w-full bg-slate-900 border border-slate-700/60 rounded-xl p-2.5 text-white focus:outline-none">
                </div>
                <button type="submit" class="w-full bg-gradient-to-r from-indigo-500 to-indigo-600 hover:from-indigo-600 hover:to-indigo-700 text-white font-bold p-3 rounded-xl transition-all shadow-md">
                    確認分派任務
                </button>
            </form>
        </div>

        <div class="lg:col-span-2 glass p-6 rounded-2xl shadow-xl overflow-x-auto">
            <h2 class="text-sm font-bold text-white mb-4 flex items-center gap-2 font-mono">
                <i class="fa-solid fa-list-check text-indigo-400"></i> REALTIME_MONITOR
            </h2>
            <table class="w-full text-left text-xs text-gray-300">
                <thead class="bg-slate-900/60 text-gray-400 font-mono uppercase">
                    <tr>
                        <th class="p-3 rounded-l-xl">核心任務</th>
                        <th class="p-3">擔當</th>
                        <th class="p-3">當前狀態</th>
                        <th class="p-3">優先級</th>
                        <th class="p-3 rounded-r-xl text-center">管理</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-white/5">
                    {% for task in tasks %}
                    <tr class="hover:bg-white/[0.02] transition-all">
                        <td class="p-3">
                            <div class="font-bold text-white text-sm">{{ task.title }}</div>
                            <div class="text-[11px] text-gray-500 mt-0.5 max-w-[220px] truncate">{{ task.description or '...' }}</div>
                        </td>
                        <td class="p-3 font-mono text-indigo-300">
                            @{{ task.assignee or '未指派' }}
                        </td>
                        <td class="p-3">
                            {% if task.status == 'todo' %}
                                <span class="bg-red-500/10 text-red-400 p-1 px-2 rounded-md border border-red-500/10">待處理</span>
                            {% elif task.status == 'in_progress' %}
                                <span class="bg-amber-500/10 text-amber-400 p-1 px-2 rounded-md border border-amber-500/10">執行中</span>
                            {% else %}
                                <span class="bg-emerald-500/10 text-emerald-400 p-1 px-2 rounded-md border border-emerald-500/10">已結案</span>
                            {% endif %}
                        </td>
                        <td class="p-3 font-mono text-gray-400">
                            {{ task.priority | upper }}
                        </td>
                        <td class="p-3 text-center">
                            <form action="/admin/task/delete/{{ task.id }}" method="POST" onsubmit="return confirm('確定移除此任務？')" class="inline">
                                <button type="submit" class="text-gray-500 hover:text-red-400 transition-all">
                                    <i class="fa-regular fa-trash-can"></i>
                                </button>
                            </form>
                        </td>
                    </tr>
                    {% else %}
                    <tr>
                        <td colspan="5" class="p-8 text-center text-gray-600 font-mono">NO_TASKS_FOUND</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>

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

# 【前台】員工看板路由（🛠️ 修改：讓員工也能在大廳看到完全未被指派的公開任務）
@app.route('/dashboard')
def employee_dashboard():
    if 'user_id' not in session or session.get('role') != 'employee':
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cur = conn.cursor()
    # 撈出「屬於自己」或者「完全沒人領取的任務」
    cur.execute('''
        SELECT * FROM tasks 
        WHERE assigned_to = %s OR assigned_to IS NULL 
        ORDER BY due_date ASC, id DESC
    ''', (session['user_id'],))
    tasks = cur.fetchall()
    cur.close()
    conn.close()
    
    return render_template_string(EMPLOYEE_HTML, tasks=tasks)

# 【前台 API】變更任務進度狀態 (🛠️ 這裡修正了 400 權限隔離 Bug)
@app.route('/api/task/<int:task_id>/status', methods=['POST'])
def update_task_status(task_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json() or {}
    new_status = data.get('status')
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    if session.get('role') == 'admin':
        cur.execute("UPDATE tasks SET status = %s WHERE id = %s", (new_status, task_id))
    else:
        # 【核心修正點】：
        # 允許員工更新狀態的條件：原本就是自己的任務 (assigned_to = id) OR 這個任務目前是公開待領取 (assigned_to IS NULL)
        # 同時，在更新狀態時，順便將 assigned_to 覆寫為當前員工的 ID，完成「主動領取任務」
        cur.execute('''
            UPDATE tasks 
            SET status = %s, assigned_to = %s 
            WHERE id = %s AND (assigned_to = %s OR assigned_to IS NULL)
        ''', (new_status, session['user_id'], task_id, session['user_id']))
    
    conn.commit()
    updated = cur.rowcount
    cur.close()
    conn.close()
    
    # 只要有成功更新到欄位，就回傳 200 OK，否則才回傳 400
    return jsonify({'success': True}) if updated > 0 else jsonify({'error': 'Failed'}), 400

# 【後台】管理者控制台
@app.route('/admin')
def admin_dashboard():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # 撈取全部任務與擔當者名稱
    cur.execute('''
        SELECT t.*, u.username as assignee 
        FROM tasks t 
        LEFT JOIN users u ON t.assigned_to = u.id 
        ORDER BY t.id DESC
    ''')
    tasks = cur.fetchall()
    
    # 員工指派選單
    cur.execute("SELECT id, username FROM users WHERE role = 'employee' ORDER BY username")
    employees = cur.fetchall()
    
    # 統計數據
    cur.execute("SELECT COUNT(*) as total, SUM(CASE WHEN status='done' THEN 1 ELSE 0 END) as done FROM tasks")
    stats = cur.fetchone()
    
    cur.close()
    conn.close()
    
    return render_template_string(ADMIN_HTML, tasks=tasks, employees=employees, stats=stats)

# 【後台】發布任務
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
    return redirect(url_for('admin_dashboard'))

# 【後台】刪除任務
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
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    app.run(debug=True)