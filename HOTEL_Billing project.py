#!/usr/bin/env python3
"""
Billing + Inventory CLI using MySQL (mysql-connector-python)

Features:
- Add / View / Search customers
- Add / View products and stock
- Update stock
- Generate invoice (updates stock, stores bill & items)
- View bills
"""

import mysql.connector
from mysql.connector import errorcode
from decimal import Decimal
from getpass import getpass
from datetime import datetime

# ---------- CONFIG ----------
DB_CONFIG = {
    "user": "root",
    "password": "23102002",
    "host": "localhost",
    "database": "billing_db",
    "raise_on_warnings": True
}

GST_RATE = Decimal("0.18")    # 18%
DEFAULT_DISCOUNT_RATE = Decimal("0.10")  # 10% discount (can be changed)
# ----------------------------

def connect_db():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Authentication error: check username/password")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print("Database does not exist.")
        else:
            print(err)
        raise SystemExit(1)

# ---------- UTIL ----------
def to_decimal(x):
    return Decimal(str(x))

# ---------- CUSTOMER ----------
def add_customer(conn):
    name = input("Customer Name: ").strip()
    phone = input("Phone (optional): ").strip() or None
    email = input("Email (optional): ").strip() or None
    cur = conn.cursor()
    cur.execute("INSERT INTO customers (name, phone, email) VALUES (%s, %s, %s)",
                (name, phone, email))
    conn.commit()
    print("Customer added (id {}).".format(cur.lastrowid))
    cur.close()

def list_customers(conn):
    cur = conn.cursor()
    cur.execute("SELECT id, name, phone, email, created_at FROM customers ORDER BY id")
    rows = cur.fetchall()
    if not rows:
        print("No customers.")
    for r in rows:
        print(r)
    cur.close()

def find_customer_by_phone(conn, phone):
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM customers WHERE phone = %s", (phone,))
    r = cur.fetchone()
    cur.close()
    return r

# ---------- PRODUCTS / INVENTORY ----------
def add_product(conn):
    name = input("Product name: ").strip()
    price = input("Price (e.g. 149.50): ").strip()
    sku = input("SKU (optional): ").strip() or None
    try:
        price_d = to_decimal(price)
    except:
        print("Invalid price.")
        return
    cur = conn.cursor()
    cur.execute("INSERT INTO products (name, price, sku) VALUES (%s, %s, %s)", (name, price_d, sku))
    prod_id = cur.lastrowid
    # initialize inventory
    cur.execute("INSERT INTO inventory (product_id, stock) VALUES (%s, %s)", (prod_id, 0))
    conn.commit()
    print(f"Product added with id {prod_id}.")
    cur.close()

def list_products(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT p.id, p.name, p.price, i.stock, p.sku
        FROM products p LEFT JOIN inventory i ON p.id = i.product_id
        ORDER BY p.id
    """)
    rows = cur.fetchall()
    if not rows:
        print("No products.")
    for r in rows:
        print(r)
    cur.close()

def update_stock(conn):
    list_products(conn)
    prod_id = input("Enter product id to update stock: ").strip()
    qty = input("Enter stock quantity to set (integer): ").strip()
    try:
        pid = int(prod_id); q = int(qty)
    except:
        print("Invalid input.")
        return
    cur = conn.cursor()
    cur.execute("UPDATE inventory SET stock = %s WHERE product_id = %s", (q, pid))
    conn.commit()
    print("Stock updated.")
    cur.close()

def get_product_price_and_stock(conn, prod_id):
    cur = conn.cursor()
    cur.execute("SELECT price, (SELECT stock FROM inventory WHERE product_id = products.id) as stock FROM products WHERE id = %s", (prod_id,))
    r = cur.fetchone()
    cur.close()
    return r  # (price, stock) or None

# ---------- BILLING ----------
def generate_bill(conn):
    phone = input("Customer phone (or blank for walk-in): ").strip()
    customer_id = None
    if phone:
        cust = find_customer_by_phone(conn, phone)
        if not cust:
            print("Customer not found. Add customer first.")
            return
        customer_id = cust[0]

    # Build cart
    cart = []
    while True:
        list_products(conn)
        prod_input = input("Product id to add (blank to finish): ").strip()
        if prod_input == "":
            break
        qty_input = input("Quantity: ").strip()
        try:
            pid = int(prod_input); qty = int(qty_input)
        except:
            print("Invalid1" \
            "input.")
            continue

        res = get_product_price_and_stock(conn, pid)
        if not res:
            print("Product id not found.")
            continue
        price, stock = res
        if stock is None:
            stock = 0
        if qty > stock:
            print(f"Insufficient stock. Available: {stock}")
            continue
        line_total = to_decimal(price) * qty
        cart.append({"product_id": pid, "quantity": qty, "price_each": to_decimal(price), "line_total": line_total})

    if not cart:
        print("No items in cart. Aborting.")
        return

    total = sum(item["line_total"] for item in cart)
    gst_amount = (total * GST_RATE).quantize(Decimal("0.01"))
    discount_amount = (total * DEFAULT_DISCOUNT_RATE).quantize(Decimal("0.01"))
    final = (total + gst_amount - discount_amount).quantize(Decimal("0.01"))

    cur = conn.cursor()
    cur.execute("""
        INSERT INTO bills (customer_id, bill_date, total_amount, gst_amount, discount_amount, final_amount)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (customer_id, datetime.now(), str(total), str(gst_amount), str(discount_amount), str(final)))
    bill_id = cur.lastrowid

    # insert bill items and decrement stock
    for item in cart:
        cur.execute("""
            INSERT INTO bill_items (bill_id, product_id, quantity, price_each, line_total)
            VALUES (%s, %s, %s, %s, %s)
        """, (bill_id, item["product_id"], item["quantity"], str(item["price_each"]), str(item["line_total"])))
        # update stock
        cur.execute("UPDATE inventory SET stock = stock - %s WHERE product_id = %s", (item["quantity"], item["product_id"]))

    conn.commit()
    print("\n=== INVOICE ===")
    print(f"Bill ID: {bill_id}")
    print(f"Total: {total:.2f}")
    print(f"GST (18%): {gst_amount:.2f}")
    print(f"Discount (10%): {discount_amount:.2f}")
    print(f"Final Amount: {final:.2f}")
    cur.close()

def view_bills(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT b.bill_id, c.name, b.bill_date, b.final_amount
        FROM bills b LEFT JOIN customers c ON b.customer_id = c.id
        ORDER BY b.bill_id DESC LIMIT 50
    """)
    for row in cur.fetchall():
        print(row)
    cur.close()

def view_bill_details(conn):
    bid = input("Enter bill id: ").strip()
    try:
        bid = int(bid)
    except:
        print("Invalid id")
        return
    cur = conn.cursor()
    cur.execute("SELECT bill_id, customer_id, bill_date, total_amount, gst_amount, discount_amount, final_amount FROM bills WHERE bill_id = %s", (bid,))
    bill = cur.fetchone()
    if not bill:
        print("Bill not found.")
        cur.close()
        return
    print("Bill:", bill)
    cur.execute("""
        SELECT bi.id, p.name, bi.quantity, bi.price_each, bi.line_total
        FROM bill_items bi JOIN products p ON bi.product_id = p.id
        WHERE bi.bill_id = %s
    """, (bid,))
    items = cur.fetchall()
    print("Items:")
    for it in items:
        print(it)
    cur.close()

# ---------- MENU ----------
def main_menu():
    conn = connect_db()
    while True:
        print("""
===== Billing & Inventory =====
1. Add customer
2. List customers
3. Add product
4. List products
5. Update stock
6. Generate bill
7. View recent bills
8. View bill details
9. Exit
""")
        choice = input("Choose: ").strip()
        if choice == "1":
            add_customer(conn)
        elif choice == "2":
            list_customers(conn)
        elif choice == "3":
            add_product(conn)
        elif choice == "4":
            list_products(conn)
        elif choice == "5":
            update_stock(conn)
        elif choice == "6":
            generate_bill(conn)
        elif choice == "7":
            view_bills(conn)
        elif choice == "8":
            view_bill_details(conn)
        elif choice == "9":
            conn.close()
            print("Exiting.")
            break
        else:
            print("Invalid choice.")

if __name__ == "__main__":
    main_menu()
