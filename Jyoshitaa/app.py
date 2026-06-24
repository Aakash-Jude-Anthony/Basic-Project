from flask import Flask, render_template, request, redirect, url_for, flash, session
import mysql.connector
from mysql.connector import Error
from functools import wraps

app = Flask(__name__)
app.secret_key = 'ecommerce_secret_key'

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Gvj@9806',  # your password here
    'database': 'ecommerce_db'
}

def get_db():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        print(f"DB Error: {e}")
        return None

# ── AUTH DECORATORS ──
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first.', 'error')
            return redirect(url_for('login'))
        if session.get('role') != 'admin':
            flash('Admin access only.', 'error')
            return redirect(url_for('products'))
        return f(*args, **kwargs)
    return decorated

# ── AUTH ROUTES ──
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if session.get('role') == 'admin':
        return redirect(url_for('categories'))
    return redirect(url_for('products'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('index'))
    if request.method == 'POST':
        email    = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        conn = get_db()
        if conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM flask_users WHERE email=%s AND password=%s", (email, password))
            user = cursor.fetchone()
            conn.close()
            if user:
                session['user_id'] = user['id']
                session['name']    = user['name']
                session['role']    = user['role']
                flash(f"Welcome, {user['name']}!", 'success')
                return redirect(url_for('index'))
            else:
                flash('Invalid email or password.', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('login'))

# ── CATEGORIES (admin only) ──
@app.route('/categories')
@admin_required
def categories():
    conn = get_db()
    categories = []
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM categories ORDER BY created_at DESC")
        categories = cursor.fetchall()
        conn.close()
    return render_template('categories.html', categories=categories)

@app.route('/categories/add', methods=['POST'])
@admin_required
def add_category():
    name   = request.form.get('name', '').strip()
    status = request.form.get('status', 'active')
    if not name:
        flash('Category name is required.', 'error')
        return redirect(url_for('categories'))
    conn = get_db()
    if conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO categories (name, status) VALUES (%s, %s)", (name, status))
        conn.commit()
        conn.close()
        flash('Category added!', 'success')
    return redirect(url_for('categories'))

@app.route('/categories/delete/<int:id>')
@admin_required
def delete_category(id):
    conn = get_db()
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM products WHERE category_id = %s", (id,))
        count = cursor.fetchone()[0]
        if count > 0:
            flash(f'Cannot delete: {count} product(s) use this category.', 'error')
        else:
            cursor.execute("DELETE FROM categories WHERE id = %s", (id,))
            conn.commit()
            flash('Category deleted.', 'success')
        conn.close()
    return redirect(url_for('categories'))

@app.route('/categories/toggle/<int:id>')
@admin_required
def toggle_category(id):
    conn = get_db()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT status FROM categories WHERE id = %s", (id,))
        row = cursor.fetchone()
        if row:
            new_status = 'inactive' if row['status'] == 'active' else 'active'
            cursor.execute("UPDATE categories SET status=%s WHERE id=%s", (new_status, id))
            conn.commit()
        conn.close()
    return redirect(url_for('categories'))

# ── PRODUCTS ──
@app.route('/products')
@login_required
def products():
    conn = get_db()
    products   = []
    categories = []
    if conn:
        cursor = conn.cursor(dictionary=True)
        if session.get('role') == 'admin':
            cursor.execute("""
                SELECT p.*, c.name AS category_name
                FROM products p LEFT JOIN categories c ON p.category_id=c.id
                ORDER BY p.created_at DESC
            """)
        else:
            cursor.execute("""
                SELECT p.*, c.name AS category_name
                FROM products p LEFT JOIN categories c ON p.category_id=c.id
                WHERE p.status='active'
                ORDER BY p.created_at DESC
            """)
        products = cursor.fetchall()
        cursor.execute("SELECT * FROM categories WHERE status='active'")
        categories = cursor.fetchall()
        conn.close()
    return render_template('products.html', products=products, categories=categories)

@app.route('/products/add', methods=['POST'])
@admin_required
def add_product():
    name        = request.form.get('name', '').strip()
    category_id = request.form.get('category_id')
    price       = request.form.get('price', '').strip()
    description = request.form.get('description', '').strip()
    status      = request.form.get('status', 'active')
    if not name or not price:
        flash('Name and price are required.', 'error')
        return redirect(url_for('products'))
    try:
        price = float(price)
    except ValueError:
        flash('Price must be a number.', 'error')
        return redirect(url_for('products'))
    conn = get_db()
    if conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO products (name, category_id, price, description, status) VALUES (%s,%s,%s,%s,%s)",
            (name, category_id or None, price, description, status)
        )
        conn.commit()
        conn.close()
        flash('Product added!', 'success')
    return redirect(url_for('products'))

@app.route('/products/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_product(id):
    conn = get_db()
    if not conn:
        return redirect(url_for('products'))
    if request.method == 'POST':
        name        = request.form.get('name', '').strip()
        category_id = request.form.get('category_id')
        price       = request.form.get('price', '').strip()
        description = request.form.get('description', '').strip()
        status      = request.form.get('status', 'active')
        try:
            price = float(price)
        except ValueError:
            flash('Price must be a number.', 'error')
            return redirect(url_for('products'))
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE products SET name=%s, category_id=%s, price=%s, description=%s, status=%s
            WHERE id=%s
        """, (name, category_id or None, price, description, status, id))
        conn.commit()
        conn.close()
        flash('Product updated!', 'success')
        return redirect(url_for('products'))
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products WHERE id=%s", (id,))
    product = cursor.fetchone()
    cursor.execute("SELECT * FROM categories WHERE status='active'")
    categories = cursor.fetchall()
    conn.close()
    products_all = []
    conn2 = get_db()
    if conn2:
        c2 = conn2.cursor(dictionary=True)
        c2.execute("""
            SELECT p.*, c.name AS category_name
            FROM products p LEFT JOIN categories c ON p.category_id=c.id
            ORDER BY p.created_at DESC
        """)
        products_all = c2.fetchall()
        conn2.close()
    return render_template('products.html', products=products_all, categories=categories, edit_product=product)

@app.route('/products/delete/<int:id>')
@admin_required
def delete_product(id):
    conn = get_db()
    if conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM products WHERE id=%s", (id,))
        conn.commit()
        conn.close()
        flash('Product deleted.', 'success')
    return redirect(url_for('products'))

if __name__ == '__main__':
    app.run(debug=True)