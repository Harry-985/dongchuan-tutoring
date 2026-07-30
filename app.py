"""本地家教中介平台 - MVP"""
import sqlite3
import os
from flask import Flask, render_template, request, redirect, jsonify, session
from functools import wraps

app = Flask(__name__)
app.secret_key = os.urandom(24).hex()
DB = os.path.join(os.path.dirname(__file__), 'tutors.db')

# ========== DB ==========
def init_db():
    with sqlite3.connect(DB) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS teachers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            avatar TEXT DEFAULT '',
            subjects TEXT NOT NULL,
            grades TEXT NOT NULL,
            price_per_hour INTEGER DEFAULT 100,
            experience TEXT DEFAULT '',
            location TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            wechat_id TEXT DEFAULT '',
            description TEXT DEFAULT '',
            rating REAL DEFAULT 5.0,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        conn.execute("PRAGMA journal_mode=WAL")

def query(sql, params=(), one=False):
    with sqlite3.connect(DB) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(sql, params)
        return cur.fetchone() if one else cur.fetchall()

def execute(sql, params=()):
    with sqlite3.connect(DB) as conn:
        conn.execute(sql, params)
        conn.commit()

# ========== Auth ==========
ADMIN_PASSWORD = 'admin888'

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin'):
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated

# ========== Public Routes ==========
@app.route('/')
def home():
    teachers = query("SELECT * FROM teachers WHERE is_active=1 ORDER BY rating DESC")
    return render_template('home.html', teachers=teachers)

@app.route('/teacher/<int:id>')
def teacher_detail(id):
    t = query("SELECT * FROM teachers WHERE id=? AND is_active=1", (id,), one=True)
    if not t:
        return "老师不存在", 404
    return render_template('detail.html', teacher=t)

# ========== Admin Routes ==========
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['admin'] = True
            return redirect('/admin')
        return render_template('login.html', error='密码错误')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect('/')

@app.route('/admin')
@login_required
def admin():
    teachers = query("SELECT * FROM teachers ORDER BY id DESC")
    return render_template('admin.html', teachers=teachers)

@app.route('/admin/add', methods=['GET', 'POST'])
@login_required
def add_teacher():
    if request.method == 'POST':
        execute('''INSERT INTO teachers (name, avatar, subjects, grades, price_per_hour,
                   experience, location, phone, wechat_id, description, rating, is_active)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''',
                (request.form.get('name'), request.form.get('avatar', ''),
                 request.form.get('subjects'), request.form.get('grades'),
                 int(request.form.get('price_per_hour', 100)), request.form.get('experience', ''),
                 request.form.get('location', ''), request.form.get('phone', ''),
                 request.form.get('wechat_id', ''), request.form.get('description', ''),
                 float(request.form.get('rating', 5.0)),
                 1 if request.form.get('is_active') else 0))
        return redirect('/admin')
    return render_template('add_teacher.html')

@app.route('/admin/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_teacher(id):
    if request.method == 'POST':
        execute('''UPDATE teachers SET name=?, avatar=?, subjects=?, grades=?, price_per_hour=?,
                   experience=?, location=?, phone=?, wechat_id=?, description=?, rating=?, is_active=?
                   WHERE id=?''',
                (request.form.get('name'), request.form.get('avatar', ''),
                 request.form.get('subjects'), request.form.get('grades'),
                 int(request.form.get('price_per_hour', 100)), request.form.get('experience', ''),
                 request.form.get('location', ''), request.form.get('phone', ''),
                 request.form.get('wechat_id', ''), request.form.get('description', ''),
                 float(request.form.get('rating', 5.0)),
                 1 if request.form.get('is_active') else 0,
                 id))
        return redirect('/admin')
    t = query("SELECT * FROM teachers WHERE id=?", (id,), one=True)
    if not t:
        return "老师不存在", 404
    return render_template('edit_teacher.html', teacher=t)

@app.route('/admin/delete/<int:id>')
@login_required
def delete_teacher(id):
    execute("DELETE FROM teachers WHERE id=?", (id,))
    return redirect('/admin')

# ========== API ==========
@app.route('/api/teachers')
def api_teachers():
    subject = request.args.get('subject', '')
    grade = request.args.get('grade', '')
    sort = request.args.get('sort', 'rating')
    sql = "SELECT * FROM teachers WHERE is_active=1"
    params = []
    if subject:
        sql += " AND subjects LIKE ?"
        params.append(f'%{subject}%')
    if grade:
        sql += " AND grades LIKE ?"
        params.append(f'%{grade}%')
    sql += f" ORDER BY {sort} DESC"
    rows = query(sql, params)
    return jsonify([dict(r) for r in rows])

# ========== Seed Data ==========
def seed():
    """预置几条示例数据"""
    existing = query("SELECT COUNT(*) as c FROM teachers", one=True)
    if existing['c'] > 0:
        return
    samples = [
        ('张老师', '数学', '初一,初二,初三', 120, '5年教学经验，曾在某知名培训机构任教',
         '市区', '138****1234', 'zhang_math', '擅长初中数学提分，针对中考有独家解题方法', 4.9),
        ('李老师', '英语', '小学五年级,小学六年级,初一,初二', 100, '英语专业八级，3年家教经验',
         '城北', '139****5678', 'li_english', '发音标准，寓教于乐，孩子喜欢', 4.7),
        ('王老师', '物理,化学', '初三,高一,高二', 150, '某重点中学退休教师，20年教龄',
         '城南', '136****9012', 'wang_physics', '高考物理化学双料辅导，押题命中率高', 5.0),
        ('赵老师', '语文', '小学全年级', 80, '师范大学中文系毕业，2年小学语文教学经验',
         '城东', '137****3456', 'zhao_chinese', '作文辅导有独到方法，孩子进步明显', 4.6),
        ('刘老师', '生物,化学', '初三,高一,高二,高三', 130, '药学硕士，可辅导竞赛',
         '大学城', '135****7890', 'liu_bio', '医药背景，擅长理科综合，可带生物竞赛', 4.8),
    ]
    for s in samples:
        execute('''INSERT INTO teachers (name, subjects, grades, price_per_hour, experience,
                   location, phone, wechat_id, description, rating, is_active)
                   VALUES (?,?,?,?,?,?,?,?,?,?,1)''', s)
    print("Seed data inserted.")

# ========== Main ==========
if __name__ == '__main__':
    init_db()
    seed()
    print(f"数据库: {DB}")
    app.run(host='0.0.0.0', port=5000, debug=True)
