import streamlit as st
import os
import requests
import yfinance as yf
import pandas as pd
from google import genai
from datetime import datetime, timedelta

# --- 1. CONFIG & ULTRA-READABLE STYLING ---
st.set_page_config(page_title="Momentum Master Terminal", layout="wide", page_icon="📈")

st.markdown("""
    <style>
    .main { background-color: #0d1117; color: #ffffff !important; }
    [data-testid="stSidebar"] { background-color: #161b22 !important; border-right: 1px solid #30363d; }
    [data-testid="stSidebar"] .stMarkdown p, [data-testid="stSidebar"] label {
        color: #ffffff !important; font-weight: 700 !important; font-size: 1.1rem !important;
    }
    .stAlert { background-color: #1c2128 !important; color: #ffffff !important; border: 2px solid #58a6ff !important; }
    .stAlert p, .stAlert li, .stAlert span, .stAlert div { color: #ffffff !important; font-weight: 500 !important; }
    .stMetric { background-color: #161b22; border-radius: 12px; padding: 20px; border: 1px solid #30363d; }
    [data-testid="stMetricValue"] { color: #58a6ff !important; font-weight: 800; }
    </style>
    """, unsafe_allow_html=True)

# 2026 STABLE MODEL POOL
MODEL_POOL = ["gemini-3-flash", "gemini-2.5-flash"]

GEMINI_KEY = os.environ.get("GEMINI_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None

# --- 2. THE TOOLS ---
def send_telegram(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID: return False
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": f"🛰️ *MOMENTUM MASTER BRIEFING*\n---\n{message}", "parse_mode": "Markdown"}
    try:
        requests.post(url, data=payload, timeout=10)
        return True
    except: return False

@st.cache_data(ttl=300)
def get_clean_data(tickers):
    data = []
    for t in tickers:
        try:
            tk = yf.Ticker(t)
            price = tk.fast_info['last_price']
            name = tk.info.get('longName') or t
            hist = tk.history(period="3mo")
            # FIXED SYNTAX BELOW
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
    start_d = col_a.date_input("📅 Start", datetime.now())
    end_d = col_b.date_input("🏁 End", datetime.now() + timedelta(days=39))
    trading_days = (end_d - start_d).days
    st.write(f"⏱️ **Active Window:** {trading_days} Days")
    stock_count = st.slider("🎯 Portfolio Size", 3, 5, 3)
    st.divider()
    st.info("💡 Strategic Note: March 2026 focus is on GPU infrastructure and energy resilience.")
    st.markdown("[🔗 AI Studio](https://aistudio.google.com/)")

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
    
    with st.spinner(f"Analyzing {trading_days}-day trajectories..."):
        full_pool = get_clean_data(pool)
        if not full_pool.empty:
            top_picks = full_pool.sort_values("Momentum", ascending=False).head(stock_count)
            
            st.subheader(f"🥇 Recommended {stock_count}-Stock Portfolio")
            b_per_stock = budget / stock_count
            cols = st.columns(len(top_picks))
            
            ai_data_context = ""
            telegram_summary = ""
            for i, (_, row) in enumerate(top_picks.iterrows()):
                with cols[i]:
                    shares = round(b_per_stock / row['Price'], 2)
                    st.write(f"### {row['Name']}")
                    st.write(f"**Buy:** {shares} Units @ **${row['Price']}**")
                    st.metric("Momentum Score", f"{row['Momentum']:.1f}%")
                    ai_data_context += f"- {row['Name']} ({row['Ticker']}): Market Price ${row['Price']}\n"
                    telegram_summary += f"🟢 {row['Ticker']}: {shares} units @ ${row['Price']}\n"

            st.divider()
            st.subheader(f"📑 {trading_days}-Day Strategic Roadmap")
            
            if client:
                prompt = (
                    f"You are the Momentum Master trader. Plan a {trading_days}-day strategy for today, March 4, 2026.\n"
                    f"PORTFOLIO DATA (MANDATORY PRICES):\n{ai_data_context}\n"
                    f"WORLD SITUATION: Energy supply volatility and trade tariffs impacting tech. Plan defensively.\n"
                    f"PLAN: Roadmap from {start_d} to {end_d}. Include Entry, Mid-Window catalysts, and Exit phases."
                )
                
                res_text = "AI Roadmap Generation Failed."
                for m_id in MODEL_POOL:
                    try:
                        response = client.models.generate_content(model=m_id, contents=prompt)
                        res_text = response.text
                        if res_text: break
                    except: continue
                
                st.info(res_text)
                
                full_msg = f"📅 *Window:* {trading_days} Days\n💰 *Budget:* {budget}€\n\n*PORTFOLIO:*\n{telegram_summary}\n*ROADMAP:*\n{res_text}"
                send_telegram(full_msg)
            else: st.error("Missing Gemini API Key.")

else:
    st.write(f"### 🐂 Momentum Strategy: {trading_days} Day Outlook")
    st.write("We capture the 'meat' of moves around technology milestones and institutional rotations.")
    st.image("https://img.icons8.com/fluency/200/combo-chart.png")
