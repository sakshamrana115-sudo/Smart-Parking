from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
import qrcode
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "secret_key_for_session"
DB_NAME = "parking.db"
TOTAL_SLOTS = 12
PRICE_PER_HOUR = 20

def db_query(query, params=(), fetch=False):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(query, params)
    data = cur.fetchall() if fetch else None
    conn.commit()
    conn.close()
    return data

@app.route('/')
def index():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    role = request.form['role']
    
    table = "admins" if role == "admin" else "users"
    user = db_query(f"SELECT * FROM {table} WHERE username=? AND password=?", (username, password), fetch=True)
    
    if user:
        session['user'] = username
        session['role'] = role
        return redirect(url_for('dashboard'))
    else:
        flash("Invalid Credentials")
        return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('index'))
    
    booked_rows = db_query("SELECT slot_no FROM bookings", fetch=True)
    booked_slots = [r[0] for r in booked_rows]
    
    return render_template('dashboard.html', total_slots=TOTAL_SLOTS, booked_slots=booked_slots)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == "__main__":
    app.run(debug=True)
