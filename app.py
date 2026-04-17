import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import qrcode
from PIL import Image
import os

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

# --- UI COMPONENTS ---
init_db()

st.title("🅿️ Smart Parking Management System")

# Sidebar for Navigation & Stats
st.sidebar.header("Admin Dashboard")
menu = st.sidebar.radio("Navigation", ["Live Grid", "Search & Checkout", "Revenue Reports"])

booked_df = get_booked_slots()
booked_slots = booked_df['slot_no'].tolist()

# Sidebar Stats
st.sidebar.metric("Available Slots", TOTAL_SLOTS - len(booked_slots))
conn = sqlite3.connect(DB_NAME)
rev_data = pd.read_sql_query("SELECT SUM(amount) as total FROM history", conn)
total_rev = rev_data['total'].iloc[0] or 0
st.sidebar.metric("Total Revenue", f"₹{total_rev}")

# --- PAGE 1: LIVE GRID ---
if menu == "Live Grid":
    st.subheader("Real-Time Slot Status")
    
    # Create the grid layout
    cols = st.columns(4)
    for i in range(1, TOTAL_SLOTS + 1):
        col_idx = (i - 1) % 4
        with cols[col_idx]:
            if i in booked_slots:
                vehicle = booked_df[booked_df['slot_no'] == i]['vehicle_no'].values[0]
                st.error(f"Slot {i}\n\n{vehicle}")
            else:
                st.success(f"Slot {i}\n\nAVAILABLE")
                if st.button(f"Book Slot {i}", key=f"btn{i}"):
                    st.session_state['booking_slot'] = i

    # Booking Form
    if 'booking_slot' in st.session_state:
        st.divider()
        st.write(f"### Booking Form: Slot {st.session_state['booking_slot']}")
        with st.form("booking_form"):
            owner = st.text_input("Owner Name")
            vehicle = st.text_input("Vehicle Number").upper()
            submit = st.form_submit_button("Confirm Booking")
            
            if submit and owner and vehicle:
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                conn = sqlite3.connect(DB_NAME)
                cur = conn.cursor()
                cur.execute("INSERT INTO bookings VALUES (?, ?, ?, ?)", 
                            (st.session_state['booking_slot'], owner, vehicle, now))
                conn.commit()
                conn.close()
                st.balloons()
                st.success(f"Slot {st.session_state['booking_slot']} booked!")
                del st.session_state['booking_slot']
                st.rerun()

# --- PAGE 2: SEARCH & CHECKOUT ---
elif menu == "Search & Checkout":
    st.subheader("Find Vehicle & Process Payment")
    search_q = st.text_input("Enter Vehicle Number to Search").upper()
    
    if search_q:
        result = booked_df[booked_df['vehicle_no'].str.contains(search_q)]
        if not result.empty:
            st.table(result)
            slot_to_exit = result['slot_no'].values[0]
            
            if st.button(f"Checkout Slot {slot_to_exit}"):
                # Calculate bill
                checkin_str = result['checkin_time'].values[0]
                checkin_dt = datetime.strptime(checkin_str, "%Y-%m-%d %H:%M:%S")
                hours = max(1, (datetime.now() - checkin_dt).seconds // 3600)
                bill = hours * HOURLY_RATE
                
                # Update DB
                conn = sqlite3.connect(DB_NAME)
                cur = conn.cursor()
                cur.execute("DELETE FROM bookings WHERE slot_no = ?", (int(slot_to_exit),))
                cur.execute("INSERT INTO history (slot_no, amount, paid_at) VALUES (?, ?, ?)",
                            (int(slot_to_exit), bill, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                conn.commit()
                conn.close()
                
                st.warning(f"Payment Received: ₹{bill}. Slot {slot_to_exit} is now empty.")
                st.rerun()
        else:
            st.info("No active booking found for this vehicle.")

# --- PAGE 3: REPORTS ---
elif menu == "Revenue Reports":
    st.subheader("Transaction History")
    conn = sqlite3.connect(DB_NAME)
    history_df = pd.read_sql_query("SELECT * FROM history ORDER BY id DESC", conn)
    conn.close()
    st.dataframe(history_df, use_container_width=True)
    
    if st.button("Clear History"):
        conn = sqlite3.connect(DB_NAME)
        conn.execute("DELETE FROM history")
        conn.commit()
        conn.close()
        st.rerun()
