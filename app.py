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
    ticker = st.selectbox("Select Primary Asset", ["QQQ", "SPY", "BTC-USD", "NVDA", "AAPL", "TSLA"])
    capital = 2500  
    risk_euro = 25  
    
    st.divider()
    st.subheader("🛠️ Developer Tools")
    test_mode = st.toggle("Enable Test Mode", help="Bypasses technical filters for demo.")

# --- 3. DATA ENGINE ---
@st.cache_data(ttl=60)
def get_market_data(symbol):
    try:
        df = yf.download(symbol, period="5d", interval="5m", auto_adjust=True)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df['EMA_200'] = ta.ema(df['Close'], length=200)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        return df
    except Exception as e:
        st.error(f"Error fetching {symbol}: {e}")
        return pd.DataFrame()

# --- 4. SCANNER LOGIC ---
def calculate_score(df):
    if df.empty: return 0
    curr = df.iloc[-1]
    price = float(curr['Close'])
    ema = float(curr['EMA_200'])
    rsi = float(curr['RSI'])
    
    score = 0
    if price > ema: score += 60
    if rsi < 45: score += 30
    return score

# --- 5. DASHBOARD UI ---
st.title(f"🛡️ Alpha Scout Pro")

# --- PROACTIVE SCANNER SECTION ---
st.header("🛰️ Proactive Watchlist Scanner")
watchlist = ["AAPL", "NVDA", "TSLA", "BTC-USD", "SPY", "QQQ"]

if st.button("🔍 Scan All Assets Now"):
    with st.status("Scanning markets...", expanded=False) as status:
        found_hits = []
        for symbol in watchlist:
            df_scan = get_market_data(symbol)
            score = calculate_score(df_scan)
            if score >= 90:
                found_hits.append(symbol)
                st.write(f"🎯 **{symbol}** matches criteria ({score}%)")
        
        if not found_hits:
            status.update(label="😴 No high-probability setups found.", state="complete")
        else:
            status.update(label=f"🎯 Found {len(found_hits)} opportunities!", state="complete")
            st.session_state['active_hits'] = found_hits

if 'active_hits' in st.session_state and st.session_state['active_hits']:
    st.success(f"Top Picks: {', '.join(st.session_state['active_hits'])}")

st.divider()

# --- MAIN ANALYSIS SECTION ---
data = get_market_data(ticker)
if not data.empty:
    curr = data.iloc[-1]
    prob_score = calculate_score(data)
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader(f"📊 {ticker} Live Chart")
        st.line_chart(data[['Close', 'EMA_200']])
        m1, m2, m3 = st.columns(3)
        m1.metric("Price", f"${round(curr['Close'], 2)}")
        m2.metric("RSI", round(curr['RSI'], 1))
        m3.metric("Probability", f"{prob_score}%")

    with col2:
        st.subheader("💰 Risk Manager")
        atr = float(curr['ATR'])
        stop_loss_dist = (atr * 2)
        pos_size = min(capital, (risk_euro / (stop_loss_dist / float(curr['Close'])))) if stop_loss_dist > 0 else 0
        
        st.write(f"Bankroll: **{capital} €**")
        st.write(f"Risk per Trade: **{risk_euro} €**")
        st.success(f"Suggested Entry: **{round(pos_size, 2)} €**")

# --- 6. THE AGENT SWARM (STRATEGIST & DISPATCHER) ---
st.header("🤖 Autonomous Agent Swarm")

if st.button("🚀 ACTIVATE AGENT SYSTEM", key="swarm_btn"):
    if not GEMINI_KEY:
        st.error("Missing GEMINI_KEY in Secrets.")
    else:
        with st.status("Agent Swarm Active...", expanded=True) as status:
            st.write("🔍 Analyst: Checking Market Confluence...")
            
            if prob_score >= 90 or test_mode:
                if test_mode: st.info("🧪 Test Mode: Bypassing technical filters.")
                
                st.write("🧠 Strategist: Performing News-Grounded Audit...")
                persona = f"You are a cynical Senior Risk Manager for a {capital}€ fund. Search news for {ticker}. VETO if risk exists, else PROCEED."

                try:
                    client = genai.Client(api_key=GEMINI_KEY)
                    response = client.models.generate_content(
                        model='gemini-3-flash-preview', 
                        contents=persona,
                        config=types.GenerateContentConfig(
                            tools=[types.Tool(google_search=types.GoogleSearch())],
                            temperature=1.0
                        )
                    )

                    # Research Sources
                    metadata = getattr(response.candidates[0], "grounding_metadata", None)
                    if metadata:
                        with st.expander("📚 Strategist's Research Sources"):
                            for i, chunk in enumerate(metadata.grounding_chunks or []):
                                if chunk.web:
                                    st.markdown(f"**[{i+1}]** {chunk.web.title} — [Link]({chunk.web.uri})")

                    if "PROCEED" in response.text.upper():
                        st.write("🛡️ Risk Audit: **PASSED**")
                        
                        # GATE 3: DISPATCHER (Robust Telegram)
                        st.write("📡 Dispatcher: Sending Signal to Telegram...")
                        msg = f"🎯 **ALPHA SCOUT: {ticker}**\nPrice: ${round(curr['Close'], 2)}\nSize: {round(pos_size, 2)}€\nAI Audit: PASSED ✅"
                        
                        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
                        t_res = requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=10)
                        
                        if t_res.status_code == 200:
                            st.balloons()
                            status.update(label="✅ SUCCESS: Signal Sent!", state="complete")
                        else:
                            st.error(f"Telegram Error {t_res.status_code}: {t_res.text}")
                    else:
                        st.error(f"❌ VETOED BY AI: {response.text}")
                        status.update(label="⚠️ Strategist Blocked Trade", state="error")

                except Exception as e:
                    st.error(f"AI Error: {e}")
                    status.update(label="❌ API Failure", state="error")
            else:
                st.warning(f"⚖️ Analyst: Probability ({prob_score}%) too low.")
                status.update(label="😴 Monitoring...", state="complete")
