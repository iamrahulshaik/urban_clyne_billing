from flask import Flask, render_template, request, redirect, url_for, send_file
import pymysql
from pymysql.cursors import DictCursor
from datetime import datetime
from fpdf import FPDF
import os
import urllib.parse
import webbrowser

app = Flask(__name__)

# ✅ Configure PyMySQL to act like MySQLdb
pymysql.install_as_MySQLdb()
import MySQLdb

# ✅ Database connection function
def get_connection():
    return MySQLdb.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "test"),
        port=int(os.getenv("DB_PORT", 3306)),
        cursorclass=DictCursor
    )


# ✅ Home page -> billing form
@app.route("/")
def bill_page():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    conn.close()
    return render_template("bill.html", products=products)


# ✅ Handle bill submission
@app.route('/generate-bill', methods=['POST'])
def generate_bill():
    customer_name = request.form['customer_name']
    mobile_number = request.form['mobile_number']
    product_ids = request.form.getlist('product_id')
    sizes = request.form.getlist('size')
    quantities = request.form.getlist('quantity')

    bill_items = []
    grand_total = 0

    conn = get_connection()
    cursor = conn.cursor()

    for i in range(len(product_ids)):
        if not product_ids[i] or not quantities[i]:
            continue
        try:
            pid = int(product_ids[i])
            qty = int(quantities[i])
        except ValueError:
            continue
        if qty <= 0:
            continue

        size = sizes[i]
        cursor.execute("SELECT name, selling_price FROM products WHERE id=%s", (pid,))
        product = cursor.fetchone()
        if not product:
            continue

        total = float(product["selling_price"]) * qty
        grand_total += total

        cursor.execute("""
            INSERT INTO bills (customer_name, mobile_number, product_id, size, quantity, total, bill_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (customer_name, mobile_number, pid, size, qty, total, datetime.now()))
        conn.commit()

        bill_items.append({
            "name": product["name"],
            "size": size,
            "qty": qty,
            "price": product["selling_price"],
            "total": total
        })

    conn.close()

    bill_date = datetime.now().strftime("%d-%m-%Y %H:%M")

    app.config["LAST_BILL"] = {
        "customer_name": customer_name,
        "mobile_number": mobile_number,
        "items": bill_items,
        "grand_total": grand_total,
        "bill_date": bill_date,
    }

    return render_template(
        'bill_summary.html',
        customer_name=customer_name,
        mobile_number=mobile_number,
        items=bill_items,
        grand_total=grand_total,
        bill_date=bill_date
    )


# ✅ Download bill as PDF
@app.route("/download-pdf")
def download_pdf():
    bill = app.config.get("LAST_BILL")
    if not bill:
        return "No bill found!", 400

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)

    # Header
    pdf.cell(200, 10, "URBAN CLYNE", ln=True, align="C")
    pdf.set_font("Arial", "", 12)
    pdf.cell(200, 10, f"Bill Date: {bill['bill_date']}", ln=True, align="C")
    pdf.ln(10)

    # Customer details
    pdf.cell(200, 10, f"Customer: {bill['customer_name']}", ln=True)
    pdf.cell(200, 10, f"Mobile: {bill['mobile_number']}", ln=True)
    pdf.ln(10)

    # Table header
    pdf.set_font("Arial", "B", 12)
    pdf.cell(60, 10, "Item", 1)
    pdf.cell(30, 10, "Size", 1)
    pdf.cell(30, 10, "Qty", 1)
    pdf.cell(30, 10, "Price", 1)
    pdf.cell(40, 10, "Total", 1, ln=True)

    # Table rows
    pdf.set_font("Arial", "", 12)
    for item in bill["items"]:
        pdf.cell(60, 10, item["name"], 1)
        pdf.cell(30, 10, item["size"], 1)
        pdf.cell(30, 10, str(item["qty"]), 1)
        pdf.cell(30, 10, str(item["price"]), 1)
        pdf.cell(40, 10, str(item["total"]), 1, ln=True)

    # Grand total
    pdf.set_font("Arial", "B", 12)
    pdf.cell(150, 10, "Grand Total", 1)
    pdf.cell(40, 10, str(bill["grand_total"]), 1, ln=True)

    pdf.ln(20)
    pdf.set_font("Arial", "I", 10)
    pdf.multi_cell(0, 10, "Thank you for visiting us!\nVisit again and follow our Insta page @urban_clyne")

    file_path = "bill.pdf"
    pdf.output(file_path)

    return send_file(file_path, as_attachment=True)


# ✅ Share bill via WhatsApp
@app.route("/share-whatsapp/<mobile>")
def share_whatsapp(mobile):
    bill = app.config.get("LAST_BILL")
    if not bill:
        return "No bill found!", 400

    message = f"Hello {bill['customer_name']}, thank you for shopping with URBAN CLYNE!\nYour total bill is ₹{bill['grand_total']}. Visit again!\nFollow us on Instagram: urban_clyne"
    encoded_msg = urllib.parse.quote(message)

    whatsapp_url = f"https://wa.me/{mobile}?text={encoded_msg}"
    return redirect(whatsapp_url)


# ✅ Add new product
@app.route('/add_product', methods=['POST'])
def add_product():
    name = request.form['name']
    buying_price = request.form['buying_price']
    selling_price = request.form['selling_price']
    sizes = request.form.get('sizes', 'S,M,L,XL')

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO products (name, buying_price, selling_price, sizes) VALUES (%s, %s, %s, %s)",
        (name, buying_price, selling_price, sizes)
    )
    conn.commit()
    conn.close()
    return redirect('/')


# ✅ Sales Analytics
@app.route("/analytics")
def analytics():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            SUM(b.total) AS total_sales,
            SUM((p.selling_price - p.buying_price) * b.quantity) AS total_profit
        FROM bills b
        JOIN products p ON b.product_id = p.id
    """)
    totals = cursor.fetchone()
    total_sales = totals["total_sales"] or 0
    total_profit = totals["total_profit"] or 0

    cursor.execute("""
        SELECT 
            p.name,
            SUM(b.quantity) AS qty_sold,
            SUM(b.total) AS total_amount,
            SUM((p.selling_price - p.buying_price) * b.quantity) AS profit
        FROM bills b
        JOIN products p ON b.product_id = p.id
        GROUP BY b.product_id, p.name
        ORDER BY qty_sold DESC
        LIMIT 5
    """)
    top_products = cursor.fetchall()

    cursor.execute("""
        SELECT 
            DATE(b.bill_date) AS date,
            SUM(b.total) AS daily_total,
            SUM((p.selling_price - p.buying_price) * b.quantity) AS daily_profit
        FROM bills b
        JOIN products p ON b.product_id = p.id
        WHERE b.bill_date >= NOW() - INTERVAL 7 DAY
        GROUP BY DATE(b.bill_date)
        ORDER BY date DESC
        LIMIT 7
    """)
    sales_by_date = cursor.fetchall()

    conn.close()

    return render_template(
        "analytics.html",
        total_sales=total_sales,
        total_profit=total_profit,
        top_products=top_products,
        sales_by_date=sales_by_date
    )


# ✅ Update product
@app.route('/update_product', methods=['POST'])
def update_product():
    product_id = request.form['product_id']
    new_name = request.form.get('new_name', '').strip()
    new_buying_price = request.form.get('new_buying_price', '').strip()
    new_selling_price = request.form.get('new_selling_price', '').strip()

    update_fields = []
    values = []

    if new_name:
        update_fields.append("name = %s")
        values.append(new_name)
    if new_buying_price:
        update_fields.append("buying_price = %s")
        values.append(new_buying_price)
    if new_selling_price:
        update_fields.append("selling_price = %s")
        values.append(new_selling_price)

    if not update_fields:
        return redirect('/')

    values.append(product_id)

    query = f"UPDATE products SET {', '.join(update_fields)} WHERE id = %s"

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query, tuple(values))
    conn.commit()
    conn.close()

    return redirect('/')


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
