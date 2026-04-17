from flask import Flask, render_template, request, jsonify
import sqlite3
from datetime import datetime

app = Flask(__name__)

def db_query(query, params=(), fetch=False):
    conn = sqlite3.connect("parking.db")
    cur = conn.cursor()
    cur.execute(query, params)
    data = cur.fetchall() if fetch else None
    conn.commit()
    conn.close()
    return data

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/stats')
def get_stats():
    # Calculate Total Revenue & Counts
    booked = db_query("SELECT COUNT(*) FROM bookings", fetch=True)[0][0]
    revenue = db_query("SELECT SUM(amount_paid) FROM history", fetch=True)[0][0] or 0
    return jsonify({"booked": booked, "revenue": revenue, "free": 12 - booked})

@app.route('/api/book', methods=['POST'])
def book():
    data = request.json
    db_query("INSERT INTO bookings (slot_no, owner_name, vehicle_no, checkin_time) VALUES (?,?,?,?)",
             (data['slot'], data['owner'], data['vehicle'].upper(), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    return jsonify({"status": "success"})

if __name__ == '__main__':
    app.run(debug=True)
