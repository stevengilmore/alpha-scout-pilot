import streamlit as st
import os
import yfinance as yf
import pandas as pd
from google import genai
from google.genai import types
from datetime import datetime, timedelta

# --- 1. CONFIG & VIVID STYLING ---
st.set_page_config(page_title="Momentum Master Terminal", layout="wide", page_icon="📈")

# Full CSS Overhaul for High-Contrast Readability
st.markdown("""
    <style>
    /* Main Background */
    .main { background-color: #0d1117; color: #ffffff; }
    
    /* SIDEBAR: High-Contrast White Text */
    [data-testid="stSidebar"] {
        background-color: #161b22 !important;
        border-right: 1px solid #30363d;
    }
    [data-testid="stSidebar"] .stMarkdown p, 
    [data-testid="stSidebar"] label, 
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: #ffffff !important;
        font-weight: 700 !important;
    }

    /* INFO & SUCCESS BOXES: Force Solid Background & White Text */
    .stAlert {
        background-color: #21262d !important;
        color: #ffffff !important;
        border: 1px solid #30363d !important;
    }
    .stAlert p {
        color: #ffffff !important;
        font-size: 1.05rem !important;
    }

    /* METRIC CARDS */
    .stMetric {
        background-color: #1c2128;
        border-radius: 12px;
        padding: 20px;
        border: 1px solid #444c56;
    }
    [data-testid="stMetricValue"] { color: #58a6ff !important; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# 2026 Stable Model Update
GEMINI_KEY = os.environ.get("GEMINI_KEY") or st.secrets.get("GEMINI_KEY")
client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None
LATEST_MODEL = "gemini-3-flash"

# --- 2. DATA ENGINE: Pulling Full Company Names ---
@st.cache_data(ttl=300)
def get_stock_data(tickers):
    data = []
    for t in tickers:
        try:
            tk = yf.Ticker(t)
            info = tk.info
            # Use longName or shortName to avoid confusing tickers
            full_name = info.get('longName') or info.get('shortName') or t
            price = tk.fast_info['last_price']
            
            # Momentum Calculation
            hist = tk.history(period="1mo")
            mom = ((hist['Close'].iloc[-1] - hist['Close'].iloc[0]) / hist['Close'].iloc[0]) * 100
            
            data.append({
                "Ticker": t,
                "Name": full_name,
                "Price": price,
                "Momentum": mom
            })
        except: continue
    return pd.DataFrame(data)

# --- 3. SIDEBAR: THE COMMAND CENTER ---
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/bullish.png")
    st.title("Momentum Master")
    st.divider()
    
    budget = st.number_input("💵 Trading Budget (€)", min_value=100, value=1000, step=100)
    
    col_a, col_b = st.columns(2)
    start_d = col_a.date_input("📅 Start Date", datetime.now())
    end_d = col_b.date_input("🏁 End Date", datetime.now() + timedelta(days=30))
    
    stock_count = st.slider("🎯 Portfolio Size", 3, 7, 3)
    
    st.divider()
    st.markdown("### 🚀 Terminal Intent")
    st.write("Synthesizing technical momentum and real-world catalysts into a 30-day plan.")
    st.warning("⚠️ **Disclaimer:** Educational/Entertainment only. Trading involves high risk.")
    st.markdown("[🔗 Deep Analysis: Google AI Studio](https://aistudio.google.com/)")

# --- 4. DASHBOARD HEADER ---
st.title("🛸 High-Conviction 30-Day Execution")

# Quick Pulse Bar
pulse_list = ["NVDA", "BTC-USD", "SOL-USD", "MU", "TSLA"]
pulse_df = get_stock_data(pulse_list)

if not pulse_df.empty:
    ticker_cols = st.columns(len(pulse_df))
    for i, row in pulse_df.iterrows():
        ticker_cols[i].metric(row['Ticker'], f"${row['Price']:.2f}", f"{row['Momentum']:.1f}%")

st.divider()

# --- 5. SWING GENERATOR ---
if st.button("🔥 GENERATE 30-DAY ACTION PLAN"):
    # March 2026 Core Momentum Pool
    pool_list = ["NVDA", "MU", "APP", "TSLA", "PLTR", "SOL-USD", "BTC-USD", "MSTR", "AMZN", "LITE"]
    
    with st.spinner("Analyzing current momentum regime..."):
        full_pool = get_stock_data(pool_list)
        
        if not full_pool.empty:
            top_picks = full_pool.sort_values("Momentum", ascending=False).head(stock_count)
            
            st.subheader(f"🥇 Recommended {stock_count}-Stock Swing Portfolio")
            budget_per_stock = budget / stock_count
            
            cols = st.columns(len(top_picks))
            for i, (_, row) in enumerate(top_picks.iterrows()):
                with cols[i]:
                    shares = round(budget_per_stock / row['Price'], 2)
                    # Display Full Name for clarity
                    st.write(f"### {row['Name']}")
                    st.caption(f"Ticker: {row['Ticker']}")
                    st.write(f"**Action:** Buy {shares} Units")
                    st.metric("30D Momentum", f"{row['Momentum']:.1f}%")

            # Week-by-Week Strategy
            st.divider()
            st.subheader("📑 4-Week Strategic Roadmap")
            if client:
                portfolio_names = top_picks['Name'].tolist()
                prompt = (f"As Momentum Master trader, provide a week-by-week strategy for {portfolio_names} "
                          f"from {start_d} to {end_d}. Budget is {budget}€. Reference March 2026 catalysts.")
                response = client.models.generate_content(model=LATEST_MODEL, contents=prompt)
                # Success box is now solid dark with white text
                st.info(response.text)
            else:
                st.error("Missing Gemini API Key in Environment.")
        else:
            st.error("Market data connection lost. Please try again.")

# --- 6. LANDING CONTENT ---
else:
    c1, c2 = st.columns([2, 1])
    with c1:
        st.write("### 🐂 Why Swing Trading?")
        st.write("Capture the 15-30% moves around technology milestones and institutional rotations.")
    with c2:
        st.image("https://img.icons8.com/fluency/200/combo-chart.png")
