"""
step9_availability.py
Works out which appointment slots are free for a given date.
Uses only built-in Python (datetime, sqlite3) - no extra libraries.
"""
import sqlite3
import datetime

DB_PATH = "appointments.db"

# All possible 30-minute slots, 10:00 AM to 6:30 PM
ALL_SLOTS = [
    "10:00 AM", "10:30 AM", "11:00 AM", "11:30 AM",
    "12:00 PM", "12:30 PM", "01:00 PM", "01:30 PM",
    "02:00 PM", "02:30 PM", "03:00 PM", "03:30 PM",
    "04:00 PM", "04:30 PM", "05:00 PM", "05:30 PM",
    "06:00 PM", "06:30 PM"
]


def _slot_to_24h(slot, date_str):
    """Turn '02:30 PM' on a date into a datetime, for comparing with 'now'."""
    return datetime.datetime.strptime(f"{date_str} {slot}", "%Y-%m-%d %I:%M %p")


def get_available_slots(date_str):
    """
    Returns (free_slots, info).
    info == "BLOCKED" if the whole day is blocked (clinic closed).
    Otherwise info == "OK" and free_slots is the list of open times.
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Make sure tables exist (so this never crashes on a fresh database)
    c.execute("""CREATE TABLE IF NOT EXISTS appointments (
        ref TEXT, name TEXT, phone TEXT, email TEXT,
        service TEXT, date TEXT, time TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS blocked_dates (date TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS blocked_slots (date TEXT, time TEXT)""")
    conn.commit()

    # 1. Is the whole day blocked?
    c.execute("SELECT date FROM blocked_dates WHERE date = ?", (date_str,))
    if c.fetchone():
        conn.close()
        return [], "BLOCKED"

    # 2. Sunday closed
    try:
        d = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        if d.weekday() == 6:  # 6 = Sunday
            conn.close()
            return [], "BLOCKED"
    except ValueError:
        conn.close()
        return [], "BLOCKED"

    # 3. Slots already booked on this date
    c.execute("SELECT time FROM appointments WHERE date = ?", (date_str,))
    booked = {row[0] for row in c.fetchall()}

    # 4. Slots blocked by the doctor on this date
    c.execute("SELECT time FROM blocked_slots WHERE date = ?", (date_str,))
    blocked = {row[0] for row in c.fetchall()}

    conn.close()

    # 5. Build the free list
    now = datetime.datetime.now()
    free = []
    for slot in ALL_SLOTS:
        if slot in booked or slot in blocked:
            continue
        # If it's today, skip times that have already passed
        if d == datetime.date.today():
            if _slot_to_24h(slot, date_str) <= now:
                continue
        free.append(slot)

    return free, "OK"
