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

# --- SESSION STATE INITIALIZATION ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.role = None
if 'booking_slot' not in st.session_state:
    st.session_state.booking_slot = None

# --- LOGIN INTERFACE ---
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
        st.write("Click below to book your parking slot.")
        if st.button("Enter as User"):
            st.session_state.logged_in = True
            st.session_state.role = "user"
            st.rerun()
    st.stop()

# --- LOGOUT ---
if st.sidebar.button("🚪 Log Out"):
    st.session_state.logged_in = False
    st.session_state.role = None
    st.session_state.booking_slot = None
    st.rerun()

# Fetch latest data
booked_df = get_booked_slots()
booked_slots = booked_df['slot_no'].tolist()

# Helper function for button click
def set_booking_slot(slot_id):
    st.session_state.booking_slot = slot_id

# ================= USER POV (FIXED BUTTONS) =================
if st.session_state.role == "user":
    st.title("🚗 Customer Booking Portal")
    st.info("Select an available slot to park your vehicle.")
    
    # Grid Layout
    cols = st.columns(4)
    for i in range(1, TOTAL_SLOTS + 1):
        with cols[(i - 1) % 4]:
            if i in booked_slots:
                st.error(f"Slot {i} \n\n OCCUPIED")
                st.button("Occupied", key=f"occ_{i}", disabled=True)
            else:
                st.success(f"Slot {i} \n\n AVAILABLE")
                # Ye button ab session state update karega
                st.button(f"Book Slot {i}", key=f"user_slot_{i}", on_click=set_booking_slot, args=(i,))

    # AGAR USER NE SLOT SELECT KIYA HAI
    if st.session_state.booking_slot:
        st.divider()
        st.markdown(f"### 📝 Booking Details for **Slot {st.session_state.booking_slot}**")
        
        with st.form(key='user_booking_form'):
            u_name = st.text_input("Your Full Name")
            u_vno = st.text_input("Vehicle Number (e.g., DL 1C 1234)").upper()
            
            c1, c2 = st.columns([1, 4])
            with c1:
                if st.form_submit_button("Confirm"):
                    if u_name and u_vno:
                        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        conn = sqlite3.connect(DB_NAME)
                        cur = conn.cursor()
                        try:
                            cur.execute("INSERT INTO bookings VALUES (?, ?, ?, ?)", 
                                        (st.session_state.booking_slot, u_name, u_vno, now))
                            conn.commit()
                            st.success(f"✅ Slot {st.session_state.booking_slot} is now yours!")
                            st.session_state.booking_slot = None # Reset
                            st.rerun()
                        except:
                            st.error("This slot was just taken! Please pick another.")
                        finally:
                            conn.close()
                    else:
                        st.warning("Please fill in your name and vehicle number.")
            with c2:
                if st.form_submit_button("Cancel"):
                    st.session_state.booking_slot = None
                    st.rerun()

# ================= ADMIN POV =================
elif st.session_state.role == "admin":
    st.sidebar.title(f"Admin: {st.session_state.role}")
    menu = st.sidebar.radio("Go to:", ["Monitor", "Billing", "History"])

    if menu == "Monitor":
        st.title("📊 Real-Time Monitor")
        cols = st.columns(4)
        for i in range(1, TOTAL_SLOTS + 1):
            with cols[(i - 1) % 4]:
                if i in booked_slots:
                    data = booked_df[booked_df['slot_no'] == i].iloc[0]
                    st.error(f"Slot {i}\n\n{data['vehicle_no']}\n({data['owner_name']})")
                else:
                    st.success(f"Slot {i}\n\nEMPTY")

    elif menu == "Billing":
        st.title("💸 Checkout & Payments")
        search = st.text_input("Enter Vehicle No to Exit").upper()
        if search:
            res = booked_df[booked_df['vehicle_no'].str.contains(search)]
            if not res.empty:
                st.table(res)
                slot_id = res['slot_no'].values[0]
                if st.button(f"Process Checkout for Slot {slot_id}"):
                    # Calculate Billing
                    entry_time = datetime.strptime(res['checkin_time'].values[0], "%Y-%m-%d %H:%M:%S")
                    stay_hours = max(1, (datetime.now() - entry_time).seconds // 3600)
                    total_amt = stay_hours * HOURLY_RATE
                    
                    conn = sqlite3.connect(DB_NAME)
                    cur = conn.cursor()
                    cur.execute("DELETE FROM bookings WHERE slot_no=?", (int(slot_id),))
                    cur.execute("INSERT INTO history (slot_no, amount, paid_at) VALUES (?,?,?)", 
                                (int(slot_id), total_amt, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                    conn.commit()
                    conn.close()
                    st.balloons()
                    st.success(f"Payment Received: ₹{total_amt}. Slot is now FREE!")
                    st.rerun()
            else:
                st.info("No active booking found.")

    elif menu == "History":
        st.title("📈 Revenue & History")
        conn = sqlite3.connect(DB_NAME)
        history_df = pd.read_sql_query("SELECT * FROM history ORDER BY id DESC", conn)
        st.metric("Total Earnings", f"₹{history_df['amount'].sum() if not history_df.empty else 0}")
        st.dataframe(history_df, use_container_width=True)
        conn.close()
