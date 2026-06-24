from flask import Flask, render_template, request, redirect, url_for, flash, session
from functools import wraps
import mysql.connector
from mysql.connector import Error

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'

# ── DB CONFIG ── update with your credentials ─────────────────────────
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'root123',
    'database': 'catalog_db'
}
# ─────────────────────────────────────────────────────────────────────

def get_db():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        print(f"DB connection error: {e}")
        return None


def init_db():
    conn = get_db()
    if not conn:
        return
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL UNIQUE,
            status ENUM('Active', 'Inactive') DEFAULT 'Active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(150) NOT NULL,
            category_id INT,
            price DECIMAL(10,2) NOT NULL DEFAULT 0.00,
            status ENUM('Active', 'Inactive') DEFAULT 'Active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(80) NOT NULL UNIQUE,
            password VARCHAR(80) NOT NULL,
            role ENUM('admin', 'user') DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Create default admin if no users exist
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    if count == 0:
        cursor.execute(
            "INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
            ('admin', 'admin123', 'admin')
        )
    conn.commit()
    cursor.close()
    conn.close()


# ═══════════════════════════════════════════════════════
#  AUTH DECORATORS
# ═══════════════════════════════════════════════════════

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to continue.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to continue.', 'error')
            return redirect(url_for('login'))
        if session.get('role') != 'admin':
            flash('Access denied — admins only.', 'error')
            return redirect(url_for('categories'))
        return f(*args, **kwargs)
    return decorated


# ═══════════════════════════════════════════════════════
#  AUTH ROUTES
# ═══════════════════════════════════════════════════════

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('categories'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('categories'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        conn = get_db()
        if conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users WHERE username=%s AND password=%s", (username, password))
            user = cursor.fetchone()
            cursor.close()
            conn.close()
            if user:
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['role'] = user['role']
                flash(f"Welcome back, {user['username']}!", 'success')
                return redirect(url_for('categories'))
            else:
                flash('Invalid username or password.', 'error')
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('categories'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        confirm  = request.form.get('confirm', '').strip()
        if not username or not password:
            flash('Username and password are required.', 'error')
        elif password != confirm:
            flash('Passwords do not match.', 'error')
        else:
            conn = get_db()
            if conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO users (username, password, role) VALUES (%s, %s, 'user')",
                        (username, password)
                    )
                    conn.commit()
                    cursor.close()
                    conn.close()
                    flash('Account created! You can now log in.', 'success')
                    return redirect(url_for('login'))
                except Error as e:
                    if 'Duplicate' in str(e):
                        flash('Username already taken. Try another.', 'error')
                    else:
                        flash(f'Error: {e}', 'error')
    return render_template('register.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))


# ═══════════════════════════════════════════════════════
#  USER MANAGEMENT (Admin only)
# ═══════════════════════════════════════════════════════

@app.route('/users')
@admin_required
def users():
    conn = get_db()
    rows = []
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
    return render_template('users.html', users=rows)


@app.route('/users/add', methods=['GET', 'POST'])
@admin_required
def add_user():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        role     = request.form.get('role', 'user')
        if not username or not password:
            flash('Username and password are required.', 'error')
            return render_template('user_form.html', action='Add', user=None)
        conn = get_db()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
                    (username, password, role)
                )
                conn.commit()
                cursor.close()
                conn.close()
                flash('User added successfully.', 'success')
                return redirect(url_for('users'))
            except Error as e:
                flash(f'Error: {e}', 'error')
    return render_template('user_form.html', action='Add', user=None)


@app.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    conn = get_db()
    if not conn:
        flash('Database connection failed.', 'error')
        return redirect(url_for('users'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        role     = request.form.get('role', 'user')
        if not username or not password:
            flash('Username and password are required.', 'error')
        else:
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE users SET username=%s, password=%s, role=%s WHERE id=%s",
                    (username, password, role, user_id)
                )
                conn.commit()
                cursor.close()
                conn.close()
                flash('User updated.', 'success')
                return redirect(url_for('users'))
            except Error as e:
                flash(f'Error: {e}', 'error')

    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE id=%s", (user_id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('users'))
    return render_template('user_form.html', action='Edit', user=user)


@app.route('/users/delete/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    if user_id == session.get('user_id'):
        flash("You can't delete your own account.", 'error')
        return redirect(url_for('users'))
    conn = get_db()
    if conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE id=%s", (user_id,))
        conn.commit()
        cursor.close()
        conn.close()
        flash('User deleted.', 'success')
    return redirect(url_for('users'))


# ═══════════════════════════════════════════════════════
#  CATEGORY ROUTES
# ═══════════════════════════════════════════════════════

@app.route('/categories')
@login_required
def categories():
    conn = get_db()
    rows = []
    if conn:
        cursor = conn.cursor(dictionary=True)
        if session.get('role') == 'admin':
            cursor.execute("SELECT * FROM categories ORDER BY created_at DESC")
        else:
            cursor.execute("SELECT * FROM categories WHERE status='Active' ORDER BY created_at DESC")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
    return render_template('categories.html', categories=rows)


@app.route('/categories/add', methods=['GET', 'POST'])
@admin_required
def add_category():
    if request.method == 'POST':
        name   = request.form.get('name', '').strip()
        status = request.form.get('status', 'Active')
        if not name:
            flash('Category name is required.', 'error')
            return render_template('category_form.html', action='Add', category=None)
        conn = get_db()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO categories (name, status) VALUES (%s, %s)", (name, status))
                conn.commit()
                cursor.close()
                conn.close()
                flash('Category added successfully.', 'success')
                return redirect(url_for('categories'))
            except Error as e:
                flash(f'Error: {e}', 'error')
    return render_template('category_form.html', action='Add', category=None)


@app.route('/categories/edit/<int:cat_id>', methods=['GET', 'POST'])
@admin_required
def edit_category(cat_id):
    conn = get_db()
    if not conn:
        flash('Database connection failed.', 'error')
        return redirect(url_for('categories'))

    if request.method == 'POST':
        name   = request.form.get('name', '').strip()
        status = request.form.get('status', 'Active')
        if not name:
            flash('Category name is required.', 'error')
        else:
            try:
                cursor = conn.cursor()
                cursor.execute("UPDATE categories SET name=%s, status=%s WHERE id=%s", (name, status, cat_id))
                if status == 'Inactive':
                    cursor.execute("UPDATE products SET status='Inactive' WHERE category_id=%s", (cat_id,))
                conn.commit()
                cursor.close()
                conn.close()
                if status == 'Inactive':
                    flash('Category set to Inactive — all its products have been deactivated too.', 'success')
                else:
                    flash('Category updated.', 'success')
                return redirect(url_for('categories'))
            except Error as e:
                flash(f'Error: {e}', 'error')

    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM categories WHERE id=%s", (cat_id,))
    category = cursor.fetchone()
    cursor.close()
    conn.close()
    if not category:
        flash('Category not found.', 'error')
        return redirect(url_for('categories'))
    return render_template('category_form.html', action='Edit', category=category)


@app.route('/categories/delete/<int:cat_id>', methods=['POST'])
@admin_required
def delete_category(cat_id):
    conn = get_db()
    if conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM categories WHERE id=%s", (cat_id,))
        conn.commit()
        cursor.close()
        conn.close()
        flash('Category deleted.', 'success')
    return redirect(url_for('categories'))


# ═══════════════════════════════════════════════════════
#  PRODUCT ROUTES
# ═══════════════════════════════════════════════════════

@app.route('/products')
@login_required
def products():
    conn = get_db()
    rows = []
    if conn:
        cursor = conn.cursor(dictionary=True)
        if session.get('role') == 'admin':
            cursor.execute("""
                SELECT p.*, c.name AS category_name
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.id
                ORDER BY p.created_at DESC
            """)
        else:
            cursor.execute("""
                SELECT p.*, c.name AS category_name
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.id
                WHERE p.status='Active'
                AND (c.status='Active' OR p.category_id IS NULL)
                ORDER BY p.created_at DESC
            """)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
    return render_template('products.html', products=rows)


def _get_active_categories():
    conn = get_db()
    cats = []
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, name FROM categories WHERE status='Active' ORDER BY name")
        cats = cursor.fetchall()
        cursor.close()
        conn.close()
    return cats


@app.route('/products/add', methods=['GET', 'POST'])
@admin_required
def add_product():
    categories = _get_active_categories()
    if request.method == 'POST':
        name        = request.form.get('name', '').strip()
        category_id = request.form.get('category_id') or None
        price       = request.form.get('price', '0').strip()
        status      = request.form.get('status', 'Active')
        if not name:
            flash('Product name is required.', 'error')
            return render_template('product_form.html', action='Add', product=None, categories=categories)
        try:
            price = float(price)
        except ValueError:
            flash('Price must be a number.', 'error')
            return render_template('product_form.html', action='Add', product=None, categories=categories)
        conn = get_db()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO products (name, category_id, price, status) VALUES (%s, %s, %s, %s)",
                    (name, category_id, price, status)
                )
                conn.commit()
                cursor.close()
                conn.close()
                flash('Product added successfully.', 'success')
                return redirect(url_for('products'))
            except Error as e:
                flash(f'Error: {e}', 'error')
    return render_template('product_form.html', action='Add', product=None, categories=categories)


@app.route('/products/edit/<int:prod_id>', methods=['GET', 'POST'])
@admin_required
def edit_product(prod_id):
    categories = _get_active_categories()
    conn = get_db()
    if not conn:
        flash('Database connection failed.', 'error')
        return redirect(url_for('products'))

    if request.method == 'POST':
        name        = request.form.get('name', '').strip()
        category_id = request.form.get('category_id') or None
        price       = request.form.get('price', '0').strip()
        status      = request.form.get('status', 'Active')
        if not name:
            flash('Product name is required.', 'error')
        else:
            try:
                price = float(price)
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE products SET name=%s, category_id=%s, price=%s, status=%s WHERE id=%s",
                    (name, category_id, price, status, prod_id)
                )
                conn.commit()
                cursor.close()
                conn.close()
                flash('Product updated.', 'success')
                return redirect(url_for('products'))
            except (ValueError, Error) as e:
                flash(f'Error: {e}', 'error')

    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products WHERE id=%s", (prod_id,))
    product = cursor.fetchone()
    cursor.close()
    conn.close()
    if not product:
        flash('Product not found.', 'error')
        return redirect(url_for('products'))
    return render_template('product_form.html', action='Edit', product=product, categories=categories)


@app.route('/products/delete/<int:prod_id>', methods=['POST'])
@admin_required
def delete_product(prod_id):
    conn = get_db()
    if conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM products WHERE id=%s", (prod_id,))
        conn.commit()
        cursor.close()
        conn.close()
        flash('Product deleted.', 'success')
    return redirect(url_for('products'))


if __name__ == '__main__':
    init_db()
    app.run(debug=True)