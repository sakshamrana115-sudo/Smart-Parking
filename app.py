import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- CONFIGURATION ---
DB_NAME = "parking_pro.db"
TOTAL_SLOTS = 12
HOURLY_RATE = 20

st.set_page_config(page_title="Smart Parking Pro", layout="wide")

# --- DATABASE LOGIC ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    # Table for Bookings
    cur.execute('''CREATE TABLE IF NOT EXISTS bookings 
                   (slot_no INTEGER PRIMARY KEY, owner_name TEXT, 
                    vehicle_no TEXT, checkin_time TEXT)''')
    # Table for Revenue History
    cur.execute('''CREATE TABLE IF NOT EXISTS history 
                   (id INTEGER PRIMARY KEY AUTOINCREMENT, slot_no INTEGER, 
                    amount REAL, paid_at TEXT)''')
    # Table for Admins (Nayi Table)
    cur.execute('''CREATE TABLE IF NOT EXISTS admins 
                   (username TEXT PRIMARY KEY, password TEXT)''')
    
    # Default admin agar koi nahi hai toh
    cur.execute("SELECT COUNT(*) FROM admins")
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO admins VALUES (?, ?)", ("admin", "admin123"))
        
    conn.commit()
    conn.close()

def get_booked_slots():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM bookings", conn)
    conn.close()
    return df

def check_admin(u, p):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT * FROM admins WHERE username=? AND password=?", (u, p))
    result = cur.fetchone()
    conn.close()
    return result

init_db()

# --- SESSION STATE ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.role = None
if 'booking_slot' not in st.session_state:
    st.session_state.booking_slot = None

# --- LOGIN SCREEN ---
if not st.session_state.logged_in:
    st.title("🔐 Smart Parking Login")
    col1, col2 = st.columns(2)
    with col1:
        st.info("### 👨‍💼 Admin Login")
        admin_user = st.text_input("Username")
        admin_pass = st.text_input("Password", type="password")
        if st.button("Login as Admin"):
            if check_admin(admin_user, admin_pass):
                st.session_state.logged_in = True
                st.session_state.role = "admin"
                st.session_state.current_user = admin_user
                st.rerun()
            else:
                st.error("Invalid Username or Password")
    with col2:
        st.success("### 🚗 User Access")
        if st.button("Enter as User"):
            st.session_state.logged_in = True
            st.session_state.role = "user"
            st.rerun()
    st.stop()

# --- LOGOUT ---
if st.sidebar.button("🚪 Log Out"):
    st.session_state.clear()
    st.rerun()

# ================= USER POV =================
if st.session_state.role == "user":
    st.title("🚗 Customer Booking Portal")
    booked_df = get_booked_slots()
    booked_slots = booked_df['slot_no'].tolist()
    
    cols = st.columns(4)
    for i in range(1, TOTAL_SLOTS + 1):
        with cols[(i - 1) % 4]:
            if i in booked_slots:
                st.error(f"Slot {i} \n\n OCCUPIED")
            else:
                st.success(f"Slot {i} \n\n AVAILABLE")
                if st.button(f"Book Slot {i}", key=f"u_{i}"):
                    st.session_state.booking_slot = i
    
    if st.session_state.booking_slot:
        with st.form("book_form"):
            st.write(f"### Booking Slot {st.session_state.booking_slot}")
            name = st.text_input("Name")
            vno = st.text_input("Vehicle No").upper()
            if st.form_submit_button("Confirm"):
                conn = sqlite3.connect(DB_NAME)
                conn.execute("INSERT INTO bookings VALUES (?,?,?,?)", 
                             (st.session_state.booking_slot, name, vno, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                conn.commit()
                conn.close()
                st.session_state.booking_slot = None
                st.rerun()

# ================= ADMIN POV =================
elif st.session_state.role == "admin":
    st.sidebar.title(f"Welcome, {st.session_state.current_user}")
    menu = st.sidebar.radio("Menu", ["Monitor", "Billing", "Reports", "Manage Admins"])

    if menu == "Monitor":
        st.title("📊 Real-Time Monitor")
        booked_df = get_booked_slots()
        booked_slots = booked_df['slot_no'].tolist()
        cols = st.columns(4)
        for i in range(1, TOTAL_SLOTS + 1):
            with cols[(i - 1) % 4]:
                if i in booked_slots:
                    d = booked_df[booked_df['slot_no'] == i].iloc[0]
                    st.error(f"Slot {i}\n\n{d['vehicle_no']}")
                else:
                    st.success(f"Slot {i}\n\nEMPTY")

    elif menu == "Manage Admins":
        st.title("👥 Admin Management")
        st.subheader("Create New Admin Account")
        new_user = st.text_input("New Admin Username")
        new_pass = st.text_input("New Admin Password", type="password")
        
        if st.button("Create Admin"):
            if new_user and new_pass:
                try:
                    conn = sqlite3.connect(DB_NAME)
                    cur = conn.cursor()
                    cur.execute("INSERT INTO admins VALUES (?, ?)", (new_user, new_pass))
                    conn.commit()
                    conn.close()
                    st.success(f"Admin '{new_user}' created successfully!")
                except:
                    st.error("Username already exists!")
            else:
                st.warning("Please fill all fields.")
        
        st.divider()
        st.subheader("Existing Admins")
        conn = sqlite3.connect(DB_NAME)
        admins_df = pd.read_sql_query("SELECT username FROM admins", conn)
        st.table(admins_df)
        conn.close()

    # (Add your Billing and Reports logic here as per previous code)
    
