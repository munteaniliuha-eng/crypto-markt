App · PY
import os
import sqlite3
from datetime import datetime
from functools import wraps
 
import click
from flask import (
    Flask, render_template, request, redirect, url_for,
    session, jsonify, flash, g
)
from werkzeug.security import generate_password_hash, check_password_hash
 
# ============================================================
#  НАСТРОЙКИ
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, 'market.db')
 
# Адрес для пополнений. Лучше задавать через переменную окружения,
# чтобы не хранить реальный кошелёк в коде.
YOUR_USDT_WALLET = os.environ.get('USDT_WALLET', 'TXxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx')
 
COMMISSION = 7        # комиссия при выводе, %
MIN_PRICE = 70        # минимальная цена услуги, ₽
MIN_WITHDRAW = 1000   # минимальная сумма заявки на вывод, ₽
 
app = Flask(__name__)
# Секретный ключ берём из переменной окружения. Если её нет — генерируем
# случайный при старте (тогда сессии сбросятся при перезапуске сервера,
# но это лучше, чем общий ключ "secret_key_67_change_this" в коде).
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(32))
 
 
# ============================================================
#  БАЗА ДАННЫХ
# ============================================================
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys = ON')
    return db
 
 
@app.teardown_appcontext
def close_db(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()
 
 
def init_db():
    db = sqlite3.connect(DATABASE)
    db.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'buyer',
            balance REAL NOT NULL DEFAULT 0,
            wallet_usdt TEXT,
            full_name TEXT,
            created_at TEXT NOT NULL
        );
 
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            seller_id INTEGER NOT NULL REFERENCES users(id),
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            price REAL NOT NULL,
            image TEXT,
            created_at TEXT NOT NULL
        );
 
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service_id INTEGER REFERENCES services(id),
            buyer_id INTEGER NOT NULL REFERENCES users(id),
            seller_id INTEGER NOT NULL REFERENCES users(id),
            title TEXT NOT NULL,
            price REAL NOT NULL,
            created_at TEXT NOT NULL
        );
 
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            type TEXT NOT NULL,                 -- deposit | withdraw
            amount REAL NOT NULL,
            wallet TEXT,
            status TEXT NOT NULL DEFAULT 'pending',  -- pending | completed | rejected
            created_at TEXT NOT NULL,
            processed_at TEXT
        );
    ''')
    db.commit()
    db.close()
 
 
# ============================================================
#  ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ / ДЕКОРАТОРЫ
# ============================================================
def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if 'user_id' not in session:
            flash('Войдите в аккаунт, чтобы продолжить', 'error')
            return redirect(url_for('login', next=request.path))
        return view(*args, **kwargs)
    return wrapped
 
 
def role_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if 'user_id' not in session:
                flash('Войдите в аккаунт, чтобы продолжить', 'error')
                return redirect(url_for('login', next=request.path))
            if session.get('role') not in roles:
                flash('Недостаточно прав для этого действия', 'error')
                return redirect(url_for('index'))
            return view(*args, **kwargs)
        return wrapped
    return decorator
 
 
@app.context_processor
def inject_globals():
    ctx = {
        'YOUR_USDT_WALLET': YOUR_USDT_WALLET,
        'COMMISSION': COMMISSION,
        'MIN_WITHDRAW': MIN_WITHDRAW,
        'MIN_PRICE': MIN_PRICE,
        'current_user': None,
        'balance': 0,
    }
    if 'user_id' in session:
        user = get_db().execute(
            'SELECT * FROM users WHERE id = ?', (session['user_id'],)
        ).fetchone()
        if user:
            ctx['current_user'] = user
            ctx['balance'] = user['balance']
        else:
            session.clear()
    return ctx
 
 
# ============================================================
#  КАТАЛОГ
# ============================================================
@app.route('/')
def index():
    db = get_db()
    search = request.args.get('search', '').strip()
    sort = request.args.get('sort', 'date')
 
    query = (
        'SELECT services.*, users.username AS seller_name '
        'FROM services JOIN users ON users.id = services.seller_id'
    )
    params = []
    if search:
        query += ' WHERE services.title LIKE ?'
        params.append(f'%{search}%')
 
    order_clauses = {
        'price_asc': ' ORDER BY services.price ASC',
        'price_desc': ' ORDER BY services.price DESC',
    }
    query += order_clauses.get(sort, ' ORDER BY services.created_at DESC')
 
    services = db.execute(query, params).fetchall()
    return render_template('index.html', services=services, search=search, sort=sort)
 
 
@app.route('/service/<int:service_id>')
def service_detail(service_id):
    db = get_db()
    service = db.execute(
        'SELECT services.*, users.username AS seller_name '
        'FROM services JOIN users ON users.id = services.seller_id '
        'WHERE services.id = ?',
        (service_id,)
    ).fetchone()
    if service is None:
        flash('Услуга не найдена или была удалена', 'error')
        return redirect(url_for('index'))
    return render_template('service_detail.html', service=service)
 
 
@app.route('/service/<int:service_id>/buy', methods=['POST'])
@login_required
def buy(service_id):
    db = get_db()
    service = db.execute('SELECT * FROM services WHERE id = ?', (service_id,)).fetchone()
    if service is None:
        return jsonify(status='error', message='Услуга не найдена')
 
    if service['seller_id'] == session['user_id']:
        return jsonify(status='error', message='Нельзя купить собственную услугу')
 
    buyer = db.execute('SELECT balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    if buyer['balance'] < service['price']:
        return jsonify(status='error', message='Недостаточно средств на балансе')
 
    db.execute('UPDATE users SET balance = balance - ? WHERE id = ?', (service['price'], session['user_id']))
    db.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (service['price'], service['seller_id']))
    db.execute(
        'INSERT INTO orders (service_id, buyer_id, seller_id, title, price, created_at) VALUES (?,?,?,?,?,?)',
        (service['id'], session['user_id'], service['seller_id'], service['title'],
         service['price'], datetime.now().isoformat())
    )
    db.commit()
    return jsonify(status='ok', message='Покупка успешно совершена')
 
 
# ============================================================
#  КОШЕЛЁК (заявки на пополнение / вывод, требуют подтверждения)
# ============================================================
@app.route('/wallet/deposit', methods=['POST'])
@login_required
def deposit():
    data = request.get_json(silent=True) or {}
    try:
        amount = round(float(data.get('amount', 0)), 2)
    except (TypeError, ValueError):
        return jsonify(status='error', message='Некорректная сумма')
    if amount <= 0:
        return jsonify(status='error', message='Сумма должна быть больше нуля')
 
    db = get_db()
    db.execute(
        'INSERT INTO transactions (user_id, type, amount, status, created_at) VALUES (?,?,?,?,?)',
        (session['user_id'], 'deposit', amount, 'pending', datetime.now().isoformat())
    )
    db.commit()
    return jsonify(
        status='ok',
        message='Заявка отправлена. Баланс пополнится после проверки платежа администратором.'
    )
 
 
@app.route('/wallet/withdraw', methods=['POST'])
@login_required
def withdraw():
    data = request.get_json(silent=True) or {}
    wallet = (data.get('wallet') or '').strip()
    try:
        amount = round(float(data.get('amount', 0)), 2)
    except (TypeError, ValueError):
        return jsonify(status='error', message='Некорректная сумма')
 
    if not wallet:
        return jsonify(status='error', message='Укажите USDT-кошелёк для вывода')
    if amount < MIN_WITHDRAW:
        return jsonify(status='error', message=f'Минимальная сумма вывода — {MIN_WITHDRAW} ₽')
 
    db = get_db()
    user = db.execute('SELECT balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    if user['balance'] < amount:
        return jsonify(status='error', message='Недостаточно средств на балансе')
 
    # Сумма списывается сразу (резервируется), чтобы нельзя было
    # одновременно подать несколько заявок на одни и те же деньги.
    # Если администратор отклонит заявку — сумма вернётся на баланс.
    db.execute('UPDATE users SET balance = balance - ? WHERE id = ?', (amount, session['user_id']))
    db.execute(
        'INSERT INTO transactions (user_id, type, amount, wallet, status, created_at) VALUES (?,?,?,?,?,?)',
        (session['user_id'], 'withdraw', amount, wallet, 'pending', datetime.now().isoformat())
    )
    db.commit()
 
    net = round(amount * (1 - COMMISSION / 100), 2)
    return jsonify(
        status='ok',
        message=f'Заявка принята. К выплате после комиссии {COMMISSION}%: {net} ₽'
    )
 
 
# ============================================================
#  РЕГИСТРАЦИЯ / ВХОД
# ============================================================
@app.route('/register/buyer', methods=['GET', 'POST'])
def register_buyer():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
 
        if not username or not password:
            flash('Заполните логин и пароль', 'error')
            return render_template('register_buyer.html', form=request.form)
 
        db = get_db()
        try:
            db.execute(
                'INSERT INTO users (username, password, role, created_at) VALUES (?,?,?,?)',
                (username, generate_password_hash(password), 'buyer', datetime.now().isoformat())
            )
            db.commit()
        except sqlite3.IntegrityError:
            flash('Такой логин уже занят', 'error')
            return render_template('register_buyer.html', form=request.form)
 
        flash('Регистрация завершена, теперь войдите', 'success')
        return redirect(url_for('login'))
 
    return render_template('register_buyer.html', form={})
 
 
@app.route('/register/seller', methods=['GET', 'POST'])
def register_seller():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        fullname = request.form.get('fullname', '').strip()
        wallet = request.form.get('wallet', '').strip()
        title = request.form.get('title', '').strip()
        description = request.form.get('desc', '').strip()
        image = request.form.get('image', '').strip()
        price_raw = request.form.get('price', '')
 
        errors = []
        if not username or not password:
            errors.append('Заполните логин и пароль')
        if not wallet:
            errors.append('Укажите USDT-кошелёк (TRC-20) для выплат')
        if not title or not description:
            errors.append('Заполните название и описание услуги')
 
        price = None
        try:
            price = float(price_raw)
            if price < MIN_PRICE:
                errors.append(f'Минимальная цена услуги — {MIN_PRICE} ₽')
        except ValueError:
            errors.append('Цена должна быть числом')
 
        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('register_seller.html', form=request.form)
 
        db = get_db()
        try:
            cur = db.execute(
                'INSERT INTO users (username, password, role, wallet_usdt, full_name, created_at) '
                'VALUES (?,?,?,?,?,?)',
                (username, generate_password_hash(password), 'seller', wallet, fullname,
                 datetime.now().isoformat())
            )
            user_id = cur.lastrowid
            db.execute(
                'INSERT INTO services (seller_id, title, description, price, image, created_at) '
                'VALUES (?,?,?,?,?,?)',
                (user_id, title, description, price, image, datetime.now().isoformat())
            )
            db.commit()
        except sqlite3.IntegrityError:
            flash('Такой логин уже занят', 'error')
            return render_template('register_seller.html', form=request.form)
 
        flash('Регистрация завершена, теперь войдите', 'success')
        return redirect(url_for('login'))
 
    return render_template('register_seller.html', form={})
 
 
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
 
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
 
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            next_url = request.args.get('next') or url_for('index')
            return redirect(next_url)
 
        flash('Неверный логин или пароль', 'error')
 
    return render_template('login.html')
 
 
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))
 
 
# ============================================================
#  ЛИЧНЫЙ КАБИНЕТ
# ============================================================
@app.route('/dashboard')
@login_required
def dashboard():
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
 
    services = []
    sales = []
    if user['role'] == 'seller':
        services = db.execute(
            'SELECT * FROM services WHERE seller_id = ? ORDER BY created_at DESC',
            (session['user_id'],)
        ).fetchall()
        sales = db.execute(
            'SELECT * FROM orders WHERE seller_id = ? ORDER BY created_at DESC',
            (session['user_id'],)
        ).fetchall()
 
    purchases = db.execute(
        'SELECT * FROM orders WHERE buyer_id = ? ORDER BY created_at DESC',
        (session['user_id'],)
    ).fetchall()
 
    transactions = db.execute(
        'SELECT * FROM transactions WHERE user_id = ? ORDER BY created_at DESC',
        (session['user_id'],)
    ).fetchall()
 
    return render_template(
        'dashboard.html', user=user, services=services,
        purchases=purchases, sales=sales, transactions=transactions
    )
 
 
@app.route('/service/add', methods=['GET', 'POST'])
@role_required('seller', 'admin')
def add_service():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('desc', '').strip()
        image = request.form.get('image', '').strip()
        price_raw = request.form.get('price', '')
 
        errors = []
        if not title or not description:
            errors.append('Заполните название и описание')
 
        price = None
        try:
            price = float(price_raw)
            if price < MIN_PRICE:
                errors.append(f'Минимальная цена услуги — {MIN_PRICE} ₽')
        except ValueError:
            errors.append('Цена должна быть числом')
 
        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('add_service.html', form=request.form)
 
        db = get_db()
        db.execute(
            'INSERT INTO services (seller_id, title, description, price, image, created_at) '
            'VALUES (?,?,?,?,?,?)',
            (session['user_id'], title, description, price, image, datetime.now().isoformat())
        )
        db.commit()
        flash('Услуга опубликована', 'success')
        return redirect(url_for('dashboard'))
 
    return render_template('add_service.html', form={})
 
 
@app.route('/service/<int:service_id>/delete', methods=['POST'])
@role_required('seller', 'admin')
def delete_service(service_id):
    db = get_db()
    db.execute('DELETE FROM services WHERE id = ? AND seller_id = ?', (service_id, session['user_id']))
    db.commit()
    flash('Услуга удалена', 'success')
    return redirect(url_for('dashboard'))
 
 
# ============================================================
#  АДМИНКА: подтверждение заявок на пополнение / вывод
# ============================================================
@app.route('/admin')
@role_required('admin')
def admin():
    db = get_db()
    pending = db.execute(
        'SELECT transactions.*, users.username FROM transactions '
        'JOIN users ON users.id = transactions.user_id '
        "WHERE transactions.status = 'pending' "
        'ORDER BY transactions.created_at'
    ).fetchall()
    return render_template('admin.html', pending=pending)
 
 
@app.route('/admin/transaction/<int:tx_id>/<action>', methods=['POST'])
@role_required('admin')
def admin_transaction(tx_id, action):
    if action not in ('approve', 'reject'):
        flash('Неизвестное действие', 'error')
        return redirect(url_for('admin'))
 
    db = get_db()
    tx = db.execute('SELECT * FROM transactions WHERE id = ?', (tx_id,)).fetchone()
    if tx is None or tx['status'] != 'pending':
        flash('Заявка не найдена или уже обработана', 'error')
        return redirect(url_for('admin'))
 
    now = datetime.now().isoformat()
    if action == 'approve':
        if tx['type'] == 'deposit':
            db.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (tx['amount'], tx['user_id']))
        # для вывода деньги уже были списаны при создании заявки —
        # администратор переводит USDT вручную и подтверждает заявку
        db.execute('UPDATE transactions SET status = ?, processed_at = ? WHERE id = ?', ('completed', now, tx_id))
        flash('Заявка подтверждена', 'success')
    else:
        if tx['type'] == 'withdraw':
            db.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (tx['amount'], tx['user_id']))
        db.execute('UPDATE transactions SET status = ?, processed_at = ? WHERE id = ?', ('rejected', now, tx_id))
        flash('Заявка отклонена', 'success')
 
    db.commit()
    return redirect(url_for('admin'))
 
 
# ============================================================
#  CLI
# ============================================================
@app.cli.command('create-admin')
@click.argument('username')
@click.argument('password')
def create_admin(username, password):
    """Создать пользователя с ролью администратора: flask create-admin login pass"""
    db = sqlite3.connect(DATABASE)
    try:
        db.execute(
            'INSERT INTO users (username, password, role, created_at) VALUES (?,?,?,?)',
            (username, generate_password_hash(password), 'admin', datetime.now().isoformat())
        )
        db.commit()
        click.echo(f'Администратор "{username}" создан.')
    except sqlite3.IntegrityError:
        click.echo('Пользователь с таким именем уже существует.')
    finally:
        db.close()
 
 
# ============================================================
init_db()
 
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
