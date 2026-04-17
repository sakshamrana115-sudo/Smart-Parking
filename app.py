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

# Initialize Database
init_db()

# --- SIDEBAR NAVIGATION (Yeh missing tha!) ---
st.sidebar.header("🅿️ Admin Panel")
menu = st.sidebar.radio("Navigation", ["Live Grid", "Search & Checkout", "Revenue Reports"])

# Get latest data
booked_df = get_booked_slots()
booked_slots = booked_df['slot_no'].tolist()

# --- BUTTON CLICK HANDLER ---
def handle_booking_click(slot_id):
    st.session_state.booking_slot = slot_id

# --- PAGE 1: LIVE GRID ---
if menu == "Live Grid":
    st.title("🅿️ Smart Parking Management System")
    st.subheader("Real-Time Slot Status")
    
    # Grid Layout
    cols = st.columns(4)
    for i in range(1, TOTAL_SLOTS + 1):
        with cols[(i - 1) % 4]:
            if i in booked_slots:
                vehicle = booked_df[booked_df['slot_no'] == i]['vehicle_no'].values[0]
                st.error(f"Slot {i} \n\n {vehicle}")
            else:
                st.success(f"Slot {i} \n\n AVAILABLE")
                st.button(f"Book Slot {i}", key=f"btn_{i}", on_click=handle_booking_click, args=(i,))

    # Booking Form
    if 'booking_slot' in st.session_state and st.session_state.booking_slot is not None:
        st.divider()
        st.markdown(f"### 📝 Fill Details for **Slot {st.session_state.booking_slot}**")
        with st.form(key='booking_form'):
            owner = st.text_input("Owner Name")
            vehicle = st.text_input("Vehicle Number").upper()
            col1, col2 = st.columns([1, 5])
            with col1:
                if st.form_submit_button("Confirm"):
                    if owner and vehicle:
                        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        conn = sqlite3.connect(DB_NAME)
                        cur = conn.cursor()
                        cur.execute("INSERT INTO bookings VALUES (?, ?, ?, ?)", 
                                    (st.session_state.booking_slot, owner, vehicle, now))
                        conn.commit()
                        conn.close()
                        st.session_state.booking_slot = None
                        st.success("Slot Booked!")
                        st.rerun()
                    else:
                        st.warning("Please fill details!")
            with col2:
                if st.form_submit_button("Cancel"):
                    st.session_state.booking_slot = None
                    st.rerun()

# --- PAGE 2: SEARCH & CHECKOUT ---
elif menu == "Search & Checkout":
    st.title("🔍 Search & Checkout")
    search_q = st.text_input("Enter Vehicle Number").upper()
    if search_q:
        result = booked_df[booked_df['vehicle_no'].str.contains(search_q)]
        if not result.empty:
            st.table(result)
            slot_to_exit = result['slot_no'].values[0]
            if st.button(f"Process Checkout for Slot {slot_to_exit}"):
                checkin_str = result['checkin_time'].values[0]
                checkin_dt = datetime.strptime(checkin_str, "%Y-%m-%d %H:%M:%S")
                hours = max(1, (datetime.now() - checkin_dt).seconds // 3600)
                bill = hours * HOURLY_RATE
                
                conn = sqlite3.connect(DB_NAME)
                cur = conn.cursor()
                cur.execute("DELETE FROM bookings WHERE slot_no = ?", (int(slot_to_exit),))
                cur.execute("INSERT INTO history (slot_no, amount, paid_at) VALUES (?, ?, ?)",
                            (int(slot_to_exit), bill, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                conn.commit()
                conn.close()
                st.success(f"Payment Received: ₹{bill}. Slot is now FREE.")
                st.rerun()
        else:
            st.info("No vehicle found.")

# --- PAGE 3: REVENUE REPORTS ---
elif menu == "Revenue Reports":
    st.title("📊 Revenue Reports")
    conn = sqlite3.connect(DB_NAME)
    history_df = pd.read_sql_query("SELECT * FROM history", conn)
    total_rev = history_df['amount'].sum() if not history_df.empty else 0
    st.metric("Total Money Collected", f"₹{total_rev}")
    st.dataframe(history_df, use_container_width=True)
    conn.close()
