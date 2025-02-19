from fastapi import FastAPI, Form, HTTPException
import os
import barcode
from barcode.writer import ImageWriter
import asyncpg  # Use asyncpg for PostgreSQL

app = FastAPI()

BARCODE_DIR = "static/barcodes"
os.makedirs(BARCODE_DIR, exist_ok=True)

# Supabase Database Connection
DATABASE_URL = "postgresql://postgres:alankrit_321#@db.kpwsabrvzergvzpgilhy.supabase.co:5432/postgres"

async def get_db_connection():
    return await asyncpg.connect(DATABASE_URL)

def generate_gtin_13(product_id: int):
    """Generates a GTIN-13 compliant barcode number with a check digit."""
    base_gtin = f"123456{product_id:06d}"  # 6-digit prefix + 6-digit product ID
    checksum = sum((3 if i % 2 else 1) * int(d) for i, d in enumerate(base_gtin)) % 10
    check_digit = (10 - checksum) % 10
    return base_gtin + str(check_digit)

@app.post("/generate-barcode/")
async def generate_barcode(product_name: str = Form(...), price: float = Form(...)):
    try:
        conn = await get_db_connection()
        
        # Get the latest product ID
        product_id = await conn.fetchval("SELECT COALESCE(MAX(id), 0) + 1 FROM Products")

        # Generate GTIN-13 barcode number
        gtin = generate_gtin_13(product_id)

        # Generate barcode image
        barcode_obj = barcode.get("ean13", gtin, writer=ImageWriter())
        image_path = os.path.join(BARCODE_DIR, f"{gtin}.png")
        barcode_obj.save(image_path)

        # Store in Supabase (PostgreSQL)
        await conn.execute(
            "INSERT INTO Products (id, name, price, gtin, barcode_image_path) VALUES ($1, $2, $3, $4, $5)",
            product_id, product_name, price, gtin, image_path
        )
        
        await conn.close()
        
        return {"gtin": gtin, "image_path": image_path}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/fetch-product/{gtin}")
async def fetch_product(gtin: str):
    try:
        conn = await get_db_connection()
        
        product = await conn.fetchrow(
            "SELECT name, price, barcode_image_path FROM Products WHERE gtin = $1", gtin
        )
        
        await conn.close()
        
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        return {"product_name": product["name"], "price": product["price"], "barcode_image": product["barcode_image_path"]}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
