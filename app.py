import os
import sys
import streamlit as st
import yfinance as yf
import pandas as pd
from fear_and_greed import FearGreedIndex
from google import genai
from google.genai import types
from streamlit_confetti import confetti

# --- 1. SETUP & AGENTS ---
GEMINI_KEY = os.environ.get("GEMINI_KEY") or st.secrets.get("GEMINI_KEY")
client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None

AGENT_ROLES = {
    "🐂 Opportunistic Scout": "Prioritize high-upside targets and P/E compression. End with VOTE: BUY/NO.",
    "📈 Growth Specialist": "Look for momentum and revenue growth. End with VOTE: BUY/NO.",
    "🐻 Risk Auditor": "Veto based on balance sheet health and debt. End with VOTE: BUY/NO."
}

# --- 2. DYNAMIC COMMAND CENTER ENGINES ---
@st.cache_data(ttl=86400)
def get_sp500_tickers():
    """Scrapes Wikipedia for the current S&P 500 list"""
    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
    return pd.read_html(url)[0]['Symbol'].str.replace('.', '-', regex=False).tolist()

@st.cache_data(ttl=3600)
def get_market_intelligence():
    """Fetches F&G Index and Top 12 Analyst Ratings"""
    # 1. Fear & Greed
    try:
        fng = FearGreedIndex().get()
        sentiment = {"val": int(fng.value), "text": fng.description.upper()}
    except:
        sentiment = {"val": 43, "text": "FEAR"} # Current 2026 default

    # 2. S&P 500 Top 12 Screener
    all_tickers = get_sp500_tickers()
    sample = all_tickers[:40] # Limited for demo speed
    data = []
    for t in sample:
        try:
            info = yf.Ticker(t).info
            rating = info.get('recommendationMean', 5.0)
            if rating <= 2.2: # Strong Buy threshold
                curr, target = info.get('currentPrice', 0), info.get('targetMeanPrice', 0)
                upside = ((target - curr) / curr * 100) if curr > 0 else 0
                data.append({
                    "Ticker": t, "Company": info.get('longName', t),
                    "Price": curr, "Target": target, "Upside %": round(upside, 1),
                    "Analyst Score": rating
                })
        except: continue
    
    df = pd.DataFrame(data).sort_values("Analyst Score").head(12)
    return sentiment, df

# --- 3. UI LAYOUT: COMMAND CENTER ---
st.set_page_config(page_title="Alpha Scout Pro", layout="wide")

sentiment, df_intel = get_market_intelligence()

# ROW 1: Header & Fear/Greed
c1, c2 = st.columns([3, 1])
with c1:
    st.title("🛰️ Alpha Scout: Command Center")
    st.caption("S&P 500 Institutional Intelligence Dashboard")
with c2:
    st.metric(f"FEAR & GREED: {sentiment['text']}", sentiment['val'])
    st.progress(sentiment['val'] / 100)

st.divider()

# ROW 2: Intel Table & News
col_table, col_news = st.columns([2, 1])

with col_table:
    st.subheader("📊 S&P 500: Top 12 Analyst Picks")
    st.dataframe(
        df_intel.style.map(lambda v: f"color: {'green' if v > 0 else 'red'}", subset=['Upside %'])
        .format({"Price": "${:.2f}", "Target": "${:.2f}", "Upside %": "{:.1f}%"}),
        use_container_width=True, hide_index=True
    )

with col_news:
    st.subheader("📰 Market Feed")
    try:
        news = yf.Ticker(df_intel.iloc[0]['Ticker']).news[:3]
        for item in news:
            st.write(f"**{item['title']}**")
            st.caption(f"{item['publisher']} | [Link]({item['link']})")
    except: st.write("No live news available.")

st.divider()

# ROW 3: AI COMMITTEE
st.subheader("🤖 AI Investment Committee Audit")
top_t, top_n = df_intel.iloc[0]['Ticker'], df_intel.iloc[0]['Company']

if st.button(f"🚀 AUDIT {top_n} ({top_t})"):
    with st.status("Agents are debating...") as status:
        votes = 0
        cols = st.columns(3)
        for i, (name, role) in enumerate(AGENT_ROLES.items()):
            with cols[i]:
                try:
                    res = client.models.generate_content(
                        model="gemini-2.0-flash", 
                        contents=f"Audit {top_n}. Current Price: {df_intel.iloc[0]['Price']}", 
                        config=types.GenerateContentConfig(system_instruction=role)
                    )
                    is_buy = "VOTE: BUY" in res.text.upper()
                    if is_buy: votes += 1
                    st.write(f"**{name}**")
                    st.write("✅ BUY" if is_buy else "❌ NO")
                except: st.write("Agent Error")
        
        if votes >= 2:
            st.success(f"🏆 {top_n} PASSED COMMITTEE ({votes}/3)")
            if votes == 3: confetti() # Unanimous Celebration
        else: st.error(f"🛑 {top_n} REJECTED ({votes}/3)")
