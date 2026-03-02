import streamlit as st
import os
import yfinance as yf
import pandas as pd
from google import genai
from google.genai import types
from datetime import datetime, timedelta

# --- 1. CORE SETUP & STYLING (Fixed for Readability) ---
st.set_page_config(page_title="Momentum Master Terminal", layout="wide", page_icon="📈")

# High-Contrast Readability Styling
st.markdown("""
    <style>
    /* Main Background and Text */
    .main { background-color: #0e1117; color: #ffffff; }
    
    /* SIDEBAR READABILITY FIX */
    [data-testid="stSidebar"] {
        background-color: #1a1c24 !important;
        border-right: 1px solid #3d444d;
    }
    [data-testid="stSidebar"] .stMarkdown p, [data-testid="stSidebar"] label {
        color: #f0f2f6 !important; /* Bright off-white for text */
        font-weight: 500;
        font-size: 16px;
    }
    
    /* Metric Boxes Styling */
    .stMetric {
        background-color: #161b22;
        border-radius: 10px;
        padding: 15px;
        border: 1px solid #30363d;
    }
    </style>
    """, unsafe_allow_html=True)

GEMINI_KEY = os.environ.get("GEMINI_KEY") or st.secrets.get("GEMINI_KEY")
client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None

# --- 2. LIVE PULSE DATA ---
@st.cache_data(ttl=300) # Reduced TTL to keep it fresh
def get_live_pulse():
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
    st.divider()
    
    budget = st.number_input("💵 Trading Budget (€)", min_value=100, value=1000, step=100)
    
    col_a, col_b = st.columns(2)
    start_d = col_a.date_input("📅 Start Date", datetime.now())
    end_d = col_b.date_input("🏁 End Date", datetime.now() + timedelta(days=30))
    
    stock_count = st.slider("🎯 Number of Stocks", 3, 7, 3)
    
    st.divider()
    st.markdown("### 🛰️ Terminal Intent")
    st.write("This tool identifies 30-day technical momentum to build an actionable swing roadmap.")
    st.warning("⚠️ **Disclaimer:** For educational/entertainment use only. Trading involves high risk.")
    st.markdown("[🔗 Deep Analysis: Google AI Studio](https://aistudio.google.com/)")

# --- 4. DASHBOARD HEADER ---
st.title("🛸 High-Conviction 30-Day Execution")

# Live Ticker Tape (With Error Fix)
pulse_df = get_live_pulse()
if not pulse_df.empty:
    ticker_cols = st.columns(len(pulse_df)) # len(pulse_df) is now guaranteed > 0
    for i, row in pulse_df.iterrows():
        ticker_cols[i].metric(row['Asset'], row['Price'], row['24H'])
else:
    st.info("🛰️ Initializing market pulse... Refreshing data.")

st.divider()

# --- 5. SWING GENERATOR LOGIC ---
if st.button("🔥 GENERATE 30-DAY ACTION PLAN"):
    pool = ["NVDA", "MU", "APP", "TSLA", "PLTR", "SOL-USD", "BTC-USD", "MSTR", "LITE", "AMZN"]
    
    with st.spinner("Scanning for relative strength..."):
        results = []
        for t in pool:
            try:
                tk = yf.Ticker(t)
                price = tk.fast_info['last_price']
                hist = tk.history(period="1mo")
                mom = ((hist['Close'].iloc[-1] - hist['Close'].iloc[0]) / hist['Close'].iloc[0]) * 100
                results.append({"Ticker": t, "Price": price, "Momentum": mom})
            except: continue
        
        if results:
            top_picks = pd.DataFrame(results).sort_values("Momentum", ascending=False).head(stock_count)
            
            # Portfolio Display
            st.subheader(f"🥇 Recommended {stock_count}-Stock Swing Portfolio")
            budget_per_stock = budget / stock_count
            
            cols = st.columns(len(top_picks))
            for i, (_, row) in enumerate(top_picks.iterrows()):
                with cols[i]:
                    shares = round(budget_per_stock / row['Price'], 2)
                    st.write(f"### {row['Ticker']}")
                    st.write(f"**Action:** Buy {shares} Units")
                    st.metric("30D Momentum", f"{row['Momentum']:.1f}%")

            # Week-by-Week Plan
            st.divider()
            st.subheader("📑 4-Week Strategic Roadmap")
            if client:
                prompt = (f"Act as 'Momentum Master' swing trader. Create a week-by-week strategy for {top_picks['Ticker'].tolist()} "
                          f"from {start_d} to {end_d}. Reference specific catalysts like Nvidia GTC or rate decisions.")
                response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
                st.info(response.text)
        else:
            st.error("Market data connection lost. Please try again.")

# --- 6. LANDING PAGE ---
else:
    c1, c2 = st.columns([2, 1])
    with c1:
        st.write("### 🐂 Why Swing Trading?")
        st.write("Capture the 15-30% moves around technology milestones and institutional rotations.")
    with c2:
        st.image("https://img.icons8.com/fluency/200/combo-chart.png")
