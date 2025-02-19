from fastapi import FastAPI, Form, HTTPException
import os
import barcode
from barcode.writer import ImageWriter
import pyodbc

app = FastAPI()

BARCODE_DIR = "static/barcodes"
os.makedirs(BARCODE_DIR, exist_ok=True)

# Database connection
# conn = pyodbc.connect("DRIVER={SQL Server};SERVER=GLITCHPC\SQLEXPRESS;DATABASE=BARCODE;Trusted_Connection=True")
# conn = pyodbc.connect(r"DRIVER={SQL Server};SERVER=GLITCHPC\SQLEXPRESS;DATABASE=BARCODE;Trusted_Connection=True")
conn = pyodbc.connect("DRIVER={SQL Server};SERVER=GLITCHPC\\SQLEXPRESS;DATABASE=BARCODE;Trusted_Connection=True")
# conn = pyodbc.connect("DRIVER={SQL Server};SERVER=GlitchPC/SQLEXPRESS;DATABASE=BARCODE;Trusted_Connection=True")
# conn = pyodbc.connect("DRIVER={SQL Server};SERVER=GLITCHPC\\SQLEXPRESS;DATABASE=BARCODE;UID=alankrit2004;PWD=alankrit_321#")





cursor = conn.cursor()

def generate_gtin_13(product_id: int):
    """Generates a GTIN-13 compliant barcode number with a check digit."""
    base_gtin = f"123456{product_id:06d}"  # 6-digit prefix + 6-digit product ID
    checksum = sum((3 if i % 2 else 1) * int(d) for i, d in enumerate(base_gtin)) % 10
    check_digit = (10 - checksum) % 10
    return base_gtin + str(check_digit)

@app.post("/generate-barcode/")
def generate_barcode(product_name: str = Form(...), price: float = Form(...)):
    try:
        # Get latest product ID from database
        cursor.execute("SELECT ISNULL(MAX(id), 0) + 1 FROM Products")  
        product_id = cursor.fetchone()[0]  # Ensures sequential ID without gaps

        # Generate a valid GTIN-13 barcode number
        gtin = generate_gtin_13(product_id)

        # Generate barcode image
        barcode_obj = barcode.get("ean13", gtin, writer=ImageWriter())
        image_path = os.path.join(BARCODE_DIR, f"{gtin}.png")
        barcode_obj.save(image_path)

        # Store in SQL Server
        cursor.execute(
            "INSERT INTO Products (name, price, gtin, barcode_image_path) VALUES (?, ?, ?, ?)",
            (product_name, price, gtin, image_path)
        )
        conn.commit()

        return {"gtin": gtin, "image_path": image_path}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/fetch-product/{gtin}")
def fetch_product(gtin: str):
    try:
        cursor.execute("SELECT name, price, barcode_image_path FROM Products WHERE GTIN = ?", gtin)
        product = cursor.fetchone()
        
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        return {"product_name": product[0], "price": product[1], "barcode_image": product[2]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
