import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from google import genai
from google.genai import types

# --- 1. SETTINGS & SECRETS ---
st.set_page_config(page_title="Alpha Scout: Committee Command", layout="wide")

GEMINI_KEY = st.secrets["GEMINI_KEY"]
TG_TOKEN = st.secrets["TG_TOKEN"]
CHAT_ID = st.secrets["CHAT_ID"]

client = genai.Client(api_key=GEMINI_KEY)

WATCHLIST = ["INTC", "PYPL", "DIS", "F", "TSLA", "WBD", "T", "PFE", "BABA", "NKE"]

AGENT_PROMPTS = {
    "🐂 Value Hunter": "Focus on 5-year lows and turnaround potential. End with 'VOTE: BUY' or 'VOTE: NO'.",
    "📈 Momentum Pro": "Focus on positive news catalysts and analyst upgrades. End with 'VOTE: BUY' or 'VOTE: NO'.",
    "🐻 Cynical Bear": "Focus on debt, value traps, and reasons to VETO. End with 'VOTE: BUY' or 'VOTE: NO'."
}

# --- 2. ENGINE FUNCTIONS ---
def get_investor_data(ticker):
    stock = yf.Ticker(ticker)
    info = stock.info
    return {
        "Name": info.get('longName', ticker),
        "Analyst_Count": info.get('numberOfAnalystOpinions', 'N/A'),
        "Rec": info.get('recommendationKey', 'N/A').upper(),
        "Price": info.get('currentPrice', 0)
    }

def run_committee_scan():
    results = []
    for ticker in WATCHLIST:
        data = get_investor_data(ticker)
        votes = []
        for name, prompt in AGENT_PROMPTS.items():
            # Using Gemini 2.5 Flash for reasoning + search
            config = types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(include_thoughts=True),
                tools=[types.Tool(google_search=types.GoogleSearch())],
                system_instruction=prompt
            )
            res = client.models.generate_content(model="gemini-2.5-flash", contents=f"Audit {ticker}: {data}", config=config)
            votes.append(1 if "VOTE: BUY" in res.text.upper() else 0)
        
        if sum(votes) >= 2:
            results.append({"Ticker": ticker, "Votes": sum(votes), "Price": data['Price']})
    
    return sorted(results, key=lambda x: x['Votes'], reverse=True)[:5]

# --- 3. UI & MANUAL TESTING ---
st.title("🛰️ Alpha Scout: Weekly Committee")

with st.sidebar:
    st.header("🔧 System Test")
    if st.button("📱 FORCE TEST DISPATCH"):
        with st.status("Running real-time test audit..."):
            test_picks = run_committee_scan()
            msg = "🔔 **ALPHA SCOUT: TEST ALERT**\n\n" + "\n".join([f"• {p['Ticker']} (${p['Price']}) - {p['Votes']}/3 Votes" for p in test_picks])
            requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", data={"chat_id": CHAT_ID, "text": msg})
        st.success("Test sent to your phone!")

# Main Dashboard View
if st.button("🚀 MANUAL WEEKLY RUN"):
    final_picks = run_committee_scan()
    st.write(final_picks)
