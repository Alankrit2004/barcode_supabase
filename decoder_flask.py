from flask import Flask, request, jsonify
import os
import barcode
from barcode.writer import ImageWriter
import pyodbc

app = Flask(__name__)

BARCODE_DIR = "static/barcodes"
os.makedirs(BARCODE_DIR, exist_ok=True)

# Database connection
conn = pyodbc.connect("DRIVER={SQL Server};SERVER=WINDOWS-595CIJO\\SQLEXPRESS;DATABASE=BARCODE2;UID=alankrit2004;PWD=alankrit1306#")
cursor = conn.cursor()

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
        
        cursor.execute("SELECT ISNULL(MAX(id), 0) + 1 FROM Products")  
        product_id = cursor.fetchone()

        if product_id is None or product_id[0] is None:
            return jsonify({"error": "Failed to retrieve product ID"}), 500

        product_id = product_id[0]

        gtin = generate_gtin_13(product_id)
        
        print(f"Generating barcode for GTIN: {gtin}")  # Debugging
        
        barcode_obj = barcode.get("ean13", gtin, writer=ImageWriter())
        if barcode_obj is None:
            return jsonify({"error": "Barcode generation failed"}), 500
        
        image_path = os.path.join(BARCODE_DIR, f"{gtin}.png")
        barcode_obj.save(image_path)

        cursor.execute(
            "INSERT INTO Products (name, price, gtin, barcode_image_path) VALUES (?, ?, ?, ?)",
            (product_name, price, gtin, image_path)
        )
        conn.commit()

        return jsonify({"gtin": gtin, "image_path": image_path})

    except Exception as e:
        import traceback
        print(traceback.format_exc())  # Print full error traceback
        return jsonify({"error": str(e)}), 500


@app.route("/fetch-product/<string:gtin>", methods=["GET"])
def fetch_product(gtin):
    try:
        cursor.execute("SELECT name, price, barcode_image_path FROM Products WHERE GTIN = ?", gtin)
        product = cursor.fetchone()
        
        if not product:
            return jsonify({"error": "Product not found"}), 404
        
        return jsonify({"product_name": product[0], "price": product[1], "barcode_image": product[2]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, port = 8080)
