import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests
from google import genai
from google.genai import types

# --- 1. SETTINGS & SECRETS ---
st.set_page_config(page_title="Alpha Scout Command", page_icon="🛰️", layout="wide")

GEMINI_KEY = st.secrets.get("GEMINI_KEY")
TG_TOKEN = st.secrets.get("TG_TOKEN")
CHAT_ID = st.secrets.get("CHAT_ID")

ASSET_MAP = {
    "BTC-USD": "Bitcoin", "ETH-USD": "Ethereum", "NVDA": "NVIDIA", "AAPL": "Apple",
    "MSFT": "Microsoft", "TSLA": "Tesla", "AZN.L": "AstraZeneca", "SAP.DE": "SAP SE"
}

# --- 2. THE SIGNAL ENGINE ---
def get_signals():
    signals = []
    for ticker, name in ASSET_MAP.items():
        try:
            df = yf.download(ticker, period="2y", interval="1d", progress=False)
            if df.empty or len(df) < 200: continue
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            
            df['EMA_200'] = ta.ema(df['Close'], length=200)
            df['RSI'] = ta.rsi(df['Close'], length=14)
            curr = df.iloc[-1]
            
            # Position Logic
            pos_type = "LONG 🟢" if curr['Close'] > curr['EMA_200'] else "SHORT 🔴"
            
            # Score (Feb 26, 2026 Market Sensitivity)
            score = 70
            if pos_type == "LONG 🟢" and curr['RSI'] < 45: score += 20
            if pos_type == "SHORT 🔴" and curr['RSI'] > 55: score += 20
            
            signals.append({
                "Asset": name, "Ticker": ticker, "Price": round(curr['Close'], 2),
                "Position": pos_type, "Score": score
            })
        except: continue
    return pd.DataFrame(signals).sort_values(by="Score", ascending=False)

# --- 3. UI: TOP SUMMARY ---
st.title("🛰️ Alpha Scout: Top Picks (Feb 26, 2026)")
all_signals = get_signals()

# Highlight Top 3 "Buy Now"
top_cols = st.columns(3)
for i, row in enumerate(all_signals.head(3).to_dict('records')):
    with top_cols[i]:
        st.metric(f"{row['Asset']} ({row['Position']})", f"${row['Price']}", f"Confidence: {row['Score']}%")
        if st.button(f"Analyze {row['Ticker']}", key=f"btn_{row['Ticker']}"):
            st.session_state['selected_ticker'] = row['Ticker']

st.divider()

# --- 4. TELEGRAM DEBUGGER ---
with st.sidebar:
    st.header("🔧 Debugger")
    if st.button("📱 Test Telegram Connection"):
        test_url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        test_res = requests.post(test_url, data={"chat_id": CHAT_ID, "text": "🔔 SCOUT TEST: Connection Successful!"})
        if test_res.status_code == 200: st.success("Message Sent! Check Phone.")
        else: st.error(f"Error {test_res.status_code}: {test_res.text}")

# --- 5. THE AGENT DEBATE (Bull vs. Bear) ---
target = st.session_state.get('selected_ticker', "NVDA")
st.subheader(f"🤖 Agentic Debate: {ASSET_MAP[target]}")

if st.button("🚀 ACTIVATE AGENT COMMITTEE"):
    with st.status("Gathering Committee...", expanded=True) as status:
        client = genai.Client(api_key=GEMINI_KEY)
        
        # AGENT 1: THE BULL
        bull_res = client.models.generate_content(
            model='gemini-3-flash-preview',
            contents=f"Search for BULLISH news on {target}. Why should we BUY this today?",
            config=types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())])
        )
        st.chat_message("user", avatar="🐂").write(bull_res.text)
        
        # AGENT 2: THE BEAR
        bear_res = client.models.generate_content(
            model='gemini-3-flash-preview',
            contents=f"Search for BEARISH news on {target}. Why is this a TRAP or a SHORT?",
            config=types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())])
        )
        st.chat_message("user", avatar="🐻").write(bear_res.text)
        
        # AGENT 3: THE RISK MANAGER (Judge)
        final_verdict = client.models.generate_content(
            model='gemini-3-flash-preview',
            contents=f"Review the Bull and Bear arguments for {target}. Decide: PROCEED or VETO.",
            config=types.GenerateContentConfig(system_instruction="You are the Judge. Be cynical. If they disagree, side with caution.")
        )
        
        if "PROCEED" in final_verdict.text.upper():
            st.success("🏁 VERDICT: PROCEED")
            requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", 
                          data={"chat_id": CHAT_ID, "text": f"✅ APPROVED: {target}\nPosition: {all_signals[all_signals.Ticker==target].Position.values[0]}"})
        else:
            st.error(f"🚫 VERDICT: VETOED - {final_verdict.text[:200]}...")
