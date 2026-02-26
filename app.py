import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests
from google import genai
from google.genai import types

# --- 1. SETTINGS & SECRETS ---
st.set_page_config(page_title="Alpha Scout Pro", page_icon="🛡️", layout="wide")

GEMINI_KEY = st.secrets.get("GEMINI_KEY")
TG_TOKEN = st.secrets.get("TG_TOKEN")
CHAT_ID = st.secrets.get("CHAT_ID")

# --- 2. THE GLOBAL WATCHLIST (Institutional Anchors) ---
ASSET_MAP = {
    # Cryptocurrencies
    "BTC-USD": "Bitcoin", "ETH-USD": "Ethereum", "USDT-USD": "Tether", 
    "XRP-USD": "XRP", "BNB-USD": "Binance Coin",
    # S&P 10 (US Mega-Caps)
    "NVDA": "NVIDIA Corp", "AAPL": "Apple Inc.", "MSFT": "Microsoft Corp", 
    "AMZN": "Amazon.com Inc.", "GOOGL": "Alphabet Inc.", "META": "Meta Platforms", 
    "AVGO": "Broadcom Inc.", "TSLA": "Tesla Inc.", "BRK-B": "Berkshire Hathaway", 
    "LLY": "Eli Lilly & Co.",
    # European Anchors (FTSE & DAX)
    "AZN.L": "AstraZeneca", "HSBA.L": "HSBC Holdings", "SHEL.L": "Shell PLC",
    "SAP.DE": "SAP SE", "ALV.DE": "Allianz SE"
}

# --- 3. DATA & VOLATILITY ENGINE ---
@st.cache_data(ttl=300)
def get_market_pulse():
    pulse_data = []
    for ticker in list(ASSET_MAP.keys()):
        try:
            # Fetching 1 month for stable daily volatility calculation
            df = yf.download(ticker, period="1mo", interval="1d", progress=False)
            if not df.empty and len(df) > 1:
                change = ((df['Close'].iloc[-1] - df['Close'].iloc[-2]) / df['Close'].iloc[-2]) * 100
                pulse_data.append({"Ticker": ticker, "Change": float(change)})
        except: continue
    return pd.DataFrame(pulse_data).sort_values(by="Change", key=abs, ascending=False)

def get_technical_analysis(ticker):
    # EXTENDED PERIOD: Download 60 days to satisfy 200 EMA requirements
    df = yf.download(ticker, period="60d", interval="1h", progress=False)
    
    if df.empty or len(df) < 200: # Ensure enough rows for EMA calculation
        return "NEUTRAL", 0, 0
    
    # Calculate indicators using pandas-ta
    ema_series = ta.ema(df['Close'], length=200)
    
    # Safety check to avoid .iloc errors on empty indicators
    if ema_series is None or ema_series.isna().all():
        return "NEUTRAL", 0, 0
        
    ema = ema_series.iloc[-1]
    rsi = ta.rsi(df['Close']).iloc[-1]
    price = float(df['Close'].iloc[-1])
    
    # Trend Analysis: Long if price > EMA, Short if price < EMA
    direction = "LONG (🟢 Buy)" if price > ema else "SHORT (🔴 Sell)"
    
    # Probability confidence score (75% threshold)
    score = 65 
    if (direction.startswith("LONG") and rsi < 45) or (direction.startswith("SHORT") and rsi > 55):
        score += 15
    return direction, score, price

# --- 4. DASHBOARD UI ---
st.title("🛡️ Alpha Scout Pro: Global Command")

# Volatility Pulse Sidebar
with st.sidebar:
    st.header("🔥 Volatility Pulse")
    movers = get_market_pulse()
    if not movers.empty:
        for _, row in movers.head(5).iterrows():
            color = "green" if row['Change'] > 0 else "red"
            st.markdown(f"**{row['Ticker']}**: :{color}[{round(row['Change'], 2)}%]")
    
    st.divider()
    threshold = st.slider("Sensitivity Threshold %", 50, 95, 75)
    test_mode = st.toggle("Enable AI Test Mode")

# Main Selection
selected_ticker = st.selectbox("Select Target Asset", list(ASSET_MAP.keys()))
trade_dir, prob_score, current_price = get_technical_analysis(selected_ticker)

col1, col2 = st.columns([2, 1])
with col1:
    st.subheader(f"📊 {ASSET_MAP[selected_ticker]} Analysis")
    if trade_dir != "NEUTRAL":
        st.metric("Directional Bias", trade_dir, f"{prob_score}% Confidence")
        # Visualizing the last 60 days of hourly data
        df_chart = yf.download(selected_ticker, period="60d", interval="1h", progress=False)
        df_chart['EMA_200'] = ta.ema(df_chart['Close'], length=200)
        st.line_chart(df_chart[['Close', 'EMA_200']])
    else:
        st.warning("Insufficient data for technical indicators. Try a different asset.")

with col2:
    st.subheader("🤖 Swarm Strategist")
    if st.button("🚀 RUN AI AUDIT"):
        if trade_dir == "NEUTRAL":
            st.error("Cannot audit without technical confirmation.")
        elif prob_score >= threshold or test_mode:
            with st.status("Strategist Performing Audit...", expanded=True) as status:
                try:
                    client = genai.Client(api_key=GEMINI_KEY)
                    system_persona = "You are a cynical Risk Manager. Audit for macro risks. PROCEED or VETO."
                    
                    response = client.models.generate_content(
                        model='gemini-3-flash-preview',
                        contents=f"Audit a {trade_dir} on {ASSET_MAP[selected_ticker]}.",
                        config=types.GenerateContentConfig(
                            system_instruction=system_persona,
                            tools=[types.Tool(google_search=types.GoogleSearch())]
                        )
                    )
                    
                    if "PROCEED" in response.text.upper():
                        st.success("✅ AUDIT PASSED")
                        msg = f"🎯 **ALPHA SIGNAL: {selected_ticker}**\nDir: {trade_dir}\nPrice: ${round(current_price, 2)}\nAudit: PASSED"
                        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", data={"chat_id": CHAT_ID, "text": msg})
                        status.update(label="🚀 Signal Dispatched!", state="complete")
                    else:
                        st.error(f"❌ VETO: {response.text}")
                except Exception as e:
                    st.error(f"API Error: {e}")
        else:
            st.warning(f"Analyst: Confidence too low ({prob_score}% < {threshold}%)")
