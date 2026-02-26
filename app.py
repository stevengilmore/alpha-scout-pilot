import streamlit as st
import yfinance as yf
import pandas as pd     # <--- THIS IS THE FIX
import pandas_ta as ta
import requests
import google.generativeai as genai

# --- 1. SETTINGS & STYLING ---
st.set_page_config(page_title="Alpha Scout Pro", page_icon="🛡️", layout="wide")

# This pulls from the 'Secrets' menu in Streamlit Cloud
# If testing locally, it will look for these in the sidebar
TG_TOKEN = st.secrets.get("TG_TOKEN") if "TG_TOKEN" in st.secrets else st.sidebar.text_input("Telegram Token", type="password")
CHAT_ID = st.secrets.get("CHAT_ID") if "CHAT_ID" in st.secrets else st.sidebar.text_input("Chat ID")
GEMINI_KEY = st.secrets.get("GEMINI_KEY") if "GEMINI_KEY" in st.secrets else st.sidebar.text_input("Gemini API Key", type="password")

st.title("🛡️ Alpha Scout: Probability Trading Agent")
st.markdown("---")

# --- 2. DATA ENGINE ---
ticker = st.sidebar.selectbox("Select Asset", ["QQQ", "SPY", "BTC-USD", "NVDA", "AAPL"])
capital = st.sidebar.number_input("Trading Capital (€)", value=2500)
profit_target = 20 # Our €20 goal

import pandas as pd
@st.cache_data(ttl=60)
def get_market_data(symbol):
    # We add 'auto_adjust=True' and 'multi_level_download=False' to keep it simple
    df = yf.download(symbol, period="5d", interval="5m", auto_adjust=True, multi_level_download=False)
    
    # This line ensures we don't have a 'Multi-Index' headache
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
        
    # Professional Indicators
    df['EMA_200'] = ta.ema(df['Close'], length=200)
    df['RSI'] = ta.rsi(df['Close'], length=14)
    return df

# --- 3. PROBABILITY CALCULATION ---
# Gate 1: Trend Filter (Are we above the 200 EMA?)
trend_ok = curr['Close'] > curr['EMA_200']
# Gate 2: Momentum Filter (Is RSI dipping/oversold?)
rsi_ok = curr['RSI'] < 40 

prob_score = 0
if trend_ok: prob_score += 60
if rsi_ok: prob_score += 30

# --- 4. WEB DASHBOARD LAYOUT ---
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader(f"📊 {ticker} Live Analysis")
    # Show the Price vs Trend
    st.line_chart(data[['Close', 'EMA_200']])
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Price", f"${round(curr['Close'], 2)}")
    m2.metric("RSI", round(curr['RSI'], 1), delta="Oversold" if rsi_ok else "Neutral")
    m3.metric("Probability", f"{prob_score}%")

with col2:
    st.subheader("🤖 AI Risk Auditor (Gemini)")
    if GEMINI_KEY:
        genai.configure(api_key=GEMINI_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        if st.button("Run Global News Audit"):
            with st.spinner("AI is scanning headlines..."):
                prompt = f"Analyze the last hour of financial news for {ticker}. If there is a major crash risk or interest rate news, say 'VETO'. If it looks like a normal day for a bounce, say 'PROCEED'. Explain in 1 sentence."
                response = model.generate_content(prompt)
                st.info(response.text)
    else:
        st.warning("⚠️ Connect Gemini Key in Sidebar/Secrets to enable AI Audit.")

# --- 5. EXECUTION & TELEGRAM ---
st.markdown("---")
if prob_score >= 90:
    st.success("🎯 HIGH PROBABILITY SIGNAL DETECTED")
    
    # Calculate target based on €20 profit
    move_needed = (profit_target + 1) / capital # +€1 for fee
    target_price = round(curr['Close'] * (1 + move_needed), 2)
    
    st.write(f"**Strategy:** Trend-Aligned Bounce")
    st.write(f"**Trade Republic Goal:** €{profit_target} Profit")
    
    if st.button("🚀 EXECUTE: Send to Telegram"):
        if TG_TOKEN and CHAT_ID:
            msg = (f"🎯 **ALPHA SCOUT SIGNAL: {ticker}**\n"
                   f"Entry: ${round(curr['Close'], 2)}\n"
                   f"Target: ${target_price}\n\n"
                   f"1. Open Trade Republic\n2. Buy €{capital}\n3. Set Limit Sell at ${target_price}")
            url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
            requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
            st.toast("Alert sent to your phone! Check Telegram.")
        else:
            st.error("Missing Telegram Token or Chat ID!")
else:
    st.write("🔎 Agent is scanning for probability confluence (EMA 200 + RSI)...")
