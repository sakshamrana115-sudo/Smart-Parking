import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- CONFIG ---
DB_NAME = "parking_pro.db"
TOTAL_SLOTS = 12
HOURLY_RATE = 20

st.set_page_config(page_title="Smart Parking Pro", layout="wide")

# --- DATABASE FUNCTIONS ---
def run_query(query, params=(), fetch=False):
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute(query, params)
        conn.commit()
        return cur.fetchall() if fetch else None

def init_db():
    run_query('''CREATE TABLE IF NOT EXISTS bookings 
                 (slot_no INTEGER PRIMARY KEY, owner_name TEXT, vehicle_no TEXT, checkin_time TEXT)''')
    run_query('''CREATE TABLE IF NOT EXISTS history 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, slot_no INTEGER, amount REAL, paid_at TEXT)''')
    run_query('''CREATE TABLE IF NOT EXISTS admins (username TEXT PRIMARY KEY, password TEXT)''')
    if not run_query("SELECT * FROM admins WHERE username='admin'", fetch=True):
        run_query("INSERT INTO admins VALUES ('admin', 'admin123')")

init_db()

# --- SESSION STATE ---
for key, val in [('logged_in', False), ('role', None), ('booking_slot', None), ('current_user', None)]:
    if key not in st.session_state: st.session_state[key] = val

# --- LOGIN ---
if not st.session_state.logged_in:
    st.title("🔐 Smart Parking Login")
    c1, c2 = st.columns(2)
    with c1:
        st.info("### 👨‍💼 Admin Login")
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.button("Login as Admin"):
            if run_query("SELECT * FROM admins WHERE username=? AND password=?", (u, p), fetch=True):
                st.session_state.update({"logged_in": True, "role": "admin", "current_user": u})
                st.rerun()
            else: st.error("Invalid Credentials")
    with c2:
        st.success("### 🚗 User Access")
        if st.button("Enter as User"):
            st.session_state.update({"logged_in": True, "role": "user"})
            st.rerun()
    st.stop()

# --- SHARED UI ---
if st.sidebar.button("🚪 Log Out"):
    st.session_state.clear()
    st.rerun()

booked_df = pd.read_sql(f"SELECT * FROM bookings", sqlite3.connect(DB_NAME))
booked_slots = booked_df['slot_no'].tolist()

# ================= USER POV =================
if st.session_state.role == "user":
    st.title("🚗 Customer Portal")
    cols = st.columns(4)
    for i in range(1, TOTAL_SLOTS + 1):
        with cols[(i-1)%4]:
            if i in booked_slots: st.error(f"Slot {i}\n\nOccupied")
            else:
                st.success(f"Slot {i}\n\nAvailable")
                if st.button(f"Book {i}", key=f"b{i}"): st.session_state.booking_slot = i
    
    if st.session_state.booking_slot:
        with st.form("bk"):
            name, vno = st.text_input("Name"), st.text_input("Vehicle").upper()
            if st.form_submit_button("Confirm") and name and vno:
                run_query("INSERT INTO bookings VALUES (?,?,?,?)", (st.session_state.booking_slot, name, vno, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                st.session_state.booking_slot = None
                st.rerun()

# ================= ADMIN POV =================
else:
    st.sidebar.title(f"Admin: {st.session_state.current_user}")
    menu = st.sidebar.radio("Menu", ["Monitor", "Billing", "Reports", "Manage Admins"])

    if menu == "Monitor":
        st.title("📊 Live View")
        cols = st.columns(4)
        for i in range(1, TOTAL_SLOTS + 1):
            with cols[(i-1)%4]:
                if i in booked_slots:
                    d = booked_df[booked_df['slot_no']==i].iloc[0]
                    st.error(f"Slot {i}\n\n{d['vehicle_no']}")
                else: st.success(f"Slot {i}\n\nFree")

    elif menu == "Billing":
        st.title("💸 Checkout")
        v = st.text_input("Search Vehicle").upper()
        res = booked_df[booked_df['vehicle_no'].str.contains(v)] if v else None
        if res is not None and not res.empty:
            st.table(res)
            if st.button("Process Exit"):
                s_id = int(res['slot_no'].iloc[0])
                entry = datetime.strptime(res['checkin_time'].iloc[0], "%Y-%m-%d %H:%M:%S")
                hrs = max(1, (datetime.now() - entry).seconds // 3600)
                run_query("DELETE FROM bookings WHERE slot_no=?", (s_id,))
                run_query("INSERT INTO history (slot_no, amount, paid_at) VALUES (?,?,?)", (s_id, hrs*HOURLY_RATE, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                st.success(f"Bill: ₹{hrs*HOURLY_RATE}"); st.rerun()

    elif menu == "Manage Admins":
        st.title("👥 Admin Settings")
        with st.form("new_ad"):
            nu, np = st.text_input("New Username"), st.text_input("New Password", type="password")
            if st.form_submit_button("Create Admin") and nu and np:
                try: 
                    run_query("INSERT INTO admins VALUES (?,?)", (nu, np))
                    st.success("Admin Added!")
                except: st.error("Exists!")
        st.table(pd.read_sql("SELECT username FROM admins", sqlite3.connect(DB_NAME)))

    elif menu == "Reports":
        st.title("📈 History")
        dfh = pd.read_sql("SELECT * FROM history", sqlite3.connect(DB_NAME))
        st.metric("Total Revenue", f"₹{dfh['amount'].sum() if not dfh.empty else 0}")
        st.dataframe(dfh)
