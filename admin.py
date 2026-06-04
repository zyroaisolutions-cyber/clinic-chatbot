import sqlite3
import pandas as pd
import streamlit as st

DB_PATH = "/Users/AmaanUddin/Desktop/ZYRO AI SOLUTIONS/chatbot for clinics/ai chat bot/appointments.db"
ADMIN_PASSWORD = "clinic123"   # change this to your own password

st.title("Clinic Admin — Appointments Dashboard")

# --- Password gate ---
password = st.text_input("Enter admin password:", type="password")
if password != ADMIN_PASSWORD:
    st.warning("Enter the correct password to view appointments.")
    st.stop()

# --- Load all appointments ---
conn = sqlite3.connect(DB_PATH)
df = pd.read_sql_query("SELECT * FROM appointments ORDER BY date, time", conn)
conn.close()

st.success(f"Total appointments: {len(df)}")
st.dataframe(df, use_container_width=True)

# --- Download as Excel/CSV ---
csv = df.to_csv(index=False).encode("utf-8")
st.download_button(
    label="Download as Excel/CSV",
    data=csv,
    file_name="appointments.csv",
    mime="text/csv"
)

# ---------------------------------------------------------
# BLOCK A WHOLE DAY (doctor on leave)
# ---------------------------------------------------------
st.subheader("Block a whole day (doctor on leave)")
full_date = st.text_input("Date to block (YYYY-MM-DD):", key="fullday")
full_reason = st.text_input("Reason (optional):", key="fullreason")
if st.button("Block whole day"):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT OR REPLACE INTO blocked_dates (date, reason) VALUES (?, ?)", (full_date, full_reason))
    conn.commit()
    conn.close()
    st.success(f"{full_date} is now fully blocked.")

# ---------------------------------------------------------
# BLOCK PART OF A DAY (doctor unavailable some hours)
# ---------------------------------------------------------
st.subheader("Block part of a day (doctor unavailable for some hours)")

SLOTS = [
    "10:00 AM", "10:30 AM", "11:00 AM", "11:30 AM",
    "12:00 PM", "12:30 PM", "01:00 PM", "01:30 PM",
    "02:00 PM", "02:30 PM", "03:00 PM", "03:30 PM",
    "04:00 PM", "04:30 PM", "05:00 PM", "05:30 PM",
    "06:00 PM", "06:30 PM"
]

pb_date = st.text_input("Date (YYYY-MM-DD):", key="partial")
start = st.selectbox("Unavailable FROM:", SLOTS, key="start")
end = st.selectbox("Unavailable UNTIL:", SLOTS, key="end")

if st.button("Block these hours"):
    i_start = SLOTS.index(start)
    i_end = SLOTS.index(end)
    to_block = SLOTS[i_start:i_end + 1]
    conn = sqlite3.connect(DB_PATH)
    for t in to_block:
        conn.execute("INSERT INTO blocked_slots (date, time) VALUES (?, ?)", (pb_date, t))
    conn.commit()
    conn.close()
    st.success(f"Blocked {start} to {end} on {pb_date} ({len(to_block)} slots).")