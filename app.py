"""
app.py — Smile Dental Clinic Assistant (all-ages friendly)
- Type OR tap buttons (easy for everyone)
- Clean time-slot grid: available = tappable, booked = greyed out
- Thank-you + "Book another / Start over" after booking
- "Send on WhatsApp" button for confirmation
- Bigger fonts, safe medical Q&A
Gemini embeddings, deploy-ready.
"""
import sqlite3
import datetime
import random
import urllib.parse
import streamlit as st
import chromadb
from google import genai
from step9_availability import get_available_slots, ALL_SLOTS

# ---------- SETTINGS ----------
DB_PATH = "appointments.db"
CHROMA_PATH = "clinic_db"
API_KEY = st.secrets["GEMINI_KEY"]

CLINIC_NAME = "Smile Dental Clinic"
CLINIC_TAGLINE = "Healthy smiles, happy faces"
CLINIC_PHONE = "9193913980"
CLINIC_SERVICES = ["Consultation", "Teeth Cleaning", "Root Canal", "Braces", "Cosmetic Dentistry"]


# ---------- DATABASE SETUP ----------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS appointments (
        ref TEXT, name TEXT, phone TEXT, email TEXT,
        service TEXT, date TEXT, time TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS blocked_dates (date TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS blocked_slots (date TEXT, time TEXT)""")
    conn.commit()
    conn.close()

init_db()


# ---------- LOAD ONCE ----------
@st.cache_resource
def load_stuff():
    chroma = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = chroma.get_collection("clinic")
    gemini = genai.Client(api_key=API_KEY)
    return collection, gemini

collection, gemini = load_stuff()


def embed_text(text):
    result = gemini.models.embed_content(model="gemini-embedding-001", contents=text)
    return result.embeddings[0].values


# ---------- HELPERS ----------
def parse_date(user_text):
    today = datetime.date.today().isoformat()
    prompt = (
        f"Today's date is {today}. The patient said this for an appointment date: '{user_text}'. "
        "Convert it to a real calendar date in YYYY-MM-DD format. The date must be today or FUTURE. "
        "If past or nonsense, reply 'INVALID'. Reply ONLY the date (YYYY-MM-DD) or INVALID."
    )
    r = gemini.models.generate_content(model="gemini-3.1-flash-lite", contents=prompt)
    return r.text.strip()


def is_valid_phone(text):
    return len("".join(ch for ch in text if ch.isdigit())) >= 10


def make_ref():
    return "SDC-" + str(random.randint(1000, 9999))


def find_appointments(phone):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT ref, name, service, date, time FROM appointments WHERE phone = ? ORDER BY date, time", (phone,))
    rows = c.fetchall(); conn.close(); return rows


def booked_times(date_str):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT time FROM appointments WHERE date = ?", (date_str,))
    rows = {r[0] for r in c.fetchall()}; conn.close(); return rows


def cancel_appointment(ref):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("DELETE FROM appointments WHERE ref = ?", (ref,)); conn.commit(); conn.close()


def save_booking(name, phone, email, service, date, time):
    ref = make_ref()
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("INSERT INTO appointments (ref, name, phone, email, service, date, time) VALUES (?, ?, ?, ?, ?, ?, ?)",
              (ref, name, phone, email, service, date, time))
    conn.commit(); conn.close(); return ref


def detect_intent(message):
    prompt = (
        'Classify into ONE word: BOOK, CANCEL, VIEW, or QUESTION.\n'
        'BOOK=new appointment. CANCEL=cancel existing. VIEW=see existing. QUESTION=info or health question.\n'
        f'Message: "{message}" Answer (one word):'
    )
    r = gemini.models.generate_content(model="gemini-3.1-flash-lite", contents=prompt)
    return r.text.strip().upper()


def answer_question(question):
    q_emb = embed_text(question)
    results = collection.query(query_embeddings=[q_emb], n_results=4)
    context = "\n\n".join(results["documents"][0])
    prompt = (
        "You are a warm, caring assistant for Smile Dental Clinic. Use the clinic info below to answer "
        "about timings, services, prices, location. For general dental health questions (tooth pain, bleeding "
        "gums, sensitivity) you may give SAFE general comfort advice (e.g. warm saltwater rinse), but NEVER "
        "diagnose or prescribe medicine. ALWAYS gently recommend seeing Dr. Amaanuddin and mention booking or "
        f"calling {CLINIC_PHONE}. Keep answers short, kind, easy for all ages.\n\n"
        f"CLINIC INFO:\n{context}\n\nQUESTION:\n{question}"
    )
    r = gemini.models.generate_content(model="gemini-3.1-flash-lite", contents=prompt)
    return r.text


def whatsapp_link(phone, message):
    digits = "".join(ch for ch in phone if ch.isdigit())
    if len(digits) == 10:
        digits = "91" + digits   # India country code
    return f"https://wa.me/{digits}?text={urllib.parse.quote(message)}"


# ==========================================================
#                  PAGE CONFIG + STYLING
# ==========================================================
st.set_page_config(page_title=CLINIC_NAME, page_icon="\U0001F9B7", layout="centered")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600&family=Nunito+Sans:wght@400;600;700&display=swap');
:root { --teal-deep:#0f6e6e; --teal:#14a3a3; --mint:#e6f7f5; --ink:#1b3a3a; --soft:#6b8a8a; }
html, body, [class*="css"] { font-family:'Nunito Sans',sans-serif; }
.stApp { background: linear-gradient(180deg,#f4fbfa 0%,#ffffff 40%); }
#MainMenu, footer, header {visibility:hidden;}
.clinic-header { background:linear-gradient(135deg,var(--teal-deep) 0%,var(--teal) 100%);
  border-radius:20px; padding:30px 34px; margin-bottom:8px; box-shadow:0 10px 30px rgba(15,110,110,0.18); }
.clinic-header h1 { font-family:'Fraunces',serif; color:#fff; font-size:34px; margin:0; font-weight:600; }
.clinic-header p { color:#d4f0ee; margin:8px 0 0 0; font-size:18px; }
.clinic-badge { display:inline-block; background:rgba(255,255,255,0.18); color:#fff;
  padding:6px 16px; border-radius:999px; font-size:14px; font-weight:600; margin-top:12px; }
.stChatMessage { border-radius:16px !important; padding:16px 20px !important; background:#ffffff !important;
  border:1px solid #d4ede9 !important; margin-bottom:10px !important; box-shadow:0 2px 8px rgba(15,110,110,0.06) !important; }
.stChatMessage p, .stChatMessage div, .stChatMessage span, .stChatMessage li {
  color:#1b3a3a !important; opacity:1 !important; font-size:18px !important; line-height:1.65 !important; }
.stChatInput textarea { border-radius:14px !important; font-size:18px !important; }
.stButton button { background:var(--teal) !important; color:#fff !important; border:none !important;
  border-radius:12px !important; padding:14px 16px !important; font-size:17px !important; font-weight:600 !important;
  width:100% !important; margin:5px 0 !important; box-shadow:0 3px 10px rgba(20,163,163,0.25) !important; }
.stButton button:hover { background:var(--teal-deep) !important; }
.stButton button:disabled { background:#e3eeec !important; color:#9bb5b2 !important; box-shadow:none !important; }
section[data-testid="stSidebar"] { background:var(--mint); }
.side-card { background:#fff; border-radius:14px; padding:16px 18px; margin-bottom:14px; box-shadow:0 4px 14px rgba(15,110,110,0.08); }
.side-card h3 { font-family:'Fraunces',serif; color:var(--teal-deep); font-size:18px; margin:0 0 10px 0; }
.side-card p { color:var(--ink); font-size:16px; margin:5px 0; line-height:1.5; }
.side-card .label { color:var(--soft); font-size:14px; }
.booked-box { background:linear-gradient(135deg,#0f6e6e,#14a3a3); color:#fff; border-radius:16px;
  padding:22px 26px; margin:8px 0; box-shadow:0 8px 24px rgba(15,110,110,0.22); }
.booked-box h2 { margin:0 0 10px 0; font-size:24px; font-family:'Fraunces',serif; }
.booked-box p { color:#eafaf8 !important; font-size:17px !important; margin:5px 0; }
.slot-legend { font-size:15px; color:var(--soft); margin:4px 0 10px 0; }
.wa-btn a { display:inline-block; background:#25D366; color:#fff !important; text-decoration:none;
  padding:14px 20px; border-radius:12px; font-size:17px; font-weight:700; margin:6px 0;
  box-shadow:0 3px 10px rgba(37,211,102,0.35); }
</style>
""", unsafe_allow_html=True)

st.markdown(f"""
<div class="clinic-header">
    <h1>\U0001F9B7 {CLINIC_NAME}</h1>
    <p>{CLINIC_TAGLINE}</p>
    <span class="clinic-badge">\u25CF Online - AI Assistant ready</span>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown(f"""
    <div class="side-card"><h3>About Us</h3>
        <p>General dentistry, cleaning, root canal, braces & cosmetic dentistry.</p></div>
    <div class="side-card"><h3>Timings</h3>
        <p><span class="label">Mon-Sat</span><br>10:00 AM - 7:00 PM</p>
        <p><span class="label">Sunday</span><br>Closed</p></div>
    <div class="side-card"><h3>Contact</h3>
        <p>Phone: {CLINIC_PHONE}<br>NFC, Delhi<br>amaanuddin1990@gmail.com</p></div>
    """, unsafe_allow_html=True)
    st.caption("Type below, or tap the buttons. Easy for everyone!")

# ---------- SESSION STATE ----------
if "messages" not in st.session_state:
    st.session_state.messages = []
if "flow" not in st.session_state:
    st.session_state.flow = None
if "pending" not in st.session_state:
    st.session_state.pending = None

if not st.session_state.messages:
    st.session_state.messages.append({
        "role": "assistant",
        "content": f"Hi! Welcome to {CLINIC_NAME}. \U0001F44B You can **type** or **tap the buttons** below. "
                   "I can answer questions or help you book, view, or cancel an appointment. How can I help?"
    })


def bot_say(text):
    st.session_state.messages.append({"role": "assistant", "content": text})


def handle_input(user_input):
    f = st.session_state.flow
    if f is None:
        with st.spinner("\U0001F4AD Thinking..."):
            intent = detect_intent(user_input)
        if intent == "BOOK":
            st.session_state.flow = {"type": "book", "step": "name"}
            bot_say("Wonderful! Let's book your appointment. \U0001F60A What's your name?")
        elif intent == "VIEW":
            st.session_state.flow = {"type": "view", "step": "phone"}
            bot_say("Sure! What phone number did you book with?")
        elif intent == "CANCEL":
            st.session_state.flow = {"type": "cancel", "step": "phone"}
            bot_say("No problem. What phone number did you book with?")
        else:
            with st.spinner("\U0001F4AD Thinking..."):
                bot_say(answer_question(user_input))

    elif f["type"] == "view":
        rows = find_appointments(user_input)
        if not rows:
            bot_say("I couldn't find any appointments for that number. Would you like to book one?")
        else:
            lines = [f"- **{r[0]}** - {r[2]} on {r[3]} at {r[4]} (for {r[1]})" for r in rows]
            bot_say("Here are your appointments:\n\n" + "\n".join(lines) + "\n\nAnything else I can help with?")
        st.session_state.flow = None

    elif f["type"] == "cancel":
        if f["step"] == "phone":
            rows = find_appointments(user_input)
            if not rows:
                bot_say("I couldn't find any appointments for that number."); st.session_state.flow = None
            else:
                f["rows"] = rows
                lines = [f"{i+1}. **{r[0]}** - {r[2]} on {r[3]} at {r[4]}" for i, r in enumerate(rows)]
                bot_say("Which one to cancel? Reply with the number:\n\n" + "\n".join(lines)); f["step"] = "pick"
        elif f["step"] == "pick":
            try:
                chosen = f["rows"][int(user_input) - 1]
                cancel_appointment(chosen[0])
                bot_say(f"\u2705 Done - **{chosen[0]}** ({chosen[2]} on {chosen[3]} at {chosen[4]}) is cancelled. "
                        "Anything else?"); st.session_state.flow = None
            except (ValueError, IndexError):
                bot_say("Please reply with a valid number from the list.")

    elif f["type"] == "book":
        if f["step"] == "name":
            f["name"] = user_input; f["step"] = "phone"
            bot_say(f"Lovely to meet you, {user_input}! \U0001F642 What's your phone number?")
        elif f["step"] == "phone":
            if not is_valid_phone(user_input):
                bot_say("That doesn't look like a valid phone number. Please enter at least 10 digits.")
            else:
                f["phone"] = user_input
                past = find_appointments(user_input)
                if past:
                    last = past[-1]
                    bot_say(f"Welcome back, {last[1]}! \U0001F60A Lovely to see you again. "
                            f"Last time you visited for a **{last[2]}** on **{last[3]}**.")
                f["step"] = "email"
                bot_say("What's your email? (we'll send your confirmation there)")
        elif f["step"] == "email":
            if "@" not in user_input or "." not in user_input:
                bot_say("That doesn't look like a valid email. Please try again.")
            else:
                f["email"] = user_input; f["step"] = "service"
                bot_say("Great! Please **tap the service** you'd like (or type it) \U0001F447")
        elif f["step"] == "date":
            with st.spinner("\U0001F4AD Checking the calendar..."):
                parsed = parse_date(user_input)
            if parsed == "INVALID":
                bot_say("I couldn't read that date. Please tap **Tomorrow**, or type like 2026-06-20.")
            else:
                free, info = get_available_slots(parsed)
                if info == "BLOCKED":
                    bot_say(f"Sorry, the clinic is closed on {parsed}. Please pick another date.")
                elif not free:
                    bot_say(f"Sorry, no slots left on {parsed}. Please try another date.")
                else:
                    f["date"] = parsed; f["free"] = free; f["step"] = "time"
                    bot_say(f"**{parsed}** - please **tap an available time** below \U0001F447")


# ---------- SHOW CHAT HISTORY ----------
for m in st.session_state.messages:
    avatar = "\U0001F9B7" if m["role"] == "assistant" else "\U0001F642"
    with st.chat_message(m["role"], avatar=avatar):
        if m["role"] == "assistant" and m["content"].startswith("BOOKED_BOX|||"):
            _, ref, name, service, date, time, email, phone = m["content"].split("|||")
            st.markdown(f"""
            <div class="booked-box">
                <h2>\u2705 Appointment Booked!</h2>
                <p><b>Reference:</b> {ref}</p>
                <p><b>Name:</b> {name}</p>
                <p><b>Service:</b> {service}</p>
                <p><b>Date:</b> {date} &nbsp; <b>Time:</b> {time}</p>
            </div>
            """, unsafe_allow_html=True)
            wa_msg = (f"Hi {name}! Your appointment at {CLINIC_NAME} is confirmed.\n"
                      f"Reference: {ref}\nService: {service}\nDate: {date}\nTime: {time}\n"
                      f"See you then! - {CLINIC_NAME}, {CLINIC_PHONE}")
            st.markdown(f'<div class="wa-btn"><a href="{whatsapp_link(phone, wa_msg)}" target="_blank">'
                        f'\U0001F4F2 Send confirmation to WhatsApp</a></div>', unsafe_allow_html=True)
            st.write(f"Thank you, **{name}**! \U0001F64F Keep your reference **{ref}** to view or cancel anytime. "
                     "Tap below if you'd like to book another or start over.")
        else:
            st.write(m["content"])


# ---------- TAP BUTTONS ----------
f = st.session_state.flow

def choose(value):
    st.session_state.pending = value

if f and f.get("type") == "book":
    if f.get("step") == "service":
        cols = st.columns(2)
        for i, svc in enumerate(CLINIC_SERVICES):
            with cols[i % 2]:
                st.button(svc, key=f"svc_{svc}", on_click=choose, args=(svc,))
    elif f.get("step") == "date":
        c1, c2 = st.columns(2)
        day_after = (datetime.date.today() + datetime.timedelta(days=2)).isoformat()
        with c1: st.button("Tomorrow", key="d_tom", on_click=choose, args=("tomorrow",))
        with c2: st.button("Day after tomorrow", key="d_da", on_click=choose, args=(day_after,))
    elif f.get("step") == "time" and f.get("free"):
        st.markdown('<p class="slot-legend">\U0001F7E2 Green = available to book &nbsp;·&nbsp; '
                    'Grey = already booked</p>', unsafe_allow_html=True)
        taken = booked_times(f["date"])
        cols = st.columns(3)
        for i, slot in enumerate(ALL_SLOTS):
            with cols[i % 3]:
                if slot in f["free"]:
                    st.button(slot, key=f"t_{slot}", on_click=choose, args=(slot,))
                else:
                    st.button(slot, key=f"t_{slot}", disabled=True)

# Restart buttons (shown when no active flow, after first message)
if f is None and len(st.session_state.messages) > 1:
    c1, c2 = st.columns(2)
    with c1: st.button("\U0001F4C5 Book an appointment", key="restart_book", on_click=choose, args=("book an appointment",))
    with c2: st.button("\U0001F504 Start over", key="restart_clear", on_click=choose, args=("__CLEAR__",))


# ---------- HANDLE A BUTTON TAP ----------
if st.session_state.pending is not None:
    choice = st.session_state.pending
    st.session_state.pending = None
    f = st.session_state.flow

    if choice == "__CLEAR__":
        st.session_state.messages = []
        st.session_state.flow = None
        st.rerun()

    st.session_state.messages.append({"role": "user", "content": choice})

    if f and f["type"] == "book" and f["step"] == "service":
        f["service"] = choice; f["step"] = "date"
        bot_say(f"Great choice - **{choice}**! \U0001F44D Now please **tap a date** below \U0001F447")
        st.rerun()
    elif f and f["type"] == "book" and f["step"] == "time":
        ref = save_booking(f["name"], f["phone"], f["email"], f["service"], f["date"], choice)
        st.session_state.messages.append({
            "role": "assistant",
            "content": f"BOOKED_BOX|||{ref}|||{f['name']}|||{f['service']}|||{f['date']}|||{choice}|||{f['email']}|||{f['phone']}"
        })
        st.session_state.flow = None
        st.rerun()
    else:
        handle_input(choice)
        st.rerun()


# ---------- HANDLE TYPED INPUT ----------
typed = st.chat_input("Type your message...")
if typed:
    st.session_state.messages.append({"role": "user", "content": typed})
    handle_input(typed)
    st.rerun()
                bot_say("Please reply with a valid number from the list.")
