from flask import Flask, render_template, request, redirect, url_for, send_file
import pymysql
from datetime import datetime
from fpdf import FPDF   # pip install fpdf
import os
import urllib.parse
import webbrowser

app = Flask(__name__)

# MySQL connection
db = pymysql.connect(
    host="localhost",
    user="root",
    password="mysql",
    database="bills",
    cursorclass=pymysql.cursors.DictCursor
)
cursor = db.cursor()


# Home page -> billing form
@app.route("/")
def bill_page():
    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    return render_template("bill.html", products=products)


# Handle bill submission
@app.route('/generate-bill', methods=['POST'])
def generate_bill():
    customer_name = request.form['customer_name']
    mobile_number = request.form['mobile_number']
    product_ids = request.form.getlist('product_id')
    sizes = request.form.getlist('size')
    quantities = request.form.getlist('quantity')

    bill_items = []
    grand_total = 0

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
        # ✅ Use selling_price (not buying price)
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
        db.commit()

        bill_items.append({
            "name": product["name"],
            "size": size,
            "qty": qty,
            "price": product["selling_price"],  # ✅ selling price only
            "total": total
        })

    bill_date = datetime.now().strftime("%d-%m-%Y %H:%M")

    # Save bill in session (so we can use it in PDF/WhatsApp)
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

    # Footer
    pdf.ln(20)
    pdf.set_font("Arial", "I", 10)
    pdf.multi_cell(0, 10, "Thank you for visiting us!\nVisit again and follow our Insta page @urban_clyne")

    # Save PDF
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
    webbrowser.open(whatsapp_url)  # Opens WhatsApp in browser

    return redirect(whatsapp_url)


# ✅ Add new product
@app.route('/add_product', methods=['POST'])
def add_product():
    name = request.form['name']
    buying_price = request.form['buying_price']
    selling_price = request.form['selling_price']
    sizes = request.form.get('sizes', 'S,M,L,XL')

    cursor.execute(
        "INSERT INTO products (name, buying_price, selling_price, sizes) VALUES (%s, %s, %s, %s)",
        (name, buying_price, selling_price, sizes)
    )
    db.commit()
    return redirect('/')


if __name__ == "__main__":
    app.run(debug=True)
