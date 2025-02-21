from flask import Flask, request, jsonify
import os
import barcode
from barcode.writer import ImageWriter
import psycopg2

app = Flask(__name__)

BARCODE_DIR = "static/barcodes"
os.makedirs(BARCODE_DIR, exist_ok=True)

# 🔹 Supabase PostgreSQL Connection
DB_CONFIG = {
    "dbname": "postgres",
    "user": "postgres.kpwsabrvzergvzpgilhy",
    "password": "wMzRwtVTHNGMa4VS",
    "host": "aws-0-ap-southeast-1.pooler.supabase.com",
    "port": "6543"
}

def get_db_connection():
    """Establish a new database connection."""
    return psycopg2.connect(**DB_CONFIG)

def generate_gtin_13(product_id: int):
    """Generates a GTIN-13 compliant barcode number with a check digit."""
    base_gtin = f"123456{product_id:06d}"  # 6-digit prefix + 6-digit product ID
    checksum = sum((3 if i % 2 else 1) * int(d) for i, d in enumerate(base_gtin)) % 10
    check_digit = (10 - checksum) % 10
    return base_gtin + str(check_digit)

@app.route("/generate_barcode/", methods=["POST"])
def generate_barcode():
    try:
        product_name = request.form["product_name"]
        price = float(request.form["price"])
        
        conn = get_db_connection()
        cursor = conn.cursor()

        # 🔹 Get latest product ID from PostgreSQL
        cursor.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM Products")
        product_id = cursor.fetchone()[0]

        # 🔹 Generate a valid GTIN-13 barcode number
        gtin = generate_gtin_13(product_id)

        # 🔹 Generate barcode image
        barcode_obj = barcode.get("ean13", gtin, writer=ImageWriter())
        image_path = os.path.join(BARCODE_DIR, f"{gtin}.png")
        barcode_obj.save(image_path)

        # 🔹 Store in Supabase PostgreSQL
        cursor.execute(
            "INSERT INTO Products (id, name, price, gtin, barcode_image_path) VALUES (%s, %s, %s, %s, %s)",
            (product_id, product_name, price, gtin, image_path)
        )
        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({"gtin": gtin, "image_path": image_path})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/fetch-product/<string:gtin>", methods=["GET"])
def fetch_product(gtin):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT name, price, barcode_image_path FROM Products WHERE gtin = %s", (gtin,))
        product = cursor.fetchone()

        cursor.close()
        conn.close()

        if not product:
            return jsonify({"error": "Product not found"}), 404
        
        return jsonify({"product_name": product[0], "price": product[1], "barcode_image": product[2]})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=8080)
