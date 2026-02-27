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
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"}
GEMINI_KEY = os.environ.get("GEMINI_KEY") or st.secrets.get("GEMINI_KEY")
client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None

AGENT_ROLES = {
    "🐂 Opportunistic Scout": "Analyze catalysts & upside. End with VOTE: BUY/NO.",
    "📈 Growth Specialist": "Analyze revenue & momentum. End with VOTE: BUY/NO.",
    "🐻 Risk Auditor": "Identify red flags (debt, SBC, insider selling). End with VOTE: BUY/NO."
}

# --- 2. MULTI-INDEX DATA ENGINE ---
@st.cache_data(ttl=86400)
def get_tickers(index_name):
    urls = {
        "S&P 500": "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
        "Nasdaq-100": "https://en.wikipedia.org/wiki/Nasdaq-100",
        "DAX": "https://en.wikipedia.org/wiki/DAX",
        "FTSE 100": "https://en.wikipedia.org/wiki/FTSE_100_Index"
    }
    try:
        res = requests.get(urls[index_name], headers=HEADERS, timeout=10)
        tables = pd.read_html(res.text)
        if index_name == "S&P 500": return tables[0]['Symbol'].str.replace('.', '-', regex=False).tolist()
        if index_name == "Nasdaq-100": return tables[4]['Ticker'].tolist()
        if index_name == "DAX": return tables[4]['Ticker'].tolist()
        if index_name == "FTSE 100": return tables[4]['EPIC'].apply(lambda x: f"{x}.L").tolist()
    except: return []

@st.cache_data(ttl=3600)
def get_intel(tickers, limit=15):
    data = []
    for t in tickers[:limit]:
        try:
            info = yf.Ticker(t).info
            score = info.get('recommendationMean', 5.0)
            curr, target = info.get('currentPrice', 0), info.get('targetMeanPrice', 0)
            if curr > 0 and target > 0:
                upside = ((target - curr) / curr * 100)
                favor = "HIGH 🔥" if upside > 15 and score < 2.0 else "MED ⚖️" if upside > 5 else "LOW"
                data.append({
                    "Ticker": t, "Company": info.get('longName', t),
                    "Price": curr, "Upside %": round(upside, 1),
                    "Score": score, "AI Favor": favor
                })
        except: continue
    return pd.DataFrame(data).sort_values("Score", ascending=True).head(8)

# --- 3. UI LAYOUT ---
st.set_page_config(page_title="Alpha Scout Command", layout="wide")

# Market Sentiment Header
try:
    res = requests.get("https://production.dataviz.cnn.io/index/fearandgreed/graphdata", headers=HEADERS, timeout=10)
    fng = res.json()['fear_and_greed']
    val, text = int(fng['score']), fng['rating'].upper()
except: val, text = 43, "FEAR"

c1, c2 = st.columns([3, 1])
with c1:
    st.title("🛰️ Alpha Scout: Global Command")
    st.caption(f"Multi-Index Institutional Intelligence | {datetime.now().strftime('%Y-%m-%d')}")
with c2:
    st.metric(f"SENTIMENT: {text}", f"{val}/100")
    st.progress(val / 100)

st.divider()

# --- 4. THE QUAD GRID ---
def style_table(df):
    return df.style.map(lambda v: f"color: {'green' if v > 0 else 'red'}", subset=['Upside %']).map(
        lambda v: 'background-color: #004d00' if "HIGH" in str(v) else ('background-color: #333300' if "MED" in str(v) else ''),
        subset=['AI Favor']
    ).format({"Price": "${:.2f}", "Upside %": "{:.1f}%", "Score": "{:.2f}"})

row1_col1, row1_col2 = st.columns(2)
row2_col1, row2_col2 = st.columns(2)

indices = [("S&P 500", row1_col1), ("Nasdaq-100", row1_col2), ("DAX", row2_col1), ("FTSE 100", row2_col2)]
all_top_tickers = []

for idx_name, col in indices:
    with col:
        st.subheader(f"🏛️ {idx_name}")
        tickers = get_tickers(idx_name)
        df = get_intel(tickers)
        if not df.empty:
            st.dataframe(style_table(df), use_container_width=True, hide_index=True)
            all_top_tickers.extend(df.to_dict('records'))
        else:
            st.write("Data currently loading...")

st.divider()

# --- 5. SELECTABLE AUDIT ---
st.subheader("🤖 AI Committee Deep-Dive")
if all_top_tickers:
    ticker_map = {f"{r['Ticker']} - {r['Company']}": r for r in all_top_tickers}
    sel_label = st.selectbox("Select any stock from the grid to audit:", options=list(ticker_map.keys()))
    selected_data = ticker_map[sel_label]

    if st.button(f"🚀 AUDIT {selected_data['Company']}"):
        with st.status(f"Council is debating {selected_data['Company']}...") as status:
            votes = 0
            cols = st.columns(3)
            for i, (name, role) in enumerate(AGENT_ROLES.items()):
                with cols[i]:
                    try:
                        res = client.models.generate_content(
                            model="gemini-2.0-flash", 
                            contents=f"Audit {selected_data['Company']} ({selected_data['Ticker']}). Price: {selected_data['Price']}. Data: {yf.Ticker(selected_data['Ticker']).info}", 
                            config=types.GenerateContentConfig(system_instruction=role)
                        )
                        is_buy = "VOTE: BUY" in res.text.upper()
                        if is_buy: votes += 1
                        st.write(f"### {name}")
                        st.write("✅ **BUY**" if is_buy else "❌ **REJECT**")
                        with st.expander("Reasoning"):
                            st.markdown(res.text.replace("VOTE: BUY", "").replace("VOTE: NO", ""))
                    except: st.write("Agent Timeout")
            
            if votes >= 2:
                st.success(f"🏆 PASSED ({votes}/3)"); 
                if votes == 3: confetti()
            else: st.error(f"🛑 REJECTED ({votes}/3)")
