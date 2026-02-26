import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests
from datetime import datetime
from google import genai  # The NEW unified SDK
from google.genai import types

# --- 1. SETTINGS & SECRETS ---
st.set_page_config(page_title="Alpha Scout Pro", page_icon="🛡️", layout="wide")

# Safe Secret Loading
GEMINI_KEY = st.secrets.get("GEMINI_KEY")
TG_TOKEN = st.secrets.get("TG_TOKEN")
CHAT_ID = st.secrets.get("CHAT_ID")

# Configure AI (Using the 2.0-Flash stable alias to avoid NotFound errors)
if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
    # This is the 'Goldilocks' model for 2026: Fast, Stable, and Search-enabled
    model = genai.GenerativeModel('gemini-2.0-flash')

# --- 2. SIDEBAR CONTROLS ---
with st.sidebar:
    st.title("🛡️ Control Panel")
    ticker = st.selectbox("Select Asset", ["QQQ", "SPY", "BTC-USD", "NVDA", "AAPL"])
    capital = 2500  # Your Starting Capital
    risk_euro = 25  # 1% Risk Rule
    
    st.divider()
    st.subheader("🛠️ Developer Tools")
    test_mode = st.toggle("Enable Test Mode", help="Bypasses technical filters for demo.")
    
    if st.button("📋 List Active Models"):
        try:
            models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            st.write(models)
        except:
            st.error("Check API Key")

# --- 3. DATA ENGINE ---
@st.cache_data(ttl=60)
def get_market_data(symbol):
    df = yf.download(symbol, period="5d", interval="5m", auto_adjust=True)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df['EMA_200'] = ta.ema(df['Close'], length=200)
    df['RSI'] = ta.rsi(df['Close'], length=14)
    df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
    return df

data = get_market_data(ticker)
curr = data.iloc[-1]
price = float(curr['Close'])

# --- 4. PROBABILITY LOGIC ---
trend_ok = price > float(curr['EMA_200'])
rsi_ok = float(curr['RSI']) < 45

prob_score = 0
if trend_ok: prob_score += 60
if rsi_ok: prob_score += 30

# --- 5. DASHBOARD ---
st.title(f"🛡️ Alpha Scout: {ticker}")
col1, col2 = st.columns([2, 1])

with col1:
    st.line_chart(data[['Close', 'EMA_200']])
    m1, m2, m3 = st.columns(3)
    m1.metric("Price", f"${round(price, 2)}")
    m2.metric("RSI", round(curr['RSI'], 1))
    m3.metric("Probability", f"{prob_score}%")

with col2:
    st.subheader("💰 Risk Manager")
    # 1% Risk Rule Math
    stop_loss_dist = (curr['ATR'] * 2)
    pos_size = min(capital, (risk_euro / (stop_loss_dist / price)))
    
    st.write(f"Bankroll: **{capital} €**")
    st.write(f"Risk per Trade: **{risk_euro} €**")
    st.success(f"Suggested Entry: **{round(pos_size, 2)} €**")

# --- 6. THE AGENT SWARM (UNIFIED) ---
st.divider()
st.header("🤖 Autonomous Agent Swarm")

if st.button("🚀 ACTIVATE AGENT SYSTEM", key="swarm_btn"):
    with st.status("Agent Swarm Active...", expanded=True) as status:
        
        # GATE 1: ANALYST
        st.write("🔍 Analyst: Checking Market Confluence...")
        if prob_score >= 90 or test_mode:
            if test_mode: st.info("🧪 Test Mode: Bypassing technical filters.")
            
      # --- GATE 2: STRATEGIST (Gemini 2026 Unified SDK) ---
st.write("🧠 Strategist: Performing News-Grounded Audit...")

# The prompt for your risk audit
persona = f"""
You are a cynical Senior Risk Manager for a {capital}€ fund. 
Our capital is {capital}€. We only risk 1% per trade.
Search news for {ticker}. If there is ANY major macro risk today, respond ONLY with 'VETO' and a blunt reason.
Otherwise, respond with 'PROCEED'.
"""

try:
    # 1. Initialize the modern client (make sure this is inside the button logic)
    client = genai.Client(api_key=st.secrets["GEMINI_KEY"])
    
    # 2. Call the model using the 2026 Tool syntax
    response = client.models.generate_content(
        model='gemini-2.0-flash', # Recommended for Search grounding
        contents=persona,
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
            temperature=1.0 # Recommended setting for grounding
        )
    )

    # 3. Handle the decision
    if "PROCEED" in response.text.upper():
        st.write("🛡️ Risk Audit: **PASSED**")
        # --- (Your Dispatcher/Telegram code goes here) ---
    else:
        st.error(f"❌ VETOED BY AI: {response.text}")
        status.update(label="⚠️ Strategist Blocked Trade", state="error")

except Exception as e:
    st.error(f"AI Error: {e}")
    status.update(label="❌ API Failure", state="error")
            
            try:
                # Use the Search Tool
                response = model.generate_content(persona, tools=[{'google_search': {}}])
                
                if "PROCEED" in response.text.upper():
                    st.write("🛡️ Risk Audit: **PASSED**")
                    
                    # GATE 3: DISPATCHER (Telegram)
                    st.write("📡 Dispatcher: Sending Signal to Telegram...")
                    msg = (f"🎯 **ALPHA SCOUT SIGNAL: {ticker}**\n"
                           f"Entry: ${round(price, 2)}\n"
                           f"Size: {round(pos_size, 2)}€\n"
                           f"AI Audit: PASSED ✅")
                    
                    requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", 
                                  data={"chat_id": CHAT_ID, "text": msg})
                    
                    status.update(label="✅ SUCCESS: Signal Sent!", state="complete")
                else:
                    st.error(f"❌ VETOED BY AI: {response.text}")
                    status.update(label="⚠️ Strategist Blocked Trade", state="error")
            except Exception as e:
                st.error(f"AI Error: {e}")
                status.update(label="❌ API Failure", state="error")
        else:
            st.warning(f"⚖️ Analyst: Probability ({prob_score}%) too low.")
            status.update(label="😴 Monitoring...", state="complete")
