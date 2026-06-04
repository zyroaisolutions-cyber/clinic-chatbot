"""
app.py — PATIENT PAGE (professionally styled)
Run with:  streamlit run app.py
All booking/view/cancel/RAG logic is the same — only the look is upgraded.
"""
import sqlite3
import datetime
import random
import streamlit as st
import chromadb
from google import genai
from step9_availability import get_available_slots, ALL_SLOTS

# ---------- SETTINGS ----------
DB_PATH = "appointments.db"
CHROMA_PATH = "clinic_db"
API_KEY = st.secrets["GEMINI_KEY"]   # <-- your Gemini key

CLINIC_NAME = "Smile Dental Clinic"
CLINIC_TAGLINE = "Healthy smiles, happy faces"
CLINIC_SERVICES = ["Consultation", "Teeth Cleaning", "Root Canal", "Braces", "Cosmetic Dentistry"]

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


def match_service(user_text):
    prompt = (
        f"The clinic offers these services: {', '.join(CLINIC_SERVICES)}. "
        f"The patient typed: '{user_text}'. Which ONE service do they most likely mean? "
        "Reply with the exact service name from the list, or 'UNKNOWN' if none match."
    )
    r = gemini.models.generate_content(model="gemini-3.1-flash-lite", contents=prompt)
    return r.text.strip()


def parse_date(user_text):
    today = datetime.date.today().isoformat()
    prompt = (
        f"Today's date is {today}. The patient said this for an appointment date: '{user_text}'. "
        "Convert it to a real calendar date in YYYY-MM-DD format. "
        "The date must be today or in the FUTURE. "
        "If it's in the past or makes no sense, reply 'INVALID'. "
        "Reply with ONLY the date (YYYY-MM-DD) or the word INVALID."
    )
    r = gemini.models.generate_content(model="gemini-3.1-flash-lite", contents=prompt)
    return r.text.strip()


def is_valid_phone(text):
    digits = "".join(ch for ch in text if ch.isdigit())
    return len(digits) >= 10


def make_ref():
    return "SDC-" + str(random.randint(1000, 9999))


def find_appointments(phone):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT ref, name, service, date, time FROM appointments WHERE phone = ? ORDER BY date, time", (phone,))
    rows = c.fetchall()
    conn.close()
    return rows


def cancel_appointment(ref):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM appointments WHERE ref = ?", (ref,))
    conn.commit()
    conn.close()


def save_booking(name, phone, email, service, date, time):
    ref = make_ref()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO appointments (ref, name, phone, email, service, date, time) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (ref, name, phone, email, service, date, time)
    )
    conn.commit()
    conn.close()
    return ref


def detect_intent(message):
    prompt = (
        'Classify the user message into ONE word: BOOK, CANCEL, VIEW, or QUESTION.\n'
        'BOOK = make a new appointment. CANCEL = cancel/reschedule existing. '
        'VIEW = see their existing appointment. QUESTION = information.\n'
        f'Message: "{message}" Answer (one word):'
    )
    r = gemini.models.generate_content(model="gemini-3.1-flash-lite", contents=prompt)
    return r.text.strip().upper()


def answer_question(question):
    q_emb = embed_text(question)
    results = collection.query(query_embeddings=[q_emb], n_results=4)
    context = "\n\n".join(results["documents"][0])
    prompt = (
        "You are a helpful, warm clinic assistant. Answer using ONLY the info below. "
        "If not there, say you don't know.\n"
        f"INFORMATION:\n{context}\nQUESTION:\n{question}"
    )
    r = gemini.models.generate_content(model="gemini-3.1-flash-lite", contents=prompt)
    return r.text


# ==========================================================
#                    PAGE CONFIG + STYLING
# ==========================================================
st.set_page_config(page_title=CLINIC_NAME, page_icon="🦷", layout="centered")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600&family=Nunito+Sans:wght@400;600;700&display=swap');
:root {
    --teal-deep: #0f6e6e;
    --teal: #14a3a3;
    --mint: #e6f7f5;
    --ink: #1b3a3a;
    --soft: #6b8a8a;
}
html, body, [class*="css"] { font-family: 'Nunito Sans', sans-serif; }
.stApp { background: linear-gradient(180deg, #f4fbfa 0%, #ffffff 40%); }
#MainMenu, footer, header {visibility: hidden;}

.clinic-header {
    background: linear-gradient(135deg, var(--teal-deep) 0%, var(--teal) 100%);
    border-radius: 20px; padding: 28px 32px; margin-bottom: 8px;
    box-shadow: 0 10px 30px rgba(15,110,110,0.18);
}
.clinic-header h1 {
    font-family: 'Fraunces', serif; color: #ffffff; font-size: 30px;
    margin: 0; font-weight: 600; letter-spacing: -0.5px;
}
.clinic-header p { color: #d4f0ee; margin: 6px 0 0 0; font-size: 15px; }
.clinic-badge {
    display: inline-block; background: rgba(255,255,255,0.18); color: #fff;
    padding: 4px 12px; border-radius: 999px; font-size: 12px;
    font-weight: 600; margin-top: 12px;
}

/* Chat bubbles - readable text */
.stChatMessage {
    border-radius: 16px !important;
    padding: 12px 16px !important;
    background: #ffffff !important;
    border: 1px solid #d4ede9 !important;
    margin-bottom: 10px !important;
    box-shadow: 0 2px 8px rgba(15,110,110,0.06) !important;
}
.stChatMessage p, .stChatMessage div, .stChatMessage span, .stChatMessage li {
    color: #1b3a3a !important;
    opacity: 1 !important;
}

.stChatInput textarea { border-radius: 14px !important; }
section[data-testid="stSidebar"] { background: var(--mint); }
.side-card {
    background: #ffffff; border-radius: 14px; padding: 16px 18px;
    margin-bottom: 14px; box-shadow: 0 4px 14px rgba(15,110,110,0.08);
}
.side-card h3 {
    font-family: 'Fraunces', serif; color: var(--teal-deep);
    font-size: 16px; margin: 0 0 10px 0;
}
.side-card p { color: var(--ink); font-size: 14px; margin: 5px 0; line-height: 1.5; }
.side-card .label { color: var(--soft); font-size: 12px; }
</style>
""", unsafe_allow_html=True)

st.markdown(f"""
<div class="clinic-header">
    <h1>🦷 {CLINIC_NAME}</h1>
    <p>{CLINIC_TAGLINE}</p>
    <span class="clinic-badge">● Online - AI Assistant ready</span>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown(f"""
    <div class="side-card">
        <h3>About Us</h3>
        <p>General dentistry, cleaning, root canal, braces & cosmetic dentistry.</p>
    </div>
    <div class="side-card">
        <h3>Timings</h3>
        <p><span class="label">Mon-Sat</span><br>10:00 AM - 7:00 PM</p>
        <p><span class="label">Sunday</span><br>Closed</p>
    </div>
    <div class="side-card">
        <h3>Contact</h3>
        <p>Phone: 9193913980<br>NFC, Delhi<br>amaanuddin1990@gmail.com</p>
    </div>
    """, unsafe_allow_html=True)
    st.caption("Type below to chat, book, view or cancel.")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "flow" not in st.session_state:
    st.session_state.flow = None

if not st.session_state.messages:
    st.session_state.messages.append({
        "role": "assistant",
        "content": f"Hi! Welcome to {CLINIC_NAME}. I can answer your questions or help you book, view, or cancel an appointment. How can I help?"
    })

for m in st.session_state.messages:
    avatar = "🦷" if m["role"] == "assistant" else "🙂"
    with st.chat_message(m["role"], avatar=avatar):
        st.write(m["content"])


def bot_say(text):
    st.session_state.messages.append({"role": "assistant", "content": text})
    with st.chat_message("assistant", avatar="🦷"):
        st.write(text)


user_input = st.chat_input("Type your message...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user", avatar="🙂"):
        st.write(user_input)

    f = st.session_state.flow

    if f is None:
        intent = detect_intent(user_input)
        if intent == "BOOK":
            st.session_state.flow = {"type": "book", "step": "name"}
            bot_say("Wonderful! Let's book your appointment. What's your name?")
        elif intent == "VIEW":
            st.session_state.flow = {"type": "view", "step": "phone"}
            bot_say("Sure. What phone number did you book with?")
        elif intent == "CANCEL":
            st.session_state.flow = {"type": "cancel", "step": "phone"}
            bot_say("No problem. What phone number did you book with?")
        else:
            bot_say(answer_question(user_input))

    elif f["type"] == "view":
        rows = find_appointments(user_input)
        if not rows:
            bot_say("I couldn't find any appointments for that number.")
        else:
            lines = [f"- **{r[0]}** - {r[2]} on {r[3]} at {r[4]} (for {r[1]})" for r in rows]
            bot_say("Here are your appointments:\n\n" + "\n".join(lines))
        st.session_state.flow = None

    elif f["type"] == "cancel":
        if f["step"] == "phone":
            rows = find_appointments(user_input)
            if not rows:
                bot_say("I couldn't find any appointments for that number.")
                st.session_state.flow = None
            else:
                f["rows"] = rows
                lines = [f"{i+1}. **{r[0]}** - {r[2]} on {r[3]} at {r[4]}" for i, r in enumerate(rows)]
                bot_say("Which one would you like to cancel? Reply with the number:\n\n" + "\n".join(lines))
                f["step"] = "pick"
        elif f["step"] == "pick":
            try:
                chosen = f["rows"][int(user_input) - 1]
                cancel_appointment(chosen[0])
                bot_say(f"Done - **{chosen[0]}** ({chosen[2]} on {chosen[3]} at {chosen[4]}) is cancelled. "
                        "Just say 'book an appointment' if you'd like a new time.")
                st.session_state.flow = None
            except (ValueError, IndexError):
                bot_say("Please reply with a valid number from the list.")

    elif f["type"] == "book":
        if f["step"] == "name":
            f["name"] = user_input
            f["step"] = "phone"
            bot_say(f"Lovely to meet you, {user_input}! What's your phone number?")
        elif f["step"] == "phone":
            if not is_valid_phone(user_input):
                bot_say("That doesn't look like a valid phone number. Please enter at least 10 digits.")
            else:
                f["phone"] = user_input
                past = find_appointments(user_input)
                if past:
                    last = past[-1]
                    bot_say(
                        f"Welcome back, {last[1]}! 😊 It's lovely to see you again. "
                        f"Last time you visited us for a **{last[2]}** on **{last[3]}**. "
                        f"I hope you've been keeping well since then! Let's get your new appointment sorted."
                    )
                f["step"] = "email"
                bot_say("What's your email? (we'll send your confirmation there)")
        elif f["step"] == "email":
            if "@" not in user_input or "." not in user_input:
                bot_say("That doesn't look like a valid email. Please try again.")
            else:
                f["email"] = user_input
                f["step"] = "service"
                bot_say("Which service would you like?\n\n- Consultation\n- Teeth Cleaning\n- Root Canal\n- Braces\n- Cosmetic Dentistry")
        elif f["step"] == "service":
            matched = match_service(user_input)
            if matched == "UNKNOWN":
                bot_say("Sorry, I didn't recognize that. We offer: Consultation, Teeth Cleaning, "
                        "Root Canal, Braces, Cosmetic Dentistry. Which one?")
            else:
                f["service"] = matched
                f["step"] = "date"
                bot_say(f"Great choice - **{matched}**. Which date works for you? (e.g. tomorrow, next Monday, or 2026-06-20)")
        elif f["step"] == "date":
            parsed = parse_date(user_input)
            if parsed == "INVALID":
                bot_say("I couldn't read that as a future date. Please try again (e.g. tomorrow, 2026-06-20).")
            else:
                free, info = get_available_slots(parsed)
                if info == "BLOCKED":
                    bot_say(f"Sorry, the clinic is closed on {parsed}. Please pick another date.")
                elif not free:
                    bot_say(f"Sorry, no slots left on {parsed}. Please try another date.")
                else:
                    f["date"] = parsed
                    f["free"] = free
                    slot_list = "\n".join([f"{i+1}. {s}" for i, s in enumerate(free)])
                    bot_say(f"**{parsed}** has openings. Pick a time by number:\n\n{slot_list}")
                    f["step"] = "time"
        elif f["step"] == "time":
            try:
                chosen = f["free"][int(user_input) - 1]
                ref = save_booking(f["name"], f["phone"], f["email"], f["service"], f["date"], chosen)
                bot_say(
                    f"**Booked!** Your reference is **{ref}**.\n\n"
                    f"**{f['name']}** - {f['service']}\n\n"
                    f"Date: {f['date']}   Time: {chosen}\n\n"
                    f"A confirmation will be sent to {f['email']}. "
                    f"Keep your reference (**{ref}**) to view or cancel anytime."
                )
                st.session_state.flow = None
            except (ValueError, IndexError):
                bot_say("Please reply with a valid number from the list.")