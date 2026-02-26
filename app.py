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

# Expanded Watchlist (Feb 2026 Focus)
ASSET_MAP = {
    "BTC-USD": "Bitcoin", "ETH-USD": "Ethereum", "SOL-USD": "Solana",
    "NVDA": "NVIDIA", "AAPL": "Apple", "TSLA": "Tesla", "MSFT": "Microsoft",
    "SAP.DE": "SAP SE", "AZN.L": "AstraZeneca"
}

# --- 2. THE SIGNAL ENGINE ---
def get_all_signals():
    results = []
    for ticker, name in ASSET_MAP.items():
        try:
            df = yf.download(ticker, period="2y", interval="1d", progress=False)
            if df.empty or len(df) < 200: continue
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            
            df['EMA_200'] = ta.ema(df['Close'], length=200)
            df['RSI'] = ta.rsi(df['Close'], length=14)
            curr = df.iloc[-1]
            
            # Position Logic
            pos = "LONG 🟢" if curr['Close'] > curr['EMA_200'] else "SHORT 🔴"
            score = 70 + (20 if (pos == "LONG 🟢" and curr['RSI'] < 45) or (pos == "SHORT 🔴" and curr['RSI'] > 55) else 0)
            
            results.append({"Asset": name, "Ticker": ticker, "Price": round(curr['Close'], 2), "Pos": pos, "Score": score})
        except: continue
    return pd.DataFrame(results).sort_values(by="Score", ascending=False)

# --- 3. UI: THE 3x3 GRID ---
st.title("🛰️ Alpha Scout: Strategic Opportunity Grid")
signals_df = get_all_signals()

# Create 3 rows of 3 columns for 9 choices
for row_idx in range(0, 9, 3):
    cols = st.columns(3)
    for col_idx in range(3):
        idx = row_idx + col_idx
        if idx < len(signals_df):
            data = signals_df.iloc[idx]
            with cols[col_idx]:
                st.info(f"**{data['Asset']}** ({data['Ticker']})")
                st.metric(data['Pos'], f"${data['Price']}", f"Score: {data['Score']}%")
                if st.button(f"🔍 Audit {data['Ticker']}", key=f"grid_{data['Ticker']}"):
                    st.session_state['active_ticker'] = data['Ticker']

st.divider()

# --- 4. THE AGENT COMMITTEE ---
active = st.session_state.get('active_ticker')
if active:
    st.subheader(f"🤖 Committee Debate: {ASSET_MAP[active]}")
    if st.button("🔥 START DEBATE"):
        with st.status("Agents Deliberating...", expanded=True) as status:
            client = genai.Client(api_key=GEMINI_KEY)
            
            # 🐂 THE BULL (Optimization: One prompt to save time)
            bull = client.models.generate_content(model='gemini-3-flash-preview',
                contents=f"You are the BULL Agent. Search for news on {active}. Why is this a strong trade?",
                config=types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())]))
            st.chat_message("user", avatar="🐂").write(bull.text)

            # 🐻 THE BEAR
            bear = client.models.generate_content(model='gemini-3-flash-preview',
                contents=f"You are the BEAR Agent. Search for news on {active}. Why is this a dangerous trap?",
                config=types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())]))
            st.chat_message("user", avatar="🐻").write(bear.text)

            # 🛡️ THE RISK MANAGER (JUDGE)
            judge = client.models.generate_content(model='gemini-3-flash-preview',
                contents=f"Review the Bull and Bear for {active}. Decide: PROCEED or VETO. If you PROCEED, send a Telegram alert.",
                config=types.GenerateContentConfig(system_instruction="You are the cynical Judge. Kill the trade unless both technicals and news are perfect."))
            
            if "PROCEED" in judge.text.upper():
                st.success("✅ APPROVED")
                requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", 
                              data={"chat_id": CHAT_ID, "text": f"✅ {active} APPROVED BY COMMITTEE"})
            else:
                st.error(f"🚫 VETOED: {judge.text[:250]}...")

# --- 5. TELEGRAM DEBUGGER ---
with st.sidebar:
    st.header("🔧 Debugger")
    if st.button("📱 Force Telegram Test"):
        res = requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", data={"chat_id": CHAT_ID, "text": "🔔 SCOUT: Connection OK!"})
        st.write(f"Status: {res.status_code}")
