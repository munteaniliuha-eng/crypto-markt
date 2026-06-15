from flask import Flask, render_template_string, request, redirect, url_for, session, jsonify
import sqlite3
import hashlib
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'secret_key_67_change_this'

# ===== НАСТРОЙКИ =====
# ВАШ USDT КОШЕЛЁК ДЛЯ ПОПОЛНЕНИЙ
YOUR_USDT_WALLET = "TXxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
# ВАША КОМИССИЯ ПРИ ВЫВОДЕ (%)
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
                  created_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS services
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  seller_id INTEGER,
                  title TEXT,
                  description TEXT,
                  price REAL,
                  image TEXT,
                  created_at TEXT)''')
    conn.commit()
    conn.close()

init_db()

# ===== HTML ШАБЛОН (ВСЁ В ОДНОМ ФАЙЛЕ) =====
HTML = '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Market67</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: Arial, sans-serif; background: #0a0a0a; color: #eee; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 15px; padding-bottom: 20px; border-bottom: 1px solid #333; margin-bottom: 30px; }
        .logo { font-size: 28px; font-weight: bold; color: #ff6600; }
        .nav a, .nav span { margin-left: 20px; color: #ff6600; text-decoration: none; }
        .btn, button { background: #ff6600; color: #000; padding: 10px 20px; border-radius: 25px; border: none; cursor: pointer; font-weight: bold; }
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 20px; margin-top: 20px; }
        .card { background: #1a1a1a; border-radius: 15px; padding: 15px; border: 1px solid #333; }
        .card img { width: 100%; height: 160px; object-fit: cover; border-radius: 10px; }
        .price { color: #ff6600; font-size: 24px; font-weight: bold; margin: 10px 0; }
        input, textarea, select { width: 100%; padding: 10px; margin: 8px 0; border-radius: 10px; border: none; background: #2a2a2a; color: white; }
        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); justify-content: center; align-items: center; }
        .modal-content { background: #1e1e1e; padding: 25px; border-radius: 20px; width: 90%; max-width: 450px; }
        .message { padding: 10px; margin: 10px 0; border-radius: 10px; }
        .error { background: #ff4444; color: white; }
        .success { background: #44ff44; color: black; }
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <div class="logo">💰 MARKET67</div>
        <div class="nav">
            {% if session.user_id %}
                <span>👤 {{ session.username }}</span>
                <a href="#" onclick="showWallet()">💳 {{ "%.2f"|format(balance) }} ₽</a>
                <a href="/dashboard">📁 Кабинет</a>
                <a href="/logout">🚪 Выход</a>
            {% else %}
                <a href="/register_buyer">📝 Покупатель</a>
                <a href="/register_seller">🏪 Продавец</a>
                <a href="/login">🔑 Вход</a>
            {% endif %}
        </div>
    </div>
    {% block content %}
    <div style="margin-bottom: 20px;">
        <form method="GET" style="display: flex; gap: 10px;">
            <input type="text" name="search" placeholder="Поиск..." style="flex:1;">
            <select name="sort">
                <option value="date">По дате</option>
                <option value="price_asc">Дешевле</option>
                <option value="price_desc">Дороже</option>
            </select>
            <button type="submit">🔍</button>
        </form>
    </div>
    <div class="grid">
        {% for s in services %}
        <div class="card">
            <img src="{{ s[6] or 'https://via.placeholder.com/300x160' }}">
            <h3>{{ s[3] }}</h3>
            <p>{{ s[4][:80] }}</p>
            <div class="price">{{ s[5] }} ₽</div>
            <a href="/service/{{ s[0] }}"><button>Купить</button></a>
        </div>
        {% endfor %}
    </div>
    {% endblock %}
</div>
<div id="walletModal" class="modal">
    <div class="modal-content">
        <h3>💰 Кошелёк</h3>
        <p>Баланс: <span id="modalBalance">{{ "%.2f"|format(balance) }}</span> ₽</p>
        <button onclick="showDeposit()">🇺🇸 Пополнить USDT</button>
        <button onclick="showWithdraw()">💸 Вывести ({{ COMMISSION }}%)</button>
        <div id="walletForms"></div>
        <button onclick="closeModal()">Закрыть</button>
    </div>
</div>
<script>
function showWallet() { document.getElementById('walletModal').style.display = 'flex'; }
function closeModal() { document.getElementById('walletModal').style.display = 'none'; document.getElementById('walletForms').innerHTML = ''; }
function showDeposit() {
    document.getElementById('walletForms').innerHTML = '<h4>Отправьте USDT на кошелёк:</h4><b>{{ your_wallet }}</b><input type="number" id="depositAmount" placeholder="Сумма в рублях"><button onclick="deposit()">Я оплатил</button>';
}
function showWithdraw() {
    document.getElementById('walletForms').innerHTML = '<h4>Вывод (мин 1000₽)</h4><input id="withdrawWallet" placeholder="Ваш USDT кошелёк"><input id="withdrawAmount" placeholder="Сумма"><button onclick="withdraw()">Запросить</button>';
}
async function deposit() {
    let amount = document.getElementById('depositAmount').value;
    let res = await fetch('/deposit', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({amount:parseFloat(amount)})});
    let data = await res.json();
    alert(data.message);
    if(data.status === 'ok') location.reload();
}
async function withdraw() {
    let wallet = document.getElementById('withdrawWallet').value;
    let amount = document.getElementById('withdrawAmount').value;
    let res = await fetch('/withdraw', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({amount:parseFloat(amount), wallet:wallet})});
    let data = await res.json();
    alert(data.message);
    if(data.status === 'ok') location.reload();
}
</script>
</body>
</html>
'''

@app.route('/')
def index():
    if 'user_id' not in session:
        return render_template_string(HTML.replace('{% block content %}{% endblock %}', '<center><h2>Добро пожаловать!<br><a href="/register_buyer"><button>Регистрация</button></a></h2></center>'), balance=0, your_wallet=YOUR_USDT_WALLET, COMMISSION=COMMISSION)
    conn = sqlite3.connect('market.db')
    c = conn.cursor()
    search = request.args.get('search', '')
    sort = request.args.get('sort', 'date')
    q = "SELECT * FROM services"
    if search:
        q += f" WHERE title LIKE '%{search}%'"
    if sort == 'price_asc':
        q += " ORDER BY price ASC"
    elif sort == 'price_desc':
        q += " ORDER BY price DESC"
    else:
        q += " ORDER BY created_at DESC"
    services = c.execute(q).fetchall()
    balance = c.execute("SELECT balance FROM users WHERE id=?", (session['user_id'],)).fetchone()[0]
    conn.close()
    return render_template_string(HTML.replace('{% block content %}{% endblock %}', '''
    <div style="margin-bottom:20px"><form method="GET" style="display:flex;gap:10px"><input name="search" placeholder="Поиск..." style="flex:1"><select name="sort"><option value="date">По дате</option><option value="price_asc">Дешевле</option><option value="price_desc">Дороже</option></select><button>🔍</button></form></div>
    <div class="grid">{% for s in services %}<div class="card"><img src="{{ s[6] or 'https://via.placeholder.com/300x160' }}"><h3>{{ s[3] }}</h3><p>{{ s[4][:80] }}</p><div class="price">{{ s[5] }} ₽</div><a href="/service/{{ s[0] }}"><button>Купить</button></a></div>{% endfor %}</div>
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
    <div class="card" style="max-width:600px;margin:auto"><img src="{service[6] or ''}" style="width:100%"><h2>{service[3]}</h2><p>Продавец: {seller[0]}</p><p>{service[4]}</p><div class="price">{service[5]} ₽</div><button onclick="buy({service[0]}, {service[5]})">Подтвердить покупку</button><div id="result"></div></div>
    <script>async function buy(id,price){{let r=await fetch('/buy/'+id,{{method:'POST'}});let d=await r.json();alert(d.message);if(d.status=='ok')location.href='/';}}</script>
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
        return jsonify({'status':'error', 'message':'Недостаточно'})
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
    <form method="post" style="max-width:400px;margin:auto"><h2>Регистрация покупателя</h2><input name="username" placeholder="Логин"><input type="password" name="password" placeholder="Пароль"><button>Зарегистрироваться</button></form>
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
    <form method="post" style="max-width:500px;margin:auto"><h2>Регистрация продавца</h2>
    <input name="username" placeholder="Логин"><input type="password" name="password" placeholder="Пароль">
    <input name="fullname" placeholder="Ваше имя"><input name="wallet" placeholder="USDT кошелёк">
    <h3>Первая услуга</h3><input name="title" placeholder="Название"><textarea name="desc" placeholder="Описание"></textarea>
    <input name="price" type="number" placeholder="Цена (мин 70)" step="1"><input name="image" placeholder="Ссылка на фото"><button>Зарегистрироваться</button></form>
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
        return "Ошибка"
    return '<form method="post" style="max-width:300px;margin:auto"><input name="username" placeholder="Логин"><input type="password" name="password"><button>Войти</button></form>'

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')
    conn = sqlite3.connect('market.db')
    c = conn.cursor()
    user = c.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
    if user[3] == 'seller':
        services = c.execute("SELECT * FROM services WHERE seller_id=?", (session['user_id'],)).fetchall()
        html = '<h2>Кабинет продавца</h2><a href="/add_service"><button>+ Добавить услугу</button></a><div class="grid">'
        for s in services:
            html += f'<div class="card"><img src="{s[6]}"><h3>{s[3]}</h3><div class="price">{s[5]}₽</div><a href="/delete_service/{s[0]}"><button>Удалить</button></a></div>'
        html += '</div>'
    else:
        html = '<h2>Кабинет покупателя</h2><p>Ваши покупки появятся здесь</p>'
    balance = user[4]
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
    <form method="post" style="max-width:500px;margin:auto"><h2>Новая услуга</h2>
    <input name="title" placeholder="Название"><textarea name="desc" placeholder="Описание"></textarea>
    <input name="price" type="number" step="1" placeholder="Цена"><input name="image" placeholder="Ссылка на фото"><button>Добавить</button></form>
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
