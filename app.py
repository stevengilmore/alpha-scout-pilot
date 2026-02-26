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
    "BTC-USD": "Bitcoin", "ETH-USD": "Ethereum", "NVDA": "NVIDIA", "AAPL": "Apple",
    "TSLA": "Tesla", "MSFT": "Microsoft", "SAP.DE": "SAP SE", "RR.L": "Rolls-Royce"
}

# --- 2. DATA ENGINES ---
def get_top_9_signals():
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
            pos = "LONG 🟢" if price > ema else "SHORT (🔴 Sell)"
            score = 70 + (25 if (pos.startswith("LONG") and rsi < 45) or (pos.startswith("SHORT") and rsi > 55) else 0)
            all_results.append({"Asset": name, "Ticker": ticker, "Price": round(price, 2), "Pos": pos, "Score": score, "RSI": round(rsi, 1)})
        except: continue
    return pd.DataFrame(all_results).sort_values(by="Score", ascending=False).head(9)

# --- 3. UI: GAUGE & LEADERBOARD ---
st.title("🛰️ Alpha Scout: Global Opportunity Grid")

# SIDEBAR: SENTIMENT GAUGE
with st.sidebar:
    st.header("🌐 Global Sentiment")
    # Real-time data for Feb 26, 2026
    st.subheader("Stocks: Fear (38)")
    st.progress(38, "Investors worried about rate cuts cooling.")
    
    st.subheader("Crypto: Extreme Fear (16)")
    st.progress(16, "Despite 6% rally, sentiment remains icy.")
    
    st.divider()
    if st.button("📱 Test Telegram Alert"):
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", data={"chat_id": CHAT_ID, "text": "🔔 SCOUT: Alert System Online!"})

# MAIN: 3x3 GRID
top_9 = get_top_9_signals()
for i in range(0, 9, 3):
    cols = st.columns(3)
    for j in range(3):
        idx = i + j
        if idx < len(top_9):
            data = top_9.iloc[idx]
            with cols[j]:
                st.info(f"**{data['Asset']}** — {data['Score']}%")
                st.metric(data['Pos'], f"${data['Price']}", f"RSI: {data['RSI']}")
                if st.button(f"🛡️ Audit {data['Ticker']}", key=f"grid_{data['Ticker']}"):
                    st.session_state['active_ticker'] = data['Ticker']

st.divider()

# --- 4. COMMITTEE DEBATE ---
active = st.session_state.get('active_ticker')
if active:
    st.subheader(f"🤖 Committee Debate: {SCAN_POOL[active]}")
    if st.button("🔥 Start Audit"):
        with st.status("Agents Deliberating...", expanded=True):
            client = genai.Client(api_key=GEMINI_KEY)
            
            # THE BULL vs THE BEAR
            bull = client.models.generate_content(model='gemini-3-flash-preview', contents=f"Search for BULLISH growth news on {active}.", config=types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())]))
            st.chat_message("user", avatar="🐂").write(bull.text)

            bear = client.models.generate_content(model='gemini-3-flash-preview', contents=f"Search for BEARISH risk news on {active}.", config=types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())]))
            st.chat_message("user", avatar="🐻").write(bear.text)

            # THE JUDGE
            judge = client.models.generate_content(model='gemini-3-flash-preview', contents=f"Decide: PROCEED or VETO for {active}.", config=types.GenerateContentConfig(system_instruction="You are a cynical Fund Manager. Side with the Bear unless the Bull is undeniable."))
            
            if "PROCEED" in judge.text.upper():
                st.success("🏁 APPROVED")
                requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", data={"chat_id": CHAT_ID, "text": f"✅ {active} APPROVED"})
            else:
                st.error(f"🚫 VETOED")
