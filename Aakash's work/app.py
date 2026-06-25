"""
app.py
------
Mini E-Commerce Product Management System.

Flask + raw sqlite3 (no ORM) + Jinja2 + Bootstrap 5.

Run with:
    python app.py
"""

import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = "dev-secret-key-change-in-production"  # needed for flash messages

DB_NAME = "database.db"


# ---------------------------------------------------------------------------
# Database helper
# ---------------------------------------------------------------------------
def get_db_connection():
    """Returns a sqlite3 connection with Row factory enabled (dict-like rows)."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ---------------------------------------------------------------------------
# CUSTOMER SIDE
# ---------------------------------------------------------------------------
@app.route("/")
def home():
    """Public storefront — shows ONLY active products (status = 1)."""
    conn = get_db_connection()
    products = conn.execute(
        """
        SELECT p.product_id, p.product_name, p.price, p.status,
               c.category_name
        FROM products p
        JOIN categories c ON p.category_id = c.category_id
        WHERE p.status = 1
        ORDER BY p.product_id DESC
        """
    ).fetchall()
    conn.close()
    return render_template("home.html", products=products)


# ---------------------------------------------------------------------------
# ADMIN DASHBOARD
# ---------------------------------------------------------------------------
@app.route("/admin")
def admin():
    conn = get_db_connection()
    total_categories = conn.execute("SELECT COUNT(*) AS cnt FROM categories").fetchone()["cnt"]
    total_products = conn.execute("SELECT COUNT(*) AS cnt FROM products").fetchone()["cnt"]
    active_products = conn.execute(
        "SELECT COUNT(*) AS cnt FROM products WHERE status = 1"
    ).fetchone()["cnt"]
    inactive_products = total_products - active_products
    conn.close()
    return render_template(
        "admin.html",
        total_categories=total_categories,
        total_products=total_products,
        active_products=active_products,
        inactive_products=inactive_products,
    )


# ---------------------------------------------------------------------------
# CATEGORY MANAGEMENT
# ---------------------------------------------------------------------------
@app.route("/categories")
def category_list():
    conn = get_db_connection()
    categories = conn.execute(
        "SELECT category_id, category_name FROM categories ORDER BY category_id"
    ).fetchall()
    conn.close()
    return render_template("category_list.html", categories=categories)


@app.route("/category/add", methods=["GET", "POST"])
def add_category():
    if request.method == "POST":
        category_name = request.form.get("category_name", "").strip()

        if not category_name:
            flash("Category name cannot be empty.", "danger")
            return render_template("add_category.html")

        conn = get_db_connection()
        try:
            conn.execute(
                "INSERT INTO categories (category_name) VALUES (?)", (category_name,)
            )
            conn.commit()
            flash(f"Category '{category_name}' added successfully.", "success")
            conn.close()
            return redirect(url_for("category_list"))
        except sqlite3.IntegrityError:
            conn.close()
            flash("That category name already exists.", "danger")
            return render_template("add_category.html")

    return render_template("add_category.html")


@app.route("/category/edit/<int:category_id>", methods=["GET", "POST"])
def edit_category(category_id):
    conn = get_db_connection()
    category = conn.execute(
        "SELECT category_id, category_name FROM categories WHERE category_id = ?",
        (category_id,),
    ).fetchone()

    if category is None:
        conn.close()
        flash("Category not found.", "danger")
        return redirect(url_for("category_list"))

    if request.method == "POST":
        category_name = request.form.get("category_name", "").strip()

        if not category_name:
            flash("Category name cannot be empty.", "danger")
            conn.close()
            return render_template("edit_category.html", category=category)

        try:
            conn.execute(
                "UPDATE categories SET category_name = ? WHERE category_id = ?",
                (category_name, category_id),
            )
            conn.commit()
            flash(f"Category updated successfully.", "success")
            conn.close()
            return redirect(url_for("category_list"))
        except sqlite3.IntegrityError:
            conn.close()
            flash("That category name already exists.", "danger")
            return render_template("edit_category.html", category=category)

    conn.close()
    return render_template("edit_category.html", category=category)

@app.route("/products")
def product_list():
    conn = get_db_connection()
    products = conn.execute(
        """
        SELECT p.product_id, p.product_name, p.price, p.status,
               c.category_name
        FROM products p
        JOIN categories c ON p.category_id = c.category_id
        ORDER BY p.product_id
        """
    ).fetchall()
    conn.close()
    return render_template("product_list.html", products=products)


@app.route("/product/add", methods=["GET", "POST"])
def add_product():
    conn = get_db_connection()
    categories = conn.execute(
        "SELECT category_id, category_name FROM categories ORDER BY category_name"
    ).fetchall()

    if request.method == "POST":
        product_name = request.form.get("product_name", "").strip()
        category_id = request.form.get("category_id", "")
        price = request.form.get("price", "").strip()
        status = 1 if request.form.get("status") == "on" else 0

        errors = []
        if not product_name:
            errors.append("Product name cannot be empty.")
        if not category_id:
            errors.append("Please select a category.")
        try:
            price_val = float(price)
            if price_val < 0:
                errors.append("Price cannot be negative.")
        except ValueError:
            errors.append("Price must be a valid number.")
            price_val = None

        if errors:
            for e in errors:
                flash(e, "danger")
            conn.close()
            return render_template("add_product.html", categories=categories)

        conn.execute(
            """INSERT INTO products (product_name, category_id, price, status)
               VALUES (?, ?, ?, ?)""",
            (product_name, int(category_id), price_val, status),
        )
        conn.commit()
        conn.close()
        flash(f"Product '{product_name}' added successfully.", "success")
        return redirect(url_for("product_list"))

    conn.close()
    return render_template("add_product.html", categories=categories)


@app.route("/product/edit/<int:product_id>", methods=["GET", "POST"])
def edit_product(product_id):
    conn = get_db_connection()
    product = conn.execute(
        "SELECT * FROM products WHERE product_id = ?", (product_id,)
    ).fetchone()

    if product is None:
        conn.close()
        flash("Product not found.", "danger")
        return redirect(url_for("product_list"))

    categories = conn.execute(
        "SELECT category_id, category_name FROM categories ORDER BY category_name"
    ).fetchall()

    if request.method == "POST":
        product_name = request.form.get("product_name", "").strip()
        category_id = request.form.get("category_id", "")
        price = request.form.get("price", "").strip()
        status = 1 if request.form.get("status") == "on" else 0

        errors = []
        if not product_name:
            errors.append("Product name cannot be empty.")
        if not category_id:
            errors.append("Please select a category.")
        try:
            price_val = float(price)
            if price_val < 0:
                errors.append("Price cannot be negative.")
        except ValueError:
            errors.append("Price must be a valid number.")
            price_val = None

        if errors:
            for e in errors:
                flash(e, "danger")
            conn.close()
            return render_template(
                "edit_product.html", product=product, categories=categories
            )

        conn.execute(
            """UPDATE products
               SET product_name = ?, category_id = ?, price = ?, status = ?
               WHERE product_id = ?""",
            (product_name, int(category_id), price_val, status, product_id),
        )
        conn.commit()
        conn.close()
        flash("Product updated successfully.", "success")
        return redirect(url_for("product_list"))

    conn.close()
    return render_template("edit_product.html", product=product, categories=categories)

@app.route("/category-summary")
def category_summary():
    conn = get_db_connection()
    summary = conn.execute(
        """
        SELECT c.category_name AS category_name,
               COUNT(p.product_id) AS total_products
        FROM categories c
        LEFT JOIN products p ON p.category_id = c.category_id
        GROUP BY c.category_id, c.category_name
        ORDER BY total_products DESC
        """
    ).fetchall()
    conn.close()

    chart_labels = [row["category_name"] for row in summary]
    chart_data = [row["total_products"] for row in summary]

    return render_template(
        "category_summary.html",
        summary=summary,
        chart_labels=chart_labels,
        chart_data=chart_data,
    )

if __name__ == "__main__":
    app.run(debug=True)
