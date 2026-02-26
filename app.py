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

# --- 2. GLOBAL WATCHLIST ---
ASSET_MAP = {
    # Cryptocurrencies
    "BTC-USD": "Bitcoin", "ETH-USD": "Ethereum", "USDT-USD": "Tether", 
    "XRP-USD": "XRP", "BNB-USD": "Binance Coin",
    # S&P 500 Top 10
    "NVDA": "NVIDIA Corp", "AAPL": "Apple Inc.", "MSFT": "Microsoft Corp", 
    "AMZN": "Amazon.com Inc.", "GOOGL": "Alphabet Inc.", "META": "Meta Platforms", 
    "AVGO": "Broadcom Inc.", "TSLA": "Tesla Inc.", "BRK-B": "Berkshire Hathaway", 
    "LLY": "Eli Lilly & Co.",
    # European Blue Chips
    "AZN.L": "AstraZeneca", "HSBA.L": "HSBC Holdings", "SHEL.L": "Shell PLC",
    "SAP.DE": "SAP SE", "ALV.DE": "Allianz SE"
}

# --- 3. DATA & VOLATILITY ENGINE ---
@st.cache_data(ttl=300)
def get_market_pulse():
    pulse_data = []
    for ticker in list(ASSET_MAP.keys()):
        try:
            # 1mo daily data is highly reliable for volatility scanning
            df = yf.download(ticker, period="1mo", interval="1d", progress=False)
            if not df.empty and len(df) > 1:
                change = ((df['Close'].iloc[-1] - df['Close'].iloc[-2]) / df['Close'].iloc[-2]) * 100
                pulse_data.append({"Ticker": ticker, "Change": float(change)})
        except: continue
    return pd.DataFrame(pulse_data).sort_values(by="Change", key=abs, ascending=False)

def get_technical_analysis(ticker):
    # BULLETPROOF FIX: Request 1y daily data to ensure 200+ candles for EMA
    df = yf.download(ticker, period="1y", interval="1d", progress=False)
    
    if df.empty or len(df) < 200: 
        return "NEUTRAL", 0, 0, pd.DataFrame()
    
    # Calculate indicators
    df['EMA_200'] = ta.ema(df['Close'], length=200)
    df['RSI'] = ta.rsi(df['Close'], length=14)
    df.dropna(inplace=True) # Ensure clean rows for calculation
    
    if df.empty: return "NEUTRAL", 0, 0, pd.DataFrame()
    
    curr = df.iloc[-1]
    price = float(curr['Close'])
    ema = float(curr['EMA_200'])
    rsi = float(curr['RSI'])
    
    # Trend Analysis
    direction = "LONG (🟢 Buy)" if price > ema else "SHORT (🔴 Sell)"
    
    # Confidence Score (75% Threshold)
    score = 65 
    if (direction.startswith("LONG") and rsi < 45) or (direction.startswith("SHORT") and rsi > 55):
        score += 15
    return direction, score, price, df

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
    threshold = st.sidebar.slider("Sensitivity Threshold %", 50, 95, 75)
    test_mode = st.sidebar.toggle("Enable AI Test Mode")

# Main Selection
selected_ticker = st.selectbox("Select Target Asset", list(ASSET_MAP.keys()))
trade_dir, prob_score, current_price, full_df = get_technical_analysis(selected_ticker)

col1, col2 = st.columns([2, 1])
with col1:
    st.subheader(f"📊 {ASSET_MAP[selected_ticker]} Analysis")
    if trade_dir != "NEUTRAL":
        st.metric("Directional Bias", trade_dir, f"{prob_score}% Confidence")
        st.line_chart(full_df[['Close', 'EMA_200']])
    else:
        st.warning("Insufficient data for 200-day indicators. Trying 1y daily fallback...")

with col2:
    st.subheader("🤖 Swarm Strategist")
    if st.button("🚀 RUN AI AUDIT"):
        if trade_dir == "NEUTRAL" and not test_mode:
            st.error("Cannot audit without technical confirmation.")
        elif prob_score >= threshold or test_mode:
            with st.status("Strategist Performing Audit...", expanded=True) as status:
                try:
                    client = genai.Client(api_key=GEMINI_KEY)
                    system_persona = "You are a cynical Risk Manager. Audit for macro risks. PROCEED or VETO."
                    
                    response = client.models.generate_content(
                        model='gemini-3-flash-preview',
                        contents=f"Audit a {trade_dir} on {ASSET_MAP[selected_ticker]} at ${current_price}.",
                        config=types.GenerateContentConfig(
                            system_instruction=system_persona,
                            tools=[types.Tool(google_search=types.GoogleSearch())]
                        )
                    )
                    
                    # Citations/Metadata Expandable
                    metadata = getattr(response.candidates[0], "grounding_metadata", None)
                    if metadata:
                        with st.expander("📚 Research Sources"):
                            for i, chunk in enumerate(metadata.grounding_chunks or []):
                                if chunk.web:
                                    st.markdown(f"**[{i+1}]** {chunk.web.title} — [Link]({chunk.web.uri})")

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
