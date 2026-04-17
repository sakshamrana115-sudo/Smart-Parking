from flask import Flask, render_template, request, jsonify
import sqlite3
from datetime import datetime

app = Flask(__name__)
DB_NAME = "parking.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS bookings 
                   (slot_no INTEGER PRIMARY KEY, owner_name TEXT, 
                    vehicle_no TEXT, checkin_time TEXT)''')
    conn.commit()
    conn.close()

@app.route('/')
def home():
    return render_template('index.html')

# API: Saare slots ki information lene ke liye
@app.route('/api/slots', methods=['GET'])
def get_slots():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT * FROM bookings")
    rows = cur.fetchall()
    booked_slots = {r[0]: {"owner": r[1], "vehicle": r[2], "time": r[3]} for r in rows}
    conn.close()
    return jsonify(booked_slots)

# API: New booking karne ke liye
@app.route('/api/book', methods=['POST'])
def book_slot():
    data = request.json
    slot_no = data['slot_no']
    owner = data['owner']
    vehicle = data['vehicle'].upper()
    time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("INSERT INTO bookings VALUES (?, ?, ?, ?)", (slot_no, owner, vehicle, time))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"})
    except:
        return jsonify({"status": "error", "message": "Slot already booked"}), 400

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
