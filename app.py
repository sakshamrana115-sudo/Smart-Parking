import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# Database aur basic setup wahi rahega...

# --- BUTTON CLICK HANDLER ---
def handle_booking_click(slot_id):
    st.session_state.booking_slot = slot_id

# --- LIVE GRID PAGE ---
if menu == "Live Grid":
    st.subheader("Real-Time Slot Status")
    
    # Grid Layout
    cols = st.columns(4)
    for i in range(1, TOTAL_SLOTS + 1):
        with cols[(i - 1) % 4]:
            if i in booked_slots:
                # Agar slot booked hai
                vehicle = booked_df[booked_df['slot_no'] == i]['vehicle_no'].values[0]
                st.error(f"Slot {i} \n\n {vehicle}")
            else:
                # Agar slot khali hai
                st.success(f"Slot {i} \n\n AVAILABLE")
                # ON CLICK hum session state update karenge
                st.button(f"Book Slot {i}", key=f"btn_{i}", on_click=handle_booking_click, args=(i,))

    # AGAR koi button dabaya gaya hai, toh ye form niche dikhega
    if 'booking_slot' in st.session_state and st.session_state.booking_slot is not None:
        st.divider()
        st.markdown(f"### 📝 Fill Details for **Slot {st.session_state.booking_slot}**")
        
        with st.form(key='booking_form_actual'):
            owner = st.text_input("Owner Name")
            vehicle = st.text_input("Vehicle Number")
            
            col1, col2 = st.columns([1, 5])
            with col1:
                submit = st.form_submit_button("Confirm")
            with col2:
                if st.form_submit_button("Cancel"):
                    st.session_state.booking_slot = None
                    st.rerun()

            if submit:
                if owner and vehicle:
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    conn = sqlite3.connect(DB_NAME)
                    cur = conn.cursor()
                    cur.execute("INSERT INTO bookings VALUES (?, ?, ?, ?)", 
                                (st.session_state.booking_slot, owner, vehicle.upper(), now))
                    conn.commit()
                    conn.close()
                    
                    # Success message aur cleanup
                    st.success(f"✅ Slot {st.session_state.booking_slot} successfully booked!")
                    st.session_state.booking_slot = None # Slot clear karo
                    st.rerun() # Page refresh karo data dikhane ke liye
                else:
                    st.warning("Please fill all details!")
