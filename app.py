import os
import requests
import pandas as pd
import yfinance as yf
import streamlit as st
from google import genai
from google.genai import types
from streamlit_confetti import confetti
from datetime import datetime

# --- 1. SETUP & BROWSER SPOOFING ---
# Wikipedia and CNN require a User-Agent to avoid 403 Forbidden errors
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
}

GEMINI_KEY = os.environ.get("GEMINI_KEY") or st.secrets.get("GEMINI_KEY")
client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None

AGENT_ROLES = {
    "🐂 Opportunistic Scout": "Prioritize high-upside targets and value. End with VOTE: BUY/NO.",
    "📈 Growth Specialist": "Look for momentum and revenue growth. End with VOTE: BUY/NO.",
    "🐻 Risk Auditor": "Veto based on balance sheet health and debt. End with VOTE: BUY/NO."
}

# --- 2. DATA ENGINES WITH 403 FIXES ---
@st.cache_data(ttl=86400)
def get_sp500_tickers():
    """Scrapes Wikipedia with headers to avoid 403 errors"""
    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        df = pd.read_html(response.text)[0]
        return df['Symbol'].str.replace('.', '-', regex=False).tolist()
    except Exception as e:
        st.error(f"S&P 500 Scrape Failed: {e}")
        return ["AAPL", "NVDA", "MSFT", "AMZN", "GOOGL", "META", "TSLA"]

@st.cache_data(ttl=3600)
def get_fear_and_greed():
    """Fetches CNN data via direct JSON endpoint to bypass scraping blocks"""
    url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        data = response.json()
        val = int(data['fear_and_greed']['score'])
        rating = data['fear_and_greed']['rating'].upper()
        return {"val": val, "text": rating}
    except Exception as e:
        return {"val": 43, "text": "FEAR (FALLBACK)"}

@st.cache_data(ttl=3600)
def get_top_12_analysts():
    """Scans S&P 500 for strongest buy signals"""
    all_tickers = get_sp500_tickers()
    sample = all_tickers[:45] # Optimized sample to avoid timeouts
    data = []
    for t in sample:
        try:
            info = yf.Ticker(t).info
            rating = info.get('recommendationMean', 5.0)
            if rating <= 2.2: # Strong Buy intensity
                curr, target = info.get('currentPrice', 0), info.get('targetMeanPrice', 0)
                upside = ((target - curr) / curr * 100) if curr > 0 else 0
                data.append({
                    "Ticker": t, "Company": info.get('longName', t),
                    "Price": curr, "Target": target, "Upside %": round(upside, 1),
                    "Score": rating
                })
        except: continue
    return pd.DataFrame(data).sort_values("Score").head(12)

# --- 3. UI LAYOUT ---
st.set_page_config(page_title="Alpha Scout Pro", layout="wide")

# Header & Sentiment
sentiment = get_fear_and_greed()
c1, c2 = st.columns([3, 1])
with c1:
    st.title("🛰️ Alpha Scout: Command Center")
    st.caption(f"S&P 500 Institutional Intelligence | {datetime.now().strftime('%Y-%m-%d')}")
with c2:
    st.metric(f"SENTIMENT: {sentiment['text']}", sentiment['val'])
    st.progress(sentiment['val'] / 100)

st.divider()

# Analyst Intel & News
col_table, col_news = st.columns([2, 1])
df_intel = get_top_12_analysts()

with col_table:
    st.subheader("📊 S&P 500 Top Conviction Picks")
    st.dataframe(
        df_intel.style.map(lambda v: f"color: {'green' if v > 0 else 'red'}", subset=['Upside %'])
        .format({"Price": "${:.2f}", "Target": "${:.2f}", "Upside %": "{:.1f}%"}),
        use_container_width=True, hide_index=True
    )

with col_news:
    st.subheader("📰 Market Feed")
    try:
        top_ticker = df_intel.iloc[0]['Ticker']
        news = yf.Ticker(top_ticker).news[:3]
        for item in news:
            st.write(f"**{item['title']}**")
            st.caption(f"{item['publisher']} | [Link]({item['link']})")
    except: st.write("No news available for top pick.")

st.divider()

# Committee Audit
st.subheader("🤖 AI Committee Audit")
top_t, top_n = df_intel.iloc[0]['Ticker'], df_intel.iloc[0]['Company']

if st.button(f"🚀 AUDIT {top_n}"):
    with st.status(f"Council is debating {top_n}...") as status:
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
                    with st.expander("Reasoning"):
                        st.write(res.text.split("VOTE:")[0])
                except: st.write("Agent Error")
        
        if votes >= 2:
            st.success(f"🏆 {top_n} PASSED COMMITTEE ({votes}/3)")
            if votes == 3: confetti()
        else:
            st.error(f"🛑 {top_n} REJECTED ({votes}/3)")
