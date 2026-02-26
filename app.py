import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests
from google import genai
from google.genai import types

# --- 1. SETTINGS ---
st.set_page_config(page_title="Alpha Scout Command", page_icon="🛰️", layout="wide")
GEMINI_KEY = st.secrets.get("GEMINI_KEY")
TG_TOKEN = st.secrets.get("TG_TOKEN")
CHAT_ID = st.secrets.get("CHAT_ID")

SCAN_POOL = {
    "BTC-USD": "Bitcoin", "ETH-USD": "Ethereum", "SOL-USD": "Solana", "XRP-USD": "XRP",
    "NVDA": "NVIDIA", "AAPL": "Apple", "MSFT": "Microsoft", "AMZN": "Amazon",
    "META": "Meta", "TSLA": "Tesla", "SAP.DE": "SAP SE", "ASML": "ASML Holding"
}

# --- 2. THE TOP 12 ENGINE ---
def get_top_12_signals():
    all_results = []
    for ticker, name in SCAN_POOL.items():
        try:
            df = yf.download(ticker, period="2y", interval="1d", progress=False)
            if df.empty or len(df) < 200: continue
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            
            df['EMA_200'] = ta.ema(df['Close'], length=200)
            df['RSI'] = ta.rsi(df['Close'], length=14)
            curr = df.iloc[-1]
            
            price, ema, rsi = float(curr['Close']), float(curr['EMA_200']), float(curr['RSI'])
            pos = "LONG 🟢" if price > ema else "SHORT 🔴"
            
            # Confidence Calculation
            score = 70
            if (pos == "LONG 🟢" and rsi < 45) or (pos == "SHORT 🔴" and rsi > 55):
                score += 25
            
            all_results.append({
                "Asset": name, "Ticker": ticker, "Price": round(price, 2), 
                "Pos": pos, "Score": score, "RSI": round(rsi, 1)
            })
        except: continue
    return pd.DataFrame(all_results).sort_values(by="Score", ascending=False).head(12)

# --- 3. UI: GAUGE & 4x3 GRID ---
st.title("🛰️ Alpha Scout: Top 12 Opportunities")

with st.sidebar:
    st.header("🌐 Global Sentiment (Feb 26)")
    # Today's Divergence: Stocks recovering, Crypto in fear
    st.subheader("Stocks: Fear (38)")
    st.progress(38, "Investors cautious on rate timelines.")
    st.subheader("Crypto: Extreme Fear (16)")
    st.progress(16, "Bullish recovery amid deep skepticism.")
    st.divider()
    if st.button("📱 Test Telegram Alert"):
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", 
                      data={"chat_id": CHAT_ID, "text": "🔔 SCOUT: System Live!"})

# Render 12 Signals in a 4-row x 3-column Grid
top_12 = get_top_12_signals()
for i in range(0, 12, 3):
    cols = st.columns(3)
    for j in range(3):
        idx = i + j
        if idx < len(top_12):
            data = top_12.iloc[idx]
            with cols[j]:
                # Visibility Fix: Highlighting Confidence % in Header
                st.info(f"**{data['Asset']}** — Confidence: **{data['Score']}%**")
                st.metric(data['Pos'], f"${data['Price']}", f"RSI: {data['RSI']}")
                if st.button(f"🛡️ Audit {data['Ticker']}", key=f"grid_{data['Ticker']}"):
                    st.session_state['active_ticker'] = data['Ticker']

st.divider()

# --- 4. MULTI-AGENT COMMITTEE ---
active = st.session_state.get('active_ticker')
if active:
    st.subheader(f"🤖 Committee Debate: {SCAN_POOL[active]}")
    if st.button("🔥 Run Multi-Agent Audit"):
        with st.status("Gathering Perspectives...", expanded=True):
            client = genai.Client(api_key=GEMINI_KEY)
            
            # Bull vs Bear Debate
            bull = client.models.generate_content(model='gemini-3-flash-preview',
                contents=f"You are the BULL Agent. Search news for {active}. Advocate for a position.",
                config=types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())]))
            st.chat_message("user", avatar="🐂").write(bull.text)

            bear = client.models.generate_content(model='gemini-3-flash-preview',
                contents=f"You are the BEAR Agent. Search news for {active}. Warn of the trap.",
                config=types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())]))
            st.chat_message("user", avatar="🐻").write(bear.text)

            # Final Judge Verdict
            judge = client.models.generate_content(model='gemini-3-flash-preview',
                contents=f"Decide for {active}: PROCEED or VETO. Side with Bear if FOMO exists.",
                config=types.GenerateContentConfig(system_instruction="Cynical Risk Manager."))
            
            if "PROCEED" in judge.text.upper():
                st.success("✅ APPROVED: Sending Signal...")
                requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", 
                              data={"chat_id": CHAT_ID, "text": f"✅ {active} APPROVED BY COMMITTEE"})
            else:
                st.error("🚫 VETOED BY RISK MANAGER")
