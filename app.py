import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- CONFIG ---
DB_NAME = "parking_pro.db"
TOTAL_SLOTS = 12
HOURLY_RATE = 20

st.set_page_config(page_title="AI Smart Parking Pro", layout="wide")

# --- FUTURISTIC CSS ---
st.markdown("""
    <style>
    /* Main Background */
    .stApp {
        background: radial-gradient(circle at center, #0d1b2a 0%, #000814 100%);
        color: #e0e1dd;
    }

    /* Glassmorphism Cards */
    div[data-testid="stMetricValue"] {
        background: rgba(255, 255, 255, 0.05);
        padding: 20px;
        border-radius: 15px;
        border: 1px solid rgba(0, 255, 255, 0.2);
        box-shadow: 0 0 15px rgba(0, 255, 255, 0.1);
        color: #00f2ff !important;
    }

    /* Futuristic Buttons */
    .stButton>button {
        background: linear-gradient(45deg, #00f2ff, #0066ff);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 10px 24px;
        font-weight: bold;
        text-transform: uppercase;
        letter-spacing: 1px;
        transition: 0.3s;
        box-shadow: 0 0 10px rgba(0, 242, 255, 0.5);
    }

    .stButton>button:hover {
        box-shadow: 0 0 20px rgba(0, 242, 255, 0.8);
        transform: translateY(-2px);
    }

    /* Slot Cards Color Updates */
    .stAlert {
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }

    /* Occupied Slot (Neon Red) */
    div[data-testid="stNotification"] {
        background: rgba(255, 46, 99, 0.15) !important;
        border: 1px solid #ff2e63 !important;
        color: #ff2e63 !important;
    }

    /* Header Styling */
    h1, h2, h3 {
        font-family: 'Orbitron', sans-serif;
        text-transform: uppercase;
        letter-spacing: 3px;
        background: linear-gradient(to right, #00f2ff, #ffffff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #000814;
        border-right: 1px solid rgba(0, 255, 255, 0.1);
    }
    </style>
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&display=swap" rel="stylesheet">
    """, unsafe_allow_html=True)

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
    st.title("🤖 AI Parking Neural Link")
    c1, c2 = st.columns(2)
    with c1:
        st.info("### 🔐 Admin Authentication")
        u = st.text_input("Admin ID")
        p = st.text_input("Access Code", type="password")
        if st.button("Initialize Admin Session"):
            if run_query("SELECT * FROM admins WHERE username=? AND password=?", (u, p), fetch=True):
                st.session_state.update({"logged_in": True, "role": "admin", "current_user": u})
                st.rerun()
            else: st.error("Access Denied: Invalid Credentials")
    with c2:
        st.success("### 🛰️ Customer Access")
        if st.button("Enter User Matrix"):
            st.session_state.update({"logged_in": True, "role": "user"})
            st.rerun()
    st.stop()

# --- LOGOUT ---
if st.sidebar.button("🔌 Disconnect Session"):
    st.session_state.clear()
    st.rerun()

booked_df = pd.read_sql(f"SELECT * FROM bookings", sqlite3.connect(DB_NAME))
booked_slots = booked_df['slot_no'].tolist()

# ================= USER POV =================
if st.session_state.role == "user":
    user_menu = st.sidebar.radio("Core Tasks", ["Book a Slot", "My Booking Summary"])
    
    if user_menu == "Book a Slot":
        st.title("🛸 System Live Grid")
        cols = st.columns(4)
        for i in range(1, TOTAL_SLOTS + 1):
            with cols[(i-1)%4]:
                if i in booked_slots:
                    d = booked_df[booked_df['slot_no'] == i].iloc[0]
                    st.error(f"SLOT {i}\n\n[ {d['vehicle_no']} ]\nID: {d['owner_name']}")
                    st.button("LOCKED", key=f"occ_u_{i}", disabled=True)
                else:
                    st.success(f"SLOT {i}\n\nOPEN")
                    if st.button(f"Acquire {i}", key=f"ub_{i}"): 
                        st.session_state.booking_slot = i
                        st.rerun()
        
        if st.session_state.booking_slot:
            with st.form("ai_bk"):
                st.write(f"### Initialization: Slot {st.session_state.booking_slot}")
                name = st.text_input("Subject Name")
                vno = st.text_input("Unit Identifier (Vehicle No)").upper()
                if st.form_submit_button("Confirm Data Entry"):
                    if name and vno:
                        run_query("INSERT INTO bookings VALUES (?,?,?,?)", (st.session_state.booking_slot, name, vno, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                        st.session_state.booking_slot = None
                        st.rerun()
                    else: st.warning("Data incomplete.")

    elif user_menu == "My Booking Summary":
        st.title("📑 Data Retrieval")
        search_v = st.text_input("Enter Unit ID").upper()
        if search_v:
            user_res = booked_df[booked_df['vehicle_no'] == search_v]
            if not user_res.empty:
                slot_id = user_res['slot_no'].iloc[0]
                checkin = user_res['checkin_time'].iloc[0]
                entry_dt = datetime.strptime(checkin, "%Y-%m-%d %H:%M:%S")
                hrs = max(1, (datetime.now() - entry_dt).seconds // 3600)
                total_bill = hrs * HOURLY_RATE
                
                st.info(f"### ACTIVE UNIT: {search_v}")
                c1, c2, c3 = st.columns(3)
                c1.metric("Node", f"#{slot_id}")
                c2.metric("Sync Time", checkin.split()[1])
                c3.metric("Credits Due", f"₹{total_bill}")
                
                if st.button("💳 Finalize Credits & Release"):
                    run_query("DELETE FROM bookings WHERE slot_no=?", (int(slot_id),))
                    run_query("INSERT INTO history (slot_no, amount, paid_at) VALUES (?,?,?)", 
                              (int(slot_id), total_bill, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                    st.balloons()
                    st.rerun()
            else: st.error("No active unit found in system.")

# ================= ADMIN POV =================
else:
    st.sidebar.title(f"Operator: {st.session_state.current_user}")
    admin_menu = st.sidebar.radio("Core System", ["Monitor", "Reports", "Manage Admins"])

    if admin_menu == "Monitor":
        st.title("🖥️ Central Control Monitor")
        cols = st.columns(4)
        for i in range(1, TOTAL_SLOTS + 1):
            with cols[(i-1)%4]:
                if i in booked_slots:
                    d = booked_df[booked_df['slot_no']==i].iloc[0]
                    st.error(f"SLOT {i}\n\n{d['vehicle_no']}\n({d['owner_name']})")
                else: st.success(f"SLOT {i}\n\nEMPTY")

    elif admin_menu == "Manage Admins":
        st.title("👥 User Matrix Permissions")
        with st.form("new_ad"):
            nu, np = st.text_input("New Operative Name"), st.text_input("Security Hash", type="password")
            if st.form_submit_button("Grant Access") and nu and np:
                try: 
                    run_query("INSERT INTO admins VALUES (?,?)", (nu, np))
                    st.success("New Operative Added!")
                except: st.error("Alias already exists!")
        st.table(pd.read_sql("SELECT username FROM admins", sqlite3.connect(DB_NAME)))

    elif admin_menu == "Reports":
        st.title("📈 Credit Analysis")
        dfh = pd.read_sql("SELECT * FROM history", sqlite3.connect(DB_NAME))
        st.metric("Total System Revenue", f"₹{dfh['amount'].sum() if not dfh.empty else 0}")
        st.dataframe(dfh, use_container_width=True)
