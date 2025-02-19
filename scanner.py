import cv2
from pyzbar.pyzbar import decode
import pyodbc

# Database connection details
conn = pyodbc.connect("DRIVER={SQL Server};SERVER=GLITCHPC/SQLEXPRESS;DATABASE=BARCODE;Trusted_Connection=True")
cursor = conn.cursor()

def scan_barcode_camera():
    try:
        cap = cv2.VideoCapture(0)  # Open the default camera
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Failed to capture frame")
                continue

            decoded_objects = decode(frame)
            for obj in decoded_objects:
                barcode_data = obj.data.decode("utf-8")
                print(f"Barcode detected: {barcode_data}")

                # Debug: Check all barcodes in the database
                cursor.execute("SELECT Barcode FROM Products")
                all_barcodes = [row[0] for row in cursor.fetchall()]
                print(f"All barcodes in database: {all_barcodes}")

                # Query with the EXACT barcode string
                cursor.execute("SELECT Name, Price, Barcode FROM Products WHERE Barcode = ?", (barcode_data,))
                product = cursor.fetchone()

                if not product:
                    # Debug: Check for partial matches
                    for db_barcode in all_barcodes:
                        if db_barcode in barcode_data or barcode_data in db_barcode:
                            print(f"Potential partial match: DB has '{db_barcode}', scan found '{barcode_data}'")
                    print("Product not found in the database")
                    return {"error": "Product not found"}

                # Convert the row to named values
                product_name, price, barcode = product
                
                print(f"Product Name: {product_name}")
                print(f"Price: {price}")
                print(f"Barcode: {barcode}")

                cap.release()
                cv2.destroyAllWindows()
                
                return {
                    "product_name": product_name,
                    "price": price,
                    "barcode": barcode
                }

            cv2.imshow("Barcode Scanner", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()
        return {"error": "No barcode detected"}

    except Exception as e:
        print(f"Error: {e}")
        return {"error": str(e)}

# Run the function
if __name__ == "__main__":
    result = scan_barcode_camera()
    print(result)