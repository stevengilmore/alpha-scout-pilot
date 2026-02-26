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

# --- 2. GLOBAL WATCHLIST (Top Crypto, US Top 10, EU Blue Chips) ---
ASSET_MAP = {
    # Cryptocurrencies
    "BTC-USD": "Bitcoin", "ETH-USD": "Ethereum", "USDT-USD": "Tether", 
    "XRP-USD": "XRP", "BNB-USD": "Binance Coin",
    # S&P 10 (US Mega-Caps)
    "NVDA": "NVIDIA Corp", "AAPL": "Apple Inc.", "MSFT": "Microsoft Corp", 
    "AMZN": "Amazon.com Inc.", "GOOGL": "Alphabet Inc.", "META": "Meta Platforms", 
    "AVGO": "Broadcom Inc.", "TSLA": "Tesla Inc.", "BRK-B": "Berkshire Hathaway", 
    "LLY": "Eli Lilly & Co.",
    # European Anchors
    "AZN.L": "AstraZeneca", "HSBA.L": "HSBC Holdings", "SHEL.L": "Shell PLC",
    "SAP.DE": "SAP SE", "ALV.DE": "Allianz SE"
}

# --- 3. CORE ENGINES ---
@st.cache_data(ttl=300)
def get_market_pulse():
    pulse_data = []
    # Fetching latest 1mo daily for simple % change
    for ticker in list(ASSET_MAP.keys()):
        try:
            df = yf.download(ticker, period="1mo", interval="1d", progress=False)
            if not df.empty and len(df) > 1:
                # Handle MultiIndex if present
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                change = ((df['Close'].iloc[-1] - df['Close'].iloc[-2]) / df['Close'].iloc[-2]) * 100
                pulse_data.append({"Ticker": ticker, "Change": float(change)})
        except: continue
    return pd.DataFrame(pulse_data).sort_values(by="Change", key=abs, ascending=False)

def get_technical_analysis(ticker):
    # Request 2y to guarantee the 200-day EMA 'warm-up' period
    df = yf.download(ticker, period="2y", interval="1d", progress=False, auto_adjust=True)
    
    if df.empty or len(df) < 250: # Standard trading year is ~252 days
        return "NEUTRAL", 0, 0, pd.DataFrame()
    
    # Flatten MultiIndex to prevent indicator errors
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
        
    # Calculate EMA & RSI using pandas-ta
    df['EMA_200'] = ta.ema(df['Close'], length=200)
    df['RSI'] = ta.rsi(df['Close'], length=14)
    df.dropna(subset=['EMA_200', 'RSI'], inplace=True)
    
    if df.empty: return "NEUTRAL", 0, 0, pd.DataFrame()
    
    curr = df.iloc[-1]
    price = float(curr['Close'])
    ema = float(curr['EMA_200'])
    rsi = float(curr['RSI'])
    
    # Trend Analysis: LONG if price > EMA, SHORT if price < EMA
    direction = "LONG (🟢 Buy)" if price > ema else "SHORT (🔴 Sell)"
    
    # Confidence Score (75% Threshold)
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
        for _, row in movers.head(5).iterrows():
            color = "green" if row['Change'] > 0 else "red"
            st.markdown(f"**{row['Ticker']}**: :{color}[{round(row['Change'], 2)}%]")
    
    st.divider()
    threshold = st.slider("Sensitivity Threshold %", 50, 95, 75)
    test_mode = st.toggle("Enable AI Test Mode")

# Main Selection & Logic
selected_ticker = st.selectbox("Select Target Asset", list(ASSET_MAP.keys()))
trade_dir, prob_score, current_price, full_df = get_technical_analysis(selected_ticker)

col1, col2 = st.columns([2, 1])
with col1:
    if trade_dir != "NEUTRAL":
        st.subheader(f"📊 {ASSET_MAP[selected_ticker]} Analysis")
        st.metric("Directional Bias", trade_dir, f"{prob_score}% Confidence")
        st.line_chart(full_df[['Close', 'EMA_200']])
    else:
        st.error(f"⚠️ Data Unavailable: {selected_ticker} has insufficient history for a 200-day audit.")

with col2:
    st.subheader("🤖 AI Agent Swarm")
    if st.button("🚀 ACTIVATE AUDIT"):
        if trade_dir == "NEUTRAL" and not test_mode:
            st.error("Technical analysis failed. Audit blocked.")
        elif prob_score >= threshold or test_mode:
            with st.status("Strategist Performing Grounded Audit...", expanded=True) as status:
                try:
                    client = genai.Client(api_key=GEMINI_KEY)
                    response = client.models.generate_content(
                        model='gemini-3-flash-preview',
                        contents=f"Perform a macro risk audit for a {trade_dir} on {selected_ticker} at current price ${current_price}.",
                        config=types.GenerateContentConfig(
                            system_instruction="Cynical Risk Manager. Audit news via Google Search. VETO if risk, PROCEED if safe.",
                            tools=[types.Tool(google_search=types.GoogleSearch())]
                        )
                    )
                    
                    # Display Sources
                    metadata = getattr(response.candidates[0], "grounding_metadata", None)
                    if metadata:
                        with st.expander("📚 Research Sources"):
                            for i, chunk in enumerate(metadata.grounding_chunks or []):
                                if chunk.web:
                                    st.markdown(f"**[{i+1}]** {chunk.web.title} — [Read]({chunk.web.uri})")

                    if "PROCEED" in response.text.upper():
                        st.success("✅ AUDIT PASSED")
                        msg = f"🎯 **ALPHA SCOUT: {selected_ticker}**\nDir: {trade_dir}\nAudit: PASSED ✅"
                        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", data={"chat_id": CHAT_ID, "text": msg})
                        status.update(label="🚀 Signal Dispatched!", state="complete")
                    else:
                        st.error(f"❌ VETO: {response.text}")
                except Exception as e:
                    st.error(f"AI Failure: {e}")
        else:
            st.warning(f"Analyst: Confidence too low ({prob_score}% < {threshold}%)")
