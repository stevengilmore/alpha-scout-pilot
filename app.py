import os
import requests
import pandas as pd
import yfinance as yf
import streamlit as st
import concurrent.futures
from google import genai
from google.genai import types
from streamlit_confetti import confetti
from datetime import datetime

# --- 1. CONFIG & HEADERS ---
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"}
GEMINI_KEY = os.environ.get("GEMINI_KEY") or st.secrets.get("GEMINI_KEY")
client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None

AGENT_ROLES = {
    "🐂 Opportunistic Scout": "Analyze catalysts & upside. Explain logic before voting. End with VOTE: BUY/NO.",
    "📈 Growth Specialist": "Analyze revenue & momentum. Explain logic before voting. End with VOTE: BUY/NO.",
    "🐻 Risk Auditor": "Identify red flags (debt, SBC, insider selling). List rejection reasons. End with VOTE: BUY/NO."
}

# --- 2. DATA ENGINES ---
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
        if index_name == "FTSE 100": return [f"{t}.L" for t in tables[4]['Ticker'].tolist()]
    except: return []

@st.cache_data(ttl=3600)
def get_intel(tickers, limit=12):
    data = []
    # If no tickers, return empty DF immediately
    if not tickers:
        return pd.DataFrame(columns=["Ticker", "Company", "Price", "Upside %", "Score", "AI Favor"])
    
    for t in tickers[:35]: 
        try:
            info = yf.Ticker(t).info
            score = info.get('recommendationMean', 5.0)
            curr, target = info.get('currentPrice', 0), info.get('targetMeanPrice', 0)
            if curr > 0 and target > 0:
                upside = ((target - curr) / curr * 100)
                favor = "HIGH 🔥" if upside > 15 and score < 1.8 else "MED ⚖️" if upside > 5 else "LOW"
                data.append({
                    "Ticker": t, "Company": info.get('longName', t),
                    "Price": curr, "Upside %": round(upside, 1),
                    "Score": score, "AI Favor": favor
                })
        except: continue
    
    # --- FIX: SAFE SORTING ---
    if not data:
        return pd.DataFrame(columns=["Ticker", "Company", "Price", "Upside %", "Score", "AI Favor"])
    
    return pd.DataFrame(data).sort_values("Score", ascending=True).head(8)

# --- 3. UI LAYOUT ---
st.set_page_config(page_title="Alpha Scout Pro", layout="wide")

# Sentiment Header
try:
    res = requests.get("https://production.dataviz.cnn.io/index/fearandgreed/graphdata", headers=HEADERS, timeout=10).json()
    val, text = int(res['fear_and_greed']['score']), res['fear_and_greed']['rating'].upper()
except: val, text = 43, "FEAR"

c1, c2 = st.columns([3, 1])
with c1:
    st.title("🛰️ Alpha Scout: Global Command")
    st.caption(f"Multi-Index Intelligence | {datetime.now().strftime('%Y-%m-%d')}")
with c2:
    st.metric(f"SENTIMENT: {text}", f"{val}/100")
    st.progress(val / 100)

st.divider()

# --- 4. THE GLOBAL QUAD-GRID ---
row1_col1, row1_col2 = st.columns(2)
row2_col1, row2_col2 = st.columns(2)
indices = [("S&P 500", row1_col1), ("Nasdaq-100", row1_col2), ("DAX", row2_col1), ("FTSE 100", row2_col2)]
all_top_tickers = []

with st.spinner("Fetching global market data..."):
    for idx_name, col in indices:
        with col:
            st.subheader(f"🏛️ {idx_name}")
            df = get_intel(get_tickers(idx_name))
            if not df.empty:
                st.dataframe(df.style.map(lambda v: f"color: {'green' if v > 0 else 'red'}", subset=['Upside %']), use_container_width=True, hide_index=True)
                all_top_tickers.extend(df.to_dict('records'))
            else:
                st.info(f"No active 'Buy' signals found for {idx_name} right now.")

st.divider()

# --- 5. AUTO-LOADED AI TOP PICK ---
st.subheader("🌟 AI Top Pick for Today")
high_favor_list = [t for t in all_top_tickers if "HIGH" in str(t['AI Favor'])]

if high_favor_list and client:
    top_candidate = max(high_favor_list, key=lambda x: x['Upside %'])
    
    @st.cache_data(ttl=3600)
    def get_one_sentence_pick(ticker, name):
        try:
            res = client.models.generate_content(
                model="gemini-2.0-flash", 
                contents=f"In 15 words or less, why is {name} ({ticker}) the best stock to watch today?"
            )
            return res.text.strip()
        except: return "Strongest combination of institutional conviction and market upside."

    reason = get_one_sentence_pick(top_candidate['Ticker'], top_candidate['Company'])
    st.success(f"**{top_candidate['Company']} ({top_candidate['Ticker']})** — {reason}")
else:
    st.write("AI is currently scanning for a high-conviction winner...")

st.divider()

# --- 6. SIMULTANEOUS AI COMMITTEE AUDIT ---
st.subheader("🤖 AI Committee Rapid Audit")
if all_top_tickers:
    ticker_map = {f"{r['Ticker']} - {r['Company']}": r for r in all_top_tickers}
    sel_label = st.selectbox("Select a stock for a Deep Audit:", options=list(ticker_map.keys()))
    selected_data = ticker_map[sel_label]

    if st.button(f"🚀 INITIATE RAPID AUDIT: {selected_data['Company']}"):
        with st.status(f"Simultaneous debate in progress...") as status:
            def get_agent_response(name, role):
                res = client.models.generate_content(
                    model="gemini-2.0-flash", 
                    contents=f"Audit {selected_data['Company']} ({selected_data['Ticker']}). Price: {selected_data['Price']}. Data: {yf.Ticker(selected_data['Ticker']).info}", 
                    config=types.GenerateContentConfig(system_instruction=role)
                )
                return name, res.text

            agent_outputs = {}
            with concurrent.futures.ThreadPoolExecutor() as executor:
                futures = {executor.submit(get_agent_response, n, r): n for n, r in AGENT_ROLES.items()}
                for f in concurrent.futures.as_completed(futures):
                    name, text = f.result()
                    agent_outputs[name] = text
            
            cols = st.columns(3)
            votes = 0
            for i, (name, text) in enumerate(agent_outputs.items()):
                with cols[i]:
                    st.write(f"### {name}")
                    is_buy = "VOTE: BUY" in text.upper()
                    if is_buy: votes += 1
                    st.write("✅ **BUY**" if is_buy else "❌ **REJECT**")
                    with st.expander("Show Reasoning"): st.markdown(text.replace("VOTE: BUY", "").replace("VOTE: NO", ""))
            
            if votes >= 2:
                st.success(f"🏆 PASSED ({votes}/3)")
                if votes == 3: confetti()
            else: st.error(f"🛑 REJECTED ({votes}/3)")
