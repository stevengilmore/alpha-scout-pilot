import streamlit as st
import os
import yfinance as yf
import pandas as pd
from google import genai
from google.genai import types
from datetime import datetime, timedelta

# --- 1. CONFIG & HIGH-CONTRAST STYLING ---
st.set_page_config(page_title="Momentum Master Terminal", layout="wide", page_icon="📈")

# Final CSS Overhaul for Perfect Readability
st.markdown("""
    <style>
    /* Global Background & Body Text */
    .main { background-color: #0d1117; color: #ffffff !important; }
    
    /* SIDEBAR: Ultra-High Contrast */
    [data-testid="stSidebar"] {
        background-color: #1a1c24 !important;
        border-right: 1px solid #3d444d;
    }
    [data-testid="stSidebar"] .stMarkdown p, 
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] div,
    [data-testid="stSidebar"] span {
        color: #ffffff !important;
        font-weight: 700 !important;
        font-size: 1.05rem !important;
    }
    
    /* ALERT & INFO BOXES: No more grey-on-black */
    .stAlert {
        background-color: #1c2128 !important;
        color: #ffffff !important;
        border: 2px solid #58a6ff !important;
    }
    .stAlert p, .stAlert div {
        color: #ffffff !important;
        font-weight: 500 !important;
        line-height: 1.6 !important;
    }

    /* METRIC CARDS */
    .stMetric {
        background-color: #161b22;
        border-radius: 12px;
        padding: 20px;
        border: 1px solid #30363d;
    }
    [data-testid="stMetricValue"] { color: #58a6ff !important; font-weight: 800; }
    </style>
    """, unsafe_allow_html=True)

# 2026 Failover Model List (to prevent 404s)
# March 2026: Try Flash 3 first, then fallback to stable 2.5 and 2.0 
MODEL_POOL = ["gemini-3-flash-preview", "gemini-3-flash", "gemini-2.5-flash", "gemini-2.0-flash"]

GEMINI_KEY = os.environ.get("GEMINI_KEY") or st.secrets.get("GEMINI_KEY")
client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None

# --- 2. DATA ENGINE ---
@st.cache_data(ttl=300)
def get_stock_data(tickers):
    data = []
    for t in tickers:
        try:
            tk = yf.Ticker(t)
            info = tk.info
            full_name = info.get('longName') or info.get('shortName') or t
            price = tk.fast_info['last_price']
            hist = tk.history(period="1mo")
            mom = ((hist['Close'].iloc[-1] - hist['Close'].iloc[0]) / hist['Close'].iloc[0]) * 100
            data.append({"Ticker": t, "Name": full_name, "Price": price, "Momentum": mom})
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
    st.write("Generating tactical swing plans - for your chosen period - using real-time momentum & AI reasoning.")
    st.warning("⚠️ **Disclaimer:** For educational use only. High risk involved.")
    st.markdown("[🔗 Open Google AI Studio](https://aistudio.google.com/)")

# --- 4. DASHBOARD HEADER ---
st.title("🛸 High-Conviction Execution")

pulse_list = ["NVDA", "BTC-USD", "SOL-USD", "MU", "TSLA"]
pulse_df = get_stock_data(pulse_list)

if not pulse_df.empty:
    ticker_cols = st.columns(len(pulse_df))
    for i, row in pulse_df.iterrows():
        ticker_cols[i].metric(row['Ticker'], f"${row['Price']:.2f}", f"{row['Momentum']:.1f}%")

st.divider()

# --- 5. SWING GENERATOR ---
if st.button("🔥 GENERATE YOUR ACTION PLAN"):
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
                    st.write(f"### {row['Name']}")
                    st.caption(f"Ticker: {row['Ticker']}")
                    st.write(f"**Action:** Buy {shares} Units")
                    st.metric("30D Momentum", f"{row['Momentum']:.1f}%")

            st.divider()
            st.subheader("📑 Your Strategic Roadmap")
            if client:
                portfolio_names = top_picks['Name'].tolist()
                prompt = (f"As Momentum Master trader, provide a week-by-week strategy for {portfolio_names} "
                          f"from {start_d} to {end_d}. Budget is {budget}€. Reference March 2026 catalysts.")
                
                # FAILOVER LOGIC: Tries models until one works 
                response_text = "AI Strategy Generation Failed."
                for model_id in MODEL_POOL:
                    try:
                        res = client.models.generate_content(model=model_id, contents=prompt)
                        response_text = res.text
                        break
                    except Exception as e:
                        continue
                
                st.info(response_text)
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
