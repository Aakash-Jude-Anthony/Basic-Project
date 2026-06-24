from flask import Flask, render_template, request, redirect, url_for, flash
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
    conn.commit()
    cursor.close()
    conn.close()


# ═══════════════════════════════════════════════════════
#  CATEGORY ROUTES
# ═══════════════════════════════════════════════════════

@app.route('/')
def index():
    return redirect(url_for('categories'))


@app.route('/categories')
def categories():
    conn = get_db()
    rows = []
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM categories ORDER BY created_at DESC")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
    return render_template('categories.html', categories=rows)


@app.route('/categories/add', methods=['GET', 'POST'])
def add_category():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
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
def edit_category(cat_id):
    conn = get_db()
    if not conn:
        flash('Database connection failed.', 'error')
        return redirect(url_for('categories'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        status = request.form.get('status', 'Active')
        if not name:
            flash('Category name is required.', 'error')
        else:
            try:
                cursor = conn.cursor()
                cursor.execute("UPDATE categories SET name=%s, status=%s WHERE id=%s", (name, status, cat_id))
                conn.commit()
                cursor.close()
                conn.close()
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
def products():
    conn = get_db()
    rows = []
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT p.*, c.name AS category_name
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
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
def add_product():
    categories = _get_active_categories()
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        category_id = request.form.get('category_id') or None
        price = request.form.get('price', '0').strip()
        status = request.form.get('status', 'Active')
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
def edit_product(prod_id):
    categories = _get_active_categories()
    conn = get_db()
    if not conn:
        flash('Database connection failed.', 'error')
        return redirect(url_for('products'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        category_id = request.form.get('category_id') or None
        price = request.form.get('price', '0').strip()
        status = request.form.get('status', 'Active')
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
