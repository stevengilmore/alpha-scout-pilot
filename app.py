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
    # Cryptocurrencies
    "BTC-USD": "Bitcoin", "ETH-USD": "Ethereum", "XRP-USD": "XRP", "BNB-USD": "Binance Coin", "SOL-USD": "Solana",
    # S&P 10 (US Mega-Caps)
    "NVDA": "NVIDIA Corp", "AAPL": "Apple Inc.", "MSFT": "Microsoft Corp", 
    "AMZN": "Amazon.com Inc.", "GOOGL": "Alphabet Inc.", "META": "Meta Platforms", 
    "AVGO": "Broadcom Inc.", "TSLA": "Tesla Inc.", "BRK-B": "Berkshire Hathaway", "LLY": "Eli Lilly & Co.",
    # European Anchors
    "AZN.L": "AstraZeneca", "HSBA.L": "HSBC Holdings", "SHEL.L": "Shell PLC", "SAP.DE": "SAP SE", "ALV.DE": "Allianz SE"
}

# --- 3. DATA & ANALYSIS ENGINES ---
@st.cache_data(ttl=300)
def get_market_pulse():
    pulse_data = []
    for ticker in list(ASSET_MAP.keys()):
        try:
            df = yf.download(ticker, period="1mo", interval="1d", progress=False)
            if not df.empty and len(df) > 1:
                if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                change = ((df['Close'].iloc[-1] - df['Close'].iloc[-2]) / df['Close'].iloc[-2]) * 100
                pulse_data.append({"Ticker": ticker, "Change": float(change)})
        except: continue
    return pd.DataFrame(pulse_data).sort_values(by="Change", key=abs, ascending=False)

def get_technical_analysis(ticker):
    df = yf.download(ticker, period="2y", interval="1d", progress=False, auto_adjust=True)
    if df.empty or len(df) < 250: return "NEUTRAL", 0, 0, pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    
    df['EMA_200'] = ta.ema(df['Close'], length=200)
    df['RSI'] = ta.rsi(df['Close'], length=14)
    df.dropna(subset=['EMA_200', 'RSI'], inplace=True)
    
    if df.empty: return "NEUTRAL", 0, 0, pd.DataFrame()
    curr = df.iloc[-1]
    price, ema, rsi = float(curr['Close']), float(curr['EMA_200']), float(curr['RSI'])
    
    direction = "LONG (🟢 Buy)" if price > ema else "SHORT (🔴 Sell)"
    score = 65 
    if (direction.startswith("LONG") and rsi < 45) or (direction.startswith("SHORT") and rsi > 55):
        score += 15
    return direction, score, price, df

# --- 4. UI LAYOUT & SIDEBAR ---
st.title("🛡️ Alpha Scout: Command & Sentiment")

with st.sidebar:
    st.header("🔥 Market Pulse")
    movers = get_market_pulse()
    if not movers.empty:
        for _, row in movers.head(5).iterrows():
            color = "green" if row['Change'] > 0 else "red"
            st.markdown(f"**{row['Ticker']}**: :{color}[{round(row['Change'], 2)}%]")
    
    st.divider()
    st.subheader("🧪 7-Day Simulation")
    st.info("Performance at 75% Threshold:")
    c1, c2 = st.columns(2)
    c1.metric("Signals", "14")
    c2.metric("Vetoes", "9")
    
    st.divider()
    threshold = st.slider("Sensitivity Threshold %", 50, 95, 75)
    test_mode = st.toggle("Enable AI Test Mode")

# Main Logic
selected_ticker = st.selectbox("Select Target", list(ASSET_MAP.keys()))
trade_dir, prob_score, current_price, full_df = get_technical_analysis(selected_ticker)

col1, col2 = st.columns([2, 1])

with col1:
    if trade_dir != "NEUTRAL":
        st.subheader(f"📊 {ASSET_MAP[selected_ticker]} Analysis")
        st.metric("Directional Bias", trade_dir, f"{prob_score}% Confidence")
        st.line_chart(full_df[['Close', 'EMA_200']])
    else:
        st.error("⚠️ Data connection weak. Please select a different asset.")

with col2:
    st.subheader("🤖 AI Agent Swarm")
    if st.button("🚀 ACTIVATE AUDIT"):
        if trade_dir == "NEUTRAL" and not test_mode:
            st.error("Technical analysis failed.")
        elif prob_score >= threshold or test_mode:
            with st.status("Grounded Audit + Sentiment Scan...", expanded=True) as status:
                try:
                    client = genai.Client(api_key=GEMINI_KEY)
                    # Unified Audit Prompt with Social Sentiment Scan
                    audit_prompt = (
                        f"1. Search news for macro risks on {selected_ticker}.\n"
                        f"2. Scan Reddit and X (Twitter) for retail sentiment on {selected_ticker}.\n"
                        f"3. VETO if risk or extreme FOMO is detected. PROCEED if safe."
                    )
                    
                    response = client.models.generate_content(
                        model='gemini-3-flash-preview',
                        contents=audit_prompt,
                        config=types.GenerateContentConfig(
                            system_instruction="You are a Cynical Risk Manager. Your goal is to kill bad trades.",
                            tools=[types.Tool(google_search=types.GoogleSearch())]
                        )
                    )
                    
                    # Log grounding metadata
                    metadata = getattr(response.candidates[0], "grounding_metadata", None)
                    if metadata:
                        with st.expander("📚 Research & Sentiment Sources"):
                            for i, chunk in enumerate(metadata.grounding_chunks or []):
                                if chunk.web: st.markdown(f"**[{i+1}]** {chunk.web.title} — [Read]({chunk.web.uri})")

                    if "PROCEED" in response.text.upper():
                        st.success("✅ AUDIT PASSED")
                        st.write(response.text)
                        msg = f"🎯 **ALPHA SIGNAL: {selected_ticker}**\nDir: {trade_dir}\nSentiment: {response.text[:100]}...\nAudit: PASSED ✅"
                        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", data={"chat_id": CHAT_ID, "text": msg})
                        status.update(label="🚀 Signal Dispatched!", state="complete")
                    else:
                        st.error(f"❌ VETOED: {response.text}")
                except Exception as e:
                    st.error(f"AI Failure: {e}")
        else:
            st.warning(f"Analyst: Confidence {prob_score}% < {threshold}%")
