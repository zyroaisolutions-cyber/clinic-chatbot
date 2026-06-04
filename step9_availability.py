import sqlite3
import datetime

DB_PATH = "appointments.db"   # relative path

ALL_SLOTS = [
    "10:00 AM", "10:30 AM", "11:00 AM", "11:30 AM",
    "12:00 PM", "12:30 PM", "01:00 PM", "01:30 PM",
    "02:00 PM", "02:30 PM", "03:00 PM", "03:30 PM",
    "04:00 PM", "04:30 PM", "05:00 PM", "05:30 PM",
    "06:00 PM", "06:30 PM"
]


def _slot_to_time(slot):
    """Turn '02:30 PM' into a comparable time object."""
    return datetime.datetime.strptime(slot, "%I:%M %p").time()


def get_available_slots(date):
    """
    Returns (free_slots, info).
    - If the whole day is blocked: returns ([], "BLOCKED").
    - Otherwise: returns (list_of_free_slots, list_of_booked_slots).
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Whole day blocked (doctor on leave)?
    cursor.execute("SELECT reason FROM blocked_dates WHERE date = ?", (date,))
    if cursor.fetchone():
        conn.close()
        return [], "BLOCKED"

    # 2. Already-booked times
    cursor.execute("SELECT time FROM appointments WHERE date = ?", (date,))
    booked = [row[0] for row in cursor.fetchall()]

    # 3. Doctor-unavailable times (partial-day block)
    cursor.execute("SELECT time FROM blocked_slots WHERE date = ?", (date,))
    blocked_times = [row[0] for row in cursor.fetchall()]

    conn.close()

    # 4. Free = all slots minus booked minus doctor-blocked
    free = [s for s in ALL_SLOTS if s not in booked and s not in blocked_times]

    # 5. Same-day protection: if the date is today, drop times already passed
    today = datetime.date.today().isoformat()
    if date == today:
        now = datetime.datetime.now().time()
        free = [s for s in free if _slot_to_time(s) > now]

    return free, booked


# This part only runs when you run THIS file directly (not when imported)
if __name__ == "__main__":
    test_date = datetime.date.today().isoformat()
    free, info = get_available_slots(test_date)
    print(f"Date: {test_date}")
    print(f"Info (booked list or BLOCKED): {info}")
    print(f"Available slots: {free}")