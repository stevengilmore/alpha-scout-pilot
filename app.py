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

GEMINI_KEY = st.secrets.get("GEMINI_KEY")
TG_TOKEN = st.secrets.get("TG_TOKEN")
CHAT_ID = st.secrets.get("CHAT_ID")

# --- 2. SIDEBAR CONTROLS ---
with st.sidebar:
    st.title("🛡️ Control Panel")
    ticker = st.selectbox("Select Asset", ["QQQ", "SPY", "BTC-USD", "NVDA", "AAPL"])
    capital = 2500  
    risk_euro = 25  
    
    st.divider()
    st.subheader("🛠️ Developer Tools")
    test_mode = st.toggle("Enable Test Mode", help="Bypasses technical filters for demo.")

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
    stop_loss_dist = (curr['ATR'] * 2)
    if stop_loss_dist > 0:
        pos_size = min(capital, (risk_euro / (stop_loss_dist / price)))
    else:
        pos_size = 0
    
    st.write(f"Bankroll: **{capital} €**")
    st.write(f"Risk per Trade: **{risk_euro} €**")
    st.success(f"Suggested Entry: **{round(pos_size, 2)} €**")

# --- 6. THE AGENT SWARM (UNIFIED) ---
st.divider()
st.header("🤖 Autonomous Agent Swarm")

if st.button("🚀 ACTIVATE AGENT SYSTEM", key="swarm_btn"):
    if not GEMINI_KEY:
        st.error("Please add your GEMINI_KEY to Streamlit Secrets.")
    else:
        with st.status("Agent Swarm Active...", expanded=True) as status:
            
            st.write("🔍 Analyst: Checking Market Confluence...")
            if prob_score >= 90 or test_mode:
                if test_mode: st.info("🧪 Test Mode: Bypassing technical filters.")
                
                st.write("🧠 Strategist: Performing News-Grounded Audit...")
                
                persona = f"""
                You are a cynical Senior Risk Manager for a {capital}€ fund. 
                Search news for {ticker}. If there is ANY major macro risk today, respond with 'VETO' and a blunt reason.
                Otherwise, respond with 'PROCEED'.
                """

                try:
                    # 1. AI Analysis
                    client = genai.Client(api_key=GEMINI_KEY)
                    response = client.models.generate_content(
                        model='gemini-3-flash-preview', 
                        contents=persona,
                        config=types.GenerateContentConfig(
                            tools=[types.Tool(google_search=types.GoogleSearch())],
                            temperature=1.0
                        )
                    )

                    # 2. Research Sources Box
                    metadata = getattr(response.candidates[0], "grounding_metadata", None)
                    if metadata:
                        with st.expander("📚 Strategist's Research Sources"):
                            if metadata.web_search_queries:
                                st.write(f"**Queries:** {', '.join(metadata.web_search_queries)}")
                            if metadata.grounding_chunks:
                                for i, chunk in enumerate(metadata.grounding_chunks):
                                    if chunk.web:
                                        st.markdown(f"**[{i+1}]** {chunk.web.title} — [Link]({chunk.web.uri})")

                    # 3. Decision & Dispatch
                    ai_decision = response.text.upper()
                    if "PROCEED" in ai_decision:
                        st.write("🛡️ Risk Audit: **PASSED**")
                        st.write("📡 Dispatcher: Sending Signal to Telegram...")
                        
                        msg = (f"🎯 **ALPHA SCOUT SIGNAL: {ticker}**\n"
                               f"Entry: ${round(price, 2)}\n"
                               f"Size: {round(pos_size, 2)}€\n"
                               f"AI Audit: PASSED ✅")
                        
                        if TG_TOKEN and CHAT_ID:
                            requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", 
                                          data={"chat_id": CHAT_ID, "text": msg})
                            status.update(label="✅ SUCCESS: Signal Sent!", state="complete")
                        else:
                            st.warning("Telegram settings missing.")
                            status.update(label="⚠️ Telegram Failed", state="error")
                    else:
                        st.error(f"❌ VETOED BY AI: {response.text}")
                        status.update(label="⚠️ Strategist Blocked Trade", state="error")

                except Exception as e:
                    st.error(f"AI Error: {e}")
                    status.update(label="❌ API Failure", state="error")
            else:
                st.warning(f"⚖️ Analyst: Probability ({prob_score}%) too low.")
                status.update(label="😴 Monitoring...", state="complete")
