import streamlit as st
import os
import yfinance as yf
import pandas as pd
from google import genai
from google.genai import types
from datetime import datetime, timedelta

# --- 1. CORE SETUP & IDENTITY ---
st.set_page_config(page_title="Momentum Master Terminal", layout="wide", page_icon="📈")

# Professional 'Dark Mode' Styling
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    .stMetric { background-color: #161b22; border-radius: 10px; padding: 15px; border: 1px solid #30363d; }
    [data-testid="stSidebar"] { background-color: #0d1117; }
    </style>
    """, unsafe_allow_html=True)

# Key Loader
GEMINI_KEY = os.environ.get("GEMINI_KEY") or st.secrets.get("GEMINI_KEY")
client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None

# --- 2. LIVE PULSE DATA (Non-Boring Landing) ---
@st.cache_data(ttl=3600)
def get_live_pulse():
    # March 2026 Power Tickers
    watch_list = ["NVDA", "BTC-USD", "SOL-USD", "MU", "APP", "TSLA"]
    pulse = []
    for t in watch_list:
        try:
            tk = yf.Ticker(t)
            price = tk.fast_info['last_price']
            change = tk.fast_info['day_change_percent']
            pulse.append({"Asset": t, "Price": f"${price:.2f}", "24H": f"{change:.2f}%"})
        except: continue
    return pd.DataFrame(pulse)

# --- 3. SIDEBAR: USER PARAMETERS ---
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/bullish.png")
    st.title("Momentum Master")
    st.write("---")
    
    budget = st.number_input("💵 Trading Budget (€)", min_value=100, value=1000, step=100)
    
    col_a, col_b = st.columns(2)
    start_d = col_a.date_input("📅 Start Date", datetime.now())
    end_d = col_b.date_input("🏁 End Date", datetime.now() + timedelta(days=30))
    
    stock_count = st.slider("🎯 Number of Stocks", 3, 7, 3)
    
    st.divider()
    st.markdown("### 🛰️ Website Intent")
    st.caption("This terminal uses Gemini 2.0 to synthesize 30-day technical momentum and upcoming catalysts into an actionable swing trading roadmap.")
    
    st.warning("⚠️ **Disclaimer:** This AI is for educational and entertainment purposes only. I am not a financial advisor. Trading involves high risk.")
    
    st.markdown("[🔗 Deep Logic: Google AI Studio](https://aistudio.google.com/)")

# --- 4. DASHBOARD HEADER ---
st.title("🛸 High-Conviction 30-Day Execution")
st.write(f"Current Date: **{datetime.now().strftime('%B %d, %Y')}**")

# Live Ticker Tape
pulse_df = get_live_pulse()
ticker_cols = st.columns(len(pulse_df))
for i, row in pulse_df.iterrows():
    ticker_cols[i].metric(row['Asset'], row['Price'], row['24H'])

st.divider()

# --- 5. SWING GENERATOR LOGIC ---
if st.button("🔥 GENERATE 30-DAY ACTION PLAN"):
    # Momentum Pool for March 2026
    pool = ["NVDA", "MU", "APP", "TSLA", "PLTR", "SOL-USD", "BTC-USD", "MSTR", "LITE", "AMZN"]
    
    with st.spinner("Momentum Master is scanning the tape..."):
        results = []
        for t in pool:
            try:
                tk = yf.Ticker(t)
                price = tk.fast_info['last_price']
                hist = tk.history(period="1mo")
                mom = ((hist['Close'].iloc[-1] - hist['Close'].iloc[0]) / hist['Close'].iloc[0]) * 100
                results.append({"Ticker": t, "Price": price, "Momentum": mom})
            except: continue
        
        top_picks = pd.DataFrame(results).sort_values("Momentum", ascending=False).head(stock_count)
        
        # Portfolio Display
        st.subheader(f"🥇 Recommended {stock_count}-Stock Swing Portfolio")
        budget_per_stock = budget / stock_count
        
        cols = st.columns(stock_count)
        for i, (_, row) in enumerate(top_picks.iterrows()):
            with cols[i]:
                shares = round(budget_per_stock / row['Price'], 2)
                st.write(f"### {row['Ticker']}")
                st.write(f"**Action:** Buy {shares} Units")
                st.metric("30D Momentum", f"{row['Momentum']:.1f}%")

        # Week-by-Week Plan (AI Generated)
        st.divider()
        st.subheader("📑 4-Week Strategic Roadmap")
        
        if client:
            prompt = (
                f"You are the Momentum Master. Generate a week-by-week strategy for: {top_picks['Ticker'].tolist()}. "
                f"Budget: {budget}€. Window: {start_d} to {end_d}. "
                f"Reference March 2026 catalysts: Nvidia GTC (March 16), Tesla FSD Europe approval (March 20), and BTC supply halving impact. "
                f"Week 1: Setup/Entry. Week 2: Catalyst Anticipation. Week 3: Risk Management. Week 4: Exit Strategy."
            )
            response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            st.info(response.text)
        else:
            st.error("Connect your Gemini API Key in the environment to see the 4-week plan.")

# --- 6. LANDING PAGE CONTENT ---
else:
    c1, c2 = st.columns([2, 1])
    with c1:
        st.write("### 🐂 Why Swing Trading in 2026?")
        st.write("""
        In a market driven by AI-factories and autonomous robotics, price action moves in **bursts**. 
        'Buy and Hold' is great, but 'Swing Trading' captures the 15-30% moves that happen 
        around key regulatory and technology milestones.
        """)
        st.markdown("""
        **How it works:**
        1. **Select Budget:** We calculate share counts so you don't have to.
        2. **Set Dates:** Minimum 30-day window for momentum to play out.
        3. **Analyze:** We combine YFinance data with Gemini's reasoning.
        """)
    with c2:
        st.image("https://img.icons8.com/fluency/200/bullish.png")
