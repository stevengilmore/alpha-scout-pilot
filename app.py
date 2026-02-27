import os
import requests
import pandas as pd
import yfinance as yf
import streamlit as st
from google import genai
from google.genai import types
from streamlit_confetti import confetti
from datetime import datetime

# --- 1. CONFIG & HEADERS ---
# Spoofing headers to prevent 403 Forbidden errors
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"}

GEMINI_KEY = os.environ.get("GEMINI_KEY") or st.secrets.get("GEMINI_KEY")
client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None

# Transparent Agents: Programmed for detailed rejections
AGENT_ROLES = {
    "🐂 Opportunistic Scout": "Analyze catalysts & upside. If you reject, explain the price trap. End with VOTE: BUY/NO.",
    "📈 Growth Specialist": "Analyze revenue & momentum. If you reject, explain why growth is priced in. End with VOTE: BUY/NO.",
    "🐻 Risk Auditor": "Identify red flags (debt, SBC, insider selling). You MUST list rejection reasons. End with VOTE: BUY/NO."
}

# --- 2. GLOBAL DATA ENGINES ---
@st.cache_data(ttl=86400)
def get_tickers_by_index(index_name):
    """Fetches global tickers from Wikipedia with header bypass"""
    urls = {
        "S&P 500 (US)": "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
        "Nasdaq-100 (US Tech)": "https://en.wikipedia.org/wiki/Nasdaq-100",
        "EURO STOXX 50 (Europe)": "https://en.wikipedia.org/wiki/EURO_STOXX_50"
    }
    try:
        res = requests.get(urls[index_name], headers=HEADERS, timeout=10)
        tables = pd.read_html(res.text)
        if index_name == "S&P 500 (US)": return tables[0]['Symbol'].str.replace('.', '-', regex=False).tolist()
        elif index_name == "Nasdaq-100 (US Tech)": return tables[4]['Ticker'].tolist()
        else: return tables[3]['Ticker'].tolist() 
    except: return ["AAPL", "NVDA", "ASML.AS", "SAP.DE"]

@st.cache_data(ttl=3600)
def get_market_sentiment():
    """Bypasses CNN block via direct JSON endpoint"""
    try:
        res = requests.get("https://production.dataviz.cnn.io/index/fearandgreed/graphdata", headers=HEADERS, timeout=10)
        data = res.json()['fear_and_greed']
        return {"val": int(data['score']), "text": data['rating'].upper()}
    except: return {"val": 43, "text": "FEAR (FALLBACK)"}

@st.cache_data(ttl=3600)
def get_index_intel(tickers):
    """Ranks by Analyst Score and predicts AI Favorability"""
    data = []
    for t in tickers[:40]: # Scan subset for speed
        try:
            info = yf.Ticker(t).info
            score = info.get('recommendationMean', 5.0)
            curr, target = info.get('currentPrice', 0), info.get('targetMeanPrice', 0)
            if curr > 0 and target > 0:
                upside = ((target - curr) / curr * 100)
                
                # PREDICTIVE AI FAVOR LOGIC
                favor = "LOW"
                rev_growth = info.get('revenueGrowth', 0)
                debt_equity = info.get('debtToEquity', 100)
                if upside > 15 and rev_growth > 0.1 and debt_equity < 150: favor = "HIGH 🔥"
                elif upside > 5 or rev_growth > 0: favor = "MED ⚖️"
                
                data.append({
                    "Ticker": t, "Company": info.get('longName', t),
                    "Price": curr, "Target": target, "Upside %": round(upside, 1),
                    "Score": score, "AI Favor": favor
                })
        except: continue
    # Sorted by Analyst Score (Lowest/Best)
    return pd.DataFrame(data).sort_values("Score", ascending=True).head(12)

# --- 3. UI LAYOUT ---
st.set_page_config(page_title="Alpha Scout Pro", layout="wide")

with st.sidebar:
    st.header("🌐 Global Filters")
    idx = st.selectbox("Select Market Index", ["S&P 500 (US)", "Nasdaq-100 (US Tech)", "EURO STOXX 50 (Europe)"])
    st.info("Ranking: Institutional Conviction (1.0 = Max Buy)")

# Header & Sentiment
sentiment = get_market_sentiment()
c1, c2 = st.columns([3, 1])
with c1:
    st.title(f"🛰️ Command Center: {idx}")
    st.caption(f"Institutional Intelligence Dashboard | {datetime.now().strftime('%Y-%m-%d')}")
with c2:
    st.metric(f"MARKET SENTIMENT: {sentiment['text']}", f"{sentiment['val']}/100")
    st.progress(sentiment['val'] / 100)

st.divider()

# Intel Table & News
col_t, col_n = st.columns([2, 1])
df_intel = get_index_intel(get_tickers_by_index(idx))

with col_t:
    st.subheader(f"📊 {idx} Top Conviction Picks")
    
    # Custom styling for AI Favor
    def color_favor(val):
        if "HIGH" in str(val): return 'background-color: #004d00; color: white'
        if "MED" in str(val): return 'background-color: #333300; color: white'
        return ''

    st.dataframe(
        df_intel.style.map(lambda v: f"color: {'green' if v > 0 else 'red'}", subset=['Upside %'])
        .map(color_favor, subset=['AI Favor'])
        .format({"Price": "${:.2f}", "Target": "${:.2f}", "Upside %": "{:.1f}%", "Score": "{:.2f}"}),
        use_container_width=True, hide_index=True
    )

with col_n:
    st.subheader("📰 Market Feed")
    try:
        top_t = df_intel.iloc[0]['Ticker']
        for item in yf.Ticker(top_t).news[:3]:
            st.write(f"**{item['title']}**")
            st.caption(f"{item['publisher']} | [Link]({item['link']})")
            st.divider()
    except: st.write("Feed currently unavailable.")

st.divider()

# --- 4. SELECTABLE TRANSPARENT AUDIT ---
st.subheader("🤖 AI Committee Deep-Dive")
sel_ticker = st.selectbox("Choose a stock from the convictions list to audit:", options=df_intel['Ticker'].tolist())
row = df_intel[df_intel['Ticker'] == sel_ticker].iloc[0]

if st.button(f"🚀 INITIATE DEEP AUDIT: {row['Company']}"):
    with st.status(f"Council is debating {row['Company']}...") as status:
        votes = 0
        cols = st.columns(3)
        for i, (name, role) in enumerate(AGENT_ROLES.items()):
            with cols[i]:
                try:
                    res = client.models.generate_content(
                        model="gemini-2.0-flash", 
                        contents=f"Deep Audit {row['Company']} ({sel_ticker}). Price: ${row['Price']}. Data: {yf.Ticker(sel_ticker).info}", 
                        config=types.GenerateContentConfig(system_instruction=role)
                    )
                    is_buy = "VOTE: BUY" in res.text.upper()
                    if is_buy: votes += 1
                    st.write(f"### {name}")
                    st.write("✅ **BUY**" if is_buy else "❌ **REJECT**")
                    with st.expander("Show Reasoning"):
                        st.markdown(res.text.replace("VOTE: BUY", "").replace("VOTE: NO", ""))
                except: st.write("Agent Timeout")
        
        if votes >= 2:
            st.success(f"🏆 PASSED COMMITTEE ({votes}/3)")
            if votes == 3: confetti()
        else: st.error(f"🛑 REJECTED BY COMMITTEE ({votes}/3)")
