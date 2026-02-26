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

# --- 2. THE GLOBAL WATCHLIST ---
ASSET_MAP = {
    "BTC-USD": "Bitcoin", "ETH-USD": "Ethereum", "NVDA": "NVIDIA Corp", 
    "AAPL": "Apple Inc.", "MSFT": "Microsoft Corp", "AMZN": "Amazon.com Inc.", 
    "GOOGL": "Alphabet Inc.", "META": "Meta Platforms", "TSLA": "Tesla Inc.", 
    "AZN.L": "AstraZeneca", "HSBA.L": "HSBC Holdings", "SAP.DE": "SAP SE"
}

# --- 3. DATA ENGINE ---
@st.cache_data(ttl=300)
def get_market_pulse():
    pulse_data = []
    # Using 1mo daily for simple, reliable volatility scanning
    for ticker in list(ASSET_MAP.keys())[:5]: # Scan first 5 for speed
        try:
            df = yf.download(ticker, period="1mo", interval="1d", progress=False)
            if not df.empty and len(df) > 1:
                change = ((df['Close'].iloc[-1] - df['Close'].iloc[-2]) / df['Close'].iloc[-2]) * 100
                pulse_data.append({"Ticker": ticker, "Change": float(change)})
        except: continue
    return pd.DataFrame(pulse_data).sort_values(by="Change", key=abs, ascending=False)

def get_technical_analysis(ticker):
    # BULLETPROOF: Request 2 years to ensure we clear the 200-day EMA requirement
    df = yf.download(ticker, period="2y", interval="1d", progress=False)
    
    if df.empty or len(df) < 250: # Standard trading year is ~252 days
        return "NEUTRAL", 0, 0, pd.DataFrame()
    
    # Calculate indicators
    df['EMA_200'] = ta.ema(df['Close'], length=200)
    df['RSI'] = ta.rsi(df['Close'], length=14)
    df.dropna(inplace=True)
    
    if df.empty: return "NEUTRAL", 0, 0, pd.DataFrame()
    
    curr = df.iloc[-1]
    price, ema, rsi = float(curr['Close']), float(curr['EMA_200']), float(curr['RSI'])
    
    direction = "LONG (🟢 Buy)" if price > ema else "SHORT (🔴 Sell)"
    score = 65 
    if (direction.startswith("LONG") and rsi < 45) or (direction.startswith("SHORT") and rsi > 55):
        score += 15
        
    return direction, score, price, df

# --- 4. UI LAYOUT ---
st.title("🛡️ Alpha Scout Pro: Command Center")

with st.sidebar:
    st.header("🔥 Market Pulse")
    movers = get_market_pulse()
    if not movers.empty:
        for _, row in movers.iterrows():
            st.write(f"**{row['Ticker']}**: {round(row['Change'], 2)}%")
    
    st.divider()
    threshold = st.slider("Sensitivity %", 50, 95, 75)
    test_mode = st.toggle("Enable AI Test Mode")

selected_ticker = st.selectbox("Target Asset", list(ASSET_MAP.keys()))
trade_dir, prob_score, current_price, full_df = get_technical_analysis(selected_ticker)

col1, col2 = st.columns([2, 1])
with col1:
    if trade_dir != "NEUTRAL":
        st.metric(f"Bias: {ASSET_MAP[selected_ticker]}", trade_dir, f"{prob_score}% Confidence")
        st.line_chart(full_df[['Close', 'EMA_200']])
    else:
        st.error(f"⚠️ Critical Data Error: Could not fetch enough history for {selected_ticker}. Please check your internet or API limits.")

with col2:
    st.subheader("🤖 AI Agent Swarm")
    if st.button("🚀 ACTIVATE AUDIT"):
        if trade_dir == "NEUTRAL" and not test_mode:
            st.error("Technical analysis failed. Audit blocked.")
        elif prob_score >= threshold or test_mode:
            with st.status("Strategist Grounding Audit...", expanded=True) as status:
                try:
                    client = genai.Client(api_key=GEMINI_KEY)
                    response = client.models.generate_content(
                        model='gemini-3-flash-preview',
                        contents=f"Perform macro audit for a {trade_dir} on {selected_ticker}.",
                        config=types.GenerateContentConfig(
                            system_instruction="Cynical Risk Manager. Audit for news risks. VETO or PROCEED.",
                            tools=[types.Tool(google_search=types.GoogleSearch())]
                        )
                    )
                    
                    if "PROCEED" in response.text.upper():
                        st.success("✅ AUDIT PASSED")
                        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", 
                                      data={"chat_id": CHAT_ID, "text": f"🎯 SIGNAL: {selected_ticker} PASSED AI AUDIT"})
                    else:
                        st.error(f"❌ VETO: {response.text}")
                except Exception as e:
                    st.error(f"AI Failure: {e}")
