import streamlit as st
import os
import yfinance as yf
import pandas as pd
from google import genai
from google.genai import types
from datetime import datetime, timedelta

# --- 1. CONFIG & HIGH-CONTRAST STYLING ---
st.set_page_config(page_title="Momentum Master Terminal", layout="wide", page_icon="📈")

st.markdown("""
    <style>
    .main { background-color: #0d1117; color: #ffffff !important; }
    [data-testid="stSidebar"] { background-color: #161b22 !important; border-right: 1px solid #30363d; }
    [data-testid="stSidebar"] .stMarkdown p, [data-testid="stSidebar"] label {
        color: #ffffff !important; font-weight: 700 !important; font-size: 1.1rem !important;
    }
    .stAlert { 
        background-color: #1c2128 !important; 
        color: #ffffff !important; 
        border: 2px solid #58a6ff !important; 
    }
    .stAlert p, .stAlert li, .stAlert h1, .stAlert h2, .stAlert h3, .stAlert div { 
        color: #ffffff !important; font-weight: 500 !important; 
    }
    .stMetric { background-color: #161b22; border-radius: 12px; padding: 20px; border: 1px solid #30363d; }
    [data-testid="stMetricValue"] { color: #58a6ff !important; font-weight: 800; }
    </style>
    """, unsafe_allow_html=True)

MODEL_POOL = ["gemini-2.0-flash", "gemini-1.5-flash"]
GEMINI_KEY = os.environ.get("GEMINI_KEY") or st.secrets.get("GEMINI_KEY")
client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None

# --- 2. THE DATA ENGINE ---
@st.cache_data(ttl=300)
def get_clean_data(tickers):
    data = []
    for t in tickers:
        try:
            tk = yf.Ticker(t)
            info = tk.info
            name = info.get('longName') or info.get('shortName') or t
            price = tk.fast_info['last_price']
            hist = tk.history(period="3mo")
            mom = ((hist['Close'].iloc[-1] - hist['Close'].iloc[0]) / hist['Close'].iloc[0]) * 100
            data.append({"Ticker": t, "Name": name, "Price": round(price, 2), "Momentum": mom})
        except: continue
    return pd.DataFrame(data)

# --- 3. SIDEBAR ---
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/bullish.png")
    st.title("Momentum Master")
    st.divider()
    budget = st.number_input("💵 Trading Budget (€)", min_value=100, value=2500, step=100)
    col_a, col_b = st.columns(2)
    start_d = col_a.date_input("📅 Start Date", datetime.now())
    end_d = col_b.date_input("🏁 End Date", datetime.now() + timedelta(days=30))
    trading_days = (end_d - start_d).days
    st.write(f"⏱️ **Active Window:** {trading_days} Days")
    stock_count = st.slider("🎯 Portfolio Size", 3, 5, 3)
    st.divider()
    st.markdown("### 🚀 Terminal Intent")
    st.write("Dynamic swing plans based on institutional flows and technical momentum.")
    st.warning("⚠️ Disclaimer: For educational/entertainment use only.")
    st.markdown("[🔗 Deep Analysis: Google AI Studio](https://aistudio.google.com/)")

# --- 4. DASHBOARD HEADER ---
st.title(f"🛸 High-Conviction {trading_days}-Day Execution")
pulse_df = get_clean_data(["NVDA", "BTC-USD", "TSLA", "MU"])
if not pulse_df.empty:
    t_cols = st.columns(len(pulse_df))
    for i, row in pulse_df.iterrows():
        t_cols[i].metric(row['Ticker'], f"${row['Price']}", f"{row['Momentum']:.1f}%")

st.divider()

# --- 5. THE SWING GENERATOR ---
if st.button("🔥 GENERATE TACTICAL ACTION PLAN"):
    pool = ["NVDA", "MU", "APP", "TSLA", "PLTR", "SOL-USD", "BTC-USD", "MSTR", "AMZN", "LITE"]
    
    with st.spinner(f"Locking {trading_days}-day trajectories..."):
        full_pool = get_clean_data(pool)
        if not full_pool.empty:
            top_picks = full_pool.sort_values("Momentum", ascending=False).head(stock_count)
            
            st.subheader(f"🥇 Recommended {stock_count}-Stock Portfolio")
            b_per_stock = budget / stock_count
            cols = st.columns(len(top_picks))
            
            ai_data_context = ""
            for i, (_, row) in enumerate(top_picks.iterrows()):
                with cols[i]:
                    shares = round(b_per_stock / row['Price'], 2)
                    st.write(f"### {row['Name']}")
                    st.write(f"**Buy:** {shares} Units @ **${row['Price']}**")
                    st.metric("Recent Momentum", f"{row['Momentum']:.1f}%")
                    ai_data_context += f"- {row['Name']} ({row['Ticker']}): Market Price ${row['Price']}\n"

            st.divider()
            st.subheader(f"📑 {trading_days}-Day Strategic Roadmap")
            st.caption("✅ Data Verified: Using Live Exchange Prices")
            
            if client:
                prompt = (
                    f"You are the Momentum Master trader. Plan a {trading_days}-day strategy for these specific assets at these exact prices:\n"
                    f"{ai_data_context}\n"
                    f"MANDATORY: Do not mention any other prices. Use the current market prices provided. "
                    f"Timeline: {start_d} to {end_d}. Reference March 2026 catalysts (Nvidia Blackwell GTC, Tesla EU expansion). "
                    f"Plan: Divide into Entry, Growth, and Exit phases based on the {trading_days} day length."
                )
                
                res_text = "Generation failed. Try again."
                for m_id in MODEL_POOL:
                    try:
                        response = client.models.generate_content(model=m_id, contents=prompt)
                        res_text = response.text
                        break
                    except: continue
                
                st.info(res_text)
            else: st.error("Missing Gemini API Key.")

else:
    st.write(f"### 🐂 Momentum Strategy: {trading_days} Day Outlook")
    st.write("This system uses 'Relative Strength'—identifying assets with the highest institutional buying pressure to map your roadmap.")
    st.image("https://img.icons8.com/fluency/200/combo-chart.png")
