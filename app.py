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
        admin_user = st.text_input("Admin Username")
        admin_pass = st.text_input("Admin Password", type="password")
        if st.button("Login as Admin"):
            if admin_user == "admin" and admin_pass == "1234":
                st.session_state.logged_in = True
                st.session_state.role = "admin"
                st.rerun()
            else: st.error("Invalid Credentials")
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

# Fetch latest data
booked_df = get_booked_slots()
booked_slots = booked_df['slot_no'].tolist()

def set_slot(slot_id):
    st.session_state.booking_slot = slot_id

# ================= USER POV (FIXED FORM) =================
if st.session_state.role == "user":
    st.title("🚗 Customer Booking Portal")
    
    # Grid
    cols = st.columns(4)
    for i in range(1, TOTAL_SLOTS + 1):
        with cols[(i - 1) % 4]:
            if i in booked_slots:
                st.error(f"Slot {i} \n\n OCCUPIED")
                st.button("Occupied", key=f"occ_{i}", disabled=True)
            else:
                st.success(f"Slot {i} \n\n AVAILABLE")
                st.button(f"Book Slot {i}", key=f"btn_{i}", on_click=set_slot, args=(i,))

    # Booking Form Area
    if st.session_state.booking_slot:
        st.divider()
        # Hum ek placeholder banayenge jise clear kiya ja sake
        form_container = st.container()
        with form_container:
            st.markdown(f"### 📝 Booking Details for **Slot {st.session_state.booking_slot}**")
            with st.form(key='user_booking_form', clear_on_submit=True):
                u_name = st.text_input("Your Full Name")
                u_vno = st.text_input("Vehicle Number").upper()
                
                c1, c2 = st.columns([1, 4])
                with c1:
                    submit = st.form_submit_button("Confirm")
                with c2:
                    cancel = st.form_submit_button("Cancel")

                if cancel:
                    st.session_state.booking_slot = None
                    st.rerun()

                if submit:
                    if u_name and u_vno:
                        # Re-check if slot is still free
                        check_df = get_booked_slots()
                        if st.session_state.booking_slot not in check_df['slot_no'].tolist():
                            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            conn = sqlite3.connect(DB_NAME)
                            cur = conn.cursor()
                            cur.execute("INSERT INTO bookings VALUES (?, ?, ?, ?)", 
                                        (st.session_state.booking_slot, u_name, u_vno, now))
                            conn.commit()
                            conn.close()
                            
                            # Success! Clear state and refresh
                            st.session_state.booking_slot = None
                            st.toast("✅ Slot Booked Successfully!")
                            st.rerun()
                        else:
                            st.error("🚨 Oops! This slot was just taken by someone else.")
                    else:
                        st.warning("⚠️ Please enter all details.")

# ================= ADMIN POV =================
elif st.session_state.role == "admin":
    st.sidebar.title("🛡️ Admin Panel")
    menu = st.sidebar.radio("Navigation", ["Monitor", "Billing", "History"])

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
        st.title("💸 Checkout")
        search = st.text_input("Search Vehicle Number").upper()
        if search:
            res = booked_df[booked_df['vehicle_no'].str.contains(search)]
            if not res.empty:
                st.table(res)
                if st.button("Process Checkout"):
                    s_id = res['slot_no'].values[0]
                    # Logic (Price calc + history insert)
                    c_time = datetime.strptime(res['checkin_time'].values[0], "%Y-%m-%d %H:%M:%S")
                    hours = max(1, (datetime.now() - c_time).seconds // 3600)
                    bill = hours * HOURLY_RATE
                    
                    conn = sqlite3.connect(DB_NAME)
                    cur = conn.cursor()
                    cur.execute("DELETE FROM bookings WHERE slot_no=?", (int(s_id),))
                    cur.execute("INSERT INTO history (slot_no, amount, paid_at) VALUES (?,?,?)", 
                                (int(s_id), bill, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                    conn.commit()
                    conn.close()
                    st.success(f"Done! Bill: ₹{bill}")
                    st.rerun()
            else: st.info("Not found.")

    elif menu == "History":
        st.title("📊 Financials")
        conn = sqlite3.connect(DB_NAME)
        h_df = pd.read_sql_query("SELECT * FROM history ORDER BY id DESC", conn)
        st.metric("Revenue", f"₹{h_df['amount'].sum() if not h_df.empty else 0}")
        st.dataframe(h_df)
        conn.close()
