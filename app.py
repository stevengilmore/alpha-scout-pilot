import os
import sys
import streamlit as st
import yfinance as yf
import requests
from google import genai
from google.genai import types

# --- 1. SECRETS FETCHING (Render/Railway/Local) ---
def get_secret(key):
    # Render/Railway inject these as environment variables
    val = os.environ.get(key)
    if val:
        return val
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return None

GEMINI_KEY = get_secret("GEMINI_KEY")
TG_TOKEN = get_secret("TG_TOKEN")
CHAT_ID = get_secret("CHAT_ID")

# Initialize Gemini Client
client = None
if GEMINI_KEY:
    client = genai.Client(api_key=GEMINI_KEY)

# --- 2. CONFIGURATION ---
WATCHLIST = ["INTC", "PYPL", "DIS", "F", "TSLA", "WBD", "T", "PFE", "BABA", "NKE"]
AGENT_PROMPTS = {
    "🐂 Value Hunter": "Focus on turnaround potential. End with 'VOTE: BUY' or 'VOTE: NO'.",
    "📈 Momentum Pro": "Focus on positive breakouts. End with 'VOTE: BUY' or 'VOTE: NO'.",
    "🐻 Cynical Bear": "Hunt for debt traps. End with 'VOTE: BUY' or 'VOTE: NO'."
}

# --- 3. ENGINE FUNCTIONS ---
def get_stock_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        return {
            "Name": info.get('longName', ticker),
            "Price": info.get('currentPrice', 0),
            "Rec": info.get('recommendationKey', 'N/A').upper()
        }
    except Exception:
        return None

def run_committee_scan():
    results = []
    if not client:
        return [{"Ticker": "ERROR", "Votes": "API Key Missing", "Price": 0}]
        
    for ticker in WATCHLIST:
        data = get_stock_data(ticker)
        if not data: continue
        votes = []
        for name, prompt in AGENT_PROMPTS.items():
            config = types.GenerateContentConfig(
                system_instruction=prompt,
                tools=[types.Tool(google_search=types.GoogleSearch())]
            )
            try:
                # Use standard flash for faster demo response
                res = client.models.generate_content(model="gemini-2.0-flash", contents=f"Audit {ticker}: {data}", config=config)
                votes.append(1 if "VOTE: BUY" in res.text.upper() else 0)
            except Exception:
                votes.append(0)
        if sum(votes) >= 2:
            results.append({"Ticker": ticker, "Votes": sum(votes), "Price": data['Price']})
    return sorted(results, key=lambda x: x['Votes'], reverse=True)[:5]

def send_telegram(picks):
    if not picks or not TG_TOKEN: return
    msg = "🎯 **ALPHA SCOUT: WEEKLY PICKS**\n\n" + "\n".join(
        [f"• {p['Ticker']} (${p['Price']}) - {p['Votes']}/3 Votes" for p in picks]
    )
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})

# --- 4. THE UI (This fixes the blank screen) ---
st.set_page_config(page_title="Alpha Scout Pro", page_icon="🛰️")
st.title("🛰️ Alpha Scout Pro")
st.subheader("Multi-Agent Investment Committee")

# Safety Check
if not GEMINI_KEY:
    st.warning("⚠️ GEMINI_KEY is missing. Add it to Render Environment Variables.")

if st.button("🚀 Run Weekly Audit & Push to Telegram"):
    with st.status("Agents are debating..."):
        picks = run_committee_scan()
        if picks:
            send_telegram(picks)
            st.write("### ✅ Committee Picks")
            st.table(picks)
            st.success("Results pushed to Telegram!")
        else:
            st.info("No stocks passed the 2/3 vote today.")

# --- 5. AUTOMATIC TRIGGER (For Render Cron Jobs) ---
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--cron":
        print("Running scheduled audit...")
        p = run_committee_scan()
        send_telegram(p)
