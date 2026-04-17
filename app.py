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
    cur.execute('''CREATE TABLE IF NOT EXISTS bookings 
                   (slot_no INTEGER PRIMARY KEY, owner_name TEXT, 
                    vehicle_no TEXT, checkin_time TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS history 
                   (id INTEGER PRIMARY KEY AUTOINCREMENT, slot_no INTEGER, 
                    amount REAL, paid_at TEXT)''')
    conn.commit()
    conn.close()

def get_booked_slots():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM bookings", conn)
    conn.close()
    return df

init_db()

# --- LOGIN INTERFACE ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.role = None

if not st.session_state.logged_in:
    st.title("🔐 Smart Parking Login")
    col1, col2 = st.columns(2)
    
    with col1:
        st.info("### 👨‍💼 Admin Login")
        admin_user = st.text_input("Admin Username")
        admin_pass = st.text_input("Admin Password", type="password")
        if st.button("Login as Admin"):
            if admin_user == "admin" and admin_pass == "1234":
                st.session_state.logged_in = True
                st.session_state.role = "admin"
                st.rerun()
            else:
                st.error("Invalid Admin Credentials")

    with col2:
        st.success("### 🚗 User Access")
        st.write("No password required for customers to book.")
        if st.button("Enter as User"):
            st.session_state.logged_in = True
            st.session_state.role = "user"
            st.rerun()
    st.stop()

# --- LOGOUT BUTTON ---
if st.sidebar.button("Log Out"):
    st.session_state.logged_in = False
    st.session_state.role = None
    st.rerun()

# --- SHARED DATA ---
booked_df = get_booked_slots()
booked_slots = booked_df['slot_no'].tolist()

def handle_booking_click(slot_id):
    st.session_state.booking_slot = slot_id

# ================= USER POV =================
if st.session_state.role == "user":
    st.title("🚗 Customer Booking Portal")
    st.write("Select an available slot to park your vehicle.")
    
    cols = st.columns(4)
    for i in range(1, TOTAL_SLOTS + 1):
        with cols[(i - 1) % 4]:
            if i in booked_slots:
                st.error(f"Slot {i} \n\n OCCUPIED")
            else:
                st.success(f"Slot {i} \n\n AVAILABLE")
                st.button(f"Book Slot {i}", key=f"user_btn_{i}", on_click=handle_booking_click, args=(i,))

    if 'booking_slot' in st.session_state and st.session_state.booking_slot:
        with st.form("user_booking"):
            st.write(f"### Booking Slot #{st.session_state.booking_slot}")
            name = st.text_input("Your Name")
            v_no = st.text_input("Vehicle Number").upper()
            if st.form_submit_button("Confirm Booking"):
                if name and v_no:
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    conn = sqlite3.connect(DB_NAME)
                    cur = conn.cursor()
                    cur.execute("INSERT INTO bookings VALUES (?, ?, ?, ?)", (st.session_state.booking_slot, name, v_no, now))
                    conn.commit()
                    conn.close()
                    st.success("Booking Successful! Admin will process your checkout.")
                    st.session_state.booking_slot = None
                    st.rerun()
                else:
                    st.warning("Please fill all details.")

# ================= ADMIN POV =================
elif st.session_state.role == "admin":
    st.sidebar.header("🛡️ Admin Panel")
    menu = st.sidebar.radio("Navigation", ["Live Monitor", "Checkout & Billing", "Revenue Reports"])

    if menu == "Live Monitor":
        st.title("📊 Real-Time Parking Monitor")
        cols = st.columns(4)
        for i in range(1, TOTAL_SLOTS + 1):
            with cols[(i - 1) % 4]:
                if i in booked_slots:
                    data = booked_df[booked_df['slot_no'] == i].iloc[0]
                    st.error(f"Slot {i} \n\n {data['vehicle_no']} \n ({data['owner_name']})")
                else:
                    st.success(f"Slot {i} \n\n EMPTY")

    elif menu == "Checkout & Billing":
        st.title("💸 Process Checkout")
        search = st.text_input("Search Vehicle Number").upper()
        if search:
            res = booked_df[booked_df['vehicle_no'].str.contains(search)]
            if not res.empty:
                st.dataframe(res)
                s_id = res['slot_no'].values[0]
                if st.button(f"Checkout Slot {s_id}"):
                    # Logic for billing
                    c_time = datetime.strptime(res['checkin_time'].values[0], "%Y-%m-%d %H:%M:%S")
                    hours = max(1, (datetime.now() - c_time).seconds // 3600)
                    bill = hours * HOURLY_RATE
                    
                    conn = sqlite3.connect(DB_NAME)
                    cur = conn.cursor()
                    cur.execute("DELETE FROM bookings WHERE slot_no=?", (int(s_id),))
                    cur.execute("INSERT INTO history (slot_no, amount, paid_at) VALUES (?,?,?)", (int(s_id), bill, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                    conn.commit()
                    conn.close()
                    st.success(f"Checked out! Bill: ₹{bill}")
                    st.rerun()
            else:
                st.info("No such vehicle found.")

    elif menu == "Revenue Reports":
        st.title("📈 Financial Reports")
        conn = sqlite3.connect(DB_NAME)
        hist = pd.read_sql_query("SELECT * FROM history", conn)
        st.metric("Total Revenue", f"₹{hist['amount'].sum() if not hist.empty else 0}")
        st.table(hist)
        conn.close()
