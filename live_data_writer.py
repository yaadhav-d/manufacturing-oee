import time
import random
from datetime import datetime
import mysql.connector

# --------------------------------------------------
# DATABASE CONFIG (Railway)
# --------------------------------------------------
DB_CONFIG = {
    "host": "YOUR_RAILWAY_HOST",
    "user": "YOUR_DB_USER",
    "password": "YOUR_DB_PASSWORD",
    "database": "manufacturing_live_dashboard",
    "port": 3306
}

# --------------------------------------------------
# MACHINE LIST (matches machines table)
# --------------------------------------------------
MACHINES = ["M-1", "M-2", "M-3", "M-4", "M-5"]

# --------------------------------------------------
# CONNECT TO MYSQL
# --------------------------------------------------
def get_connection():
    return mysql.connector.connect(**DB_CONFIG)

# --------------------------------------------------
# GENERATE LIVE MACHINE DATA
# --------------------------------------------------
def generate_machine_data(machine_id):
    return {
        "timestamp": datetime.now(),
        "machine_id": machine_id,
        "temperature": round(random.uniform(60, 95), 2),
        "vibration": round(random.uniform(2, 9), 2),
        "units": random.randint(5, 20)
    }

# --------------------------------------------------
# INSERT DATA INTO DATABASE
# --------------------------------------------------
def insert_data(cursor, data):
    query = """
        INSERT INTO machine_telemetry
        (timestamp, machine_id, temperature, vibration, units)
        VALUES (%s, %s, %s, %s, %s)
    """
    values = (
        data["timestamp"],
        data["machine_id"],
        data["temperature"],
        data["vibration"],
        data["units"]
    )
    cursor.execute(query, values)

# --------------------------------------------------
# MAIN LOOP (LIVE WRITER)
# --------------------------------------------------
def main():
    print("🚀 Live data writer started...")

    conn = get_connection()
    cursor = conn.cursor()

    try:
        while True:
            for machine in MACHINES:
                data = generate_machine_data(machine)
                insert_data(cursor, data)

            conn.commit()
            print(f"Inserted data at {datetime.now().strftime('%H:%M:%S')}")

            time.sleep(5)  # write interval (seconds)

    except KeyboardInterrupt:
        print("⛔ Stopped by user")

    finally:
        cursor.close()
        conn.close()

# --------------------------------------------------
if __name__ == "__main__":
    main()
