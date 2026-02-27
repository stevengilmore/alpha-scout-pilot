import os
import streamlit as st
import yfinance as yf
import requests
from google import genai
from google.genai import types

# --- 1. PORTABLE SECRETS CONFIG ---
def get_secret(key):
    if key in st.secrets:
        return st.secrets[key]
    return os.environ.get(key)

GEMINI_KEY = get_secret("GEMINI_KEY")
TG_TOKEN = get_secret("TG_TOKEN")
CHAT_ID = get_secret("CHAT_ID")

# Initialize Gemini Client
client = genai.Client(api_key=GEMINI_KEY)

# --- 2. MULTI-AGENT PERSONAS ---
AGENT_PROMPTS = {
    "🐂 Value Hunter": "Find turnaround stocks at 5Y lows. End with 'VOTE: BUY' or 'VOTE: NO'.",
    "📈 Momentum Pro": "Find stocks with positive news and breakouts. End with 'VOTE: BUY' or 'VOTE: NO'.",
    "🐻 Cynical Bear": "Hunt for value traps and reasons to VETO. End with 'VOTE: BUY' or 'VOTE: NO'."
}

WATCHLIST = ["INTC", "PYPL", "DIS", "F", "TSLA", "WBD", "T", "PFE", "BABA", "NKE"]

# --- 3. ENGINE FUNCTIONS ---
def get_stock_data(ticker):
    """Fetches real-time investor analysis"""
    stock = yf.Ticker(ticker)
    info = stock.info
    return {
        "Name": info.get('longName', ticker),
        "Analyst_Count": info.get('numberOfAnalystOpinions', 'N/A'),
        "Rec": info.get('recommendationKey', 'N/A').upper(),
        "Price": info.get('currentPrice', 0)
    }

def run_committee():
    """Runs the 3-agent 2:1 consensus logic"""
    results = []
    for ticker in WATCHLIST:
        data = get_stock_data(ticker)
        votes = []
        for name, prompt in AGENT_PROMPTS.items():
            config = types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(include_thoughts=True),
                tools=[types.Tool(google_search=types.GoogleSearch())],
                system_instruction=prompt
            )
            res = client.models.generate_content(model="gemini-2.5-flash", 
                                                 contents=f"Audit {ticker}: {data}", config=config)
            votes.append(1 if "VOTE: BUY" in res.text.upper() else 0)
        
        if sum(votes) >= 2:
            results.append({"Ticker": ticker, "Votes": sum(votes), "Price": data['Price']})
    return sorted(results, key=lambda x: x['Votes'], reverse=True)[:5]

def send_telegram(picks):
    """Dispatches results to Telegram"""
    if not picks: return
    msg = "🎯 **WEEKLY TOP 5 SIGNS**\n\n" + "\n".join([f"• {p['Ticker']} (${p['Price']}) - {p['Votes']}/3 Votes" for p in picks])
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})

# --- 4. DASHBOARD UI ---
st.set_page_config(page_title="Alpha Scout Pro", layout="wide")
st.title("🛰️ Alpha Scout: Multi-Agent Committee")

if st.button("🚀 RUN WEEKLY AUDIT & PUSH"):
    with st.status("Committee is debating..."):
        top_picks = run_committee()
        send_telegram(top_picks)
        st.write(top_picks)
    st.success("Analysis complete and pushed to Telegram!")
