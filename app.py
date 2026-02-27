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
    "🐻 Risk Auditor": "Identify red flags (debt, SBC, insider selling). You MUST list rejection reasons. End with VOTE: BUY/NO."
}

# --- 2. DATA ENGINES ---
@st.cache_data(ttl=86400)
def get_tickers(index_name):
    """Fetches global tickers from Wikipedia with browser spoofing."""
    urls = {
        "S&P 500": "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
        "Nasdaq-100": "https://en.wikipedia.org/wiki/Nasdaq-100",
        "DAX": "https://en.wikipedia.org/wiki/DAX",
        "FTSE 100": "https://en.wikipedia.org/wiki/FTSE_100_Index"
    }
    try:
        res = requests.get(urls[index_name], headers=HEADERS, timeout=10)
        tables = pd.read_html(res.text)
        if index_name == "S&P 500": 
            return tables[0]['Symbol'].str.replace('.', '-', regex=False).tolist()
        if index_name == "Nasdaq-100": 
            return tables[4]['Ticker'].tolist()
        if index_name == "DAX": 
            # DAX table usually has Ticker in 3rd or 4th column
            return tables[4]['Ticker'].tolist()
        if index_name == "FTSE 100": 
            # FTSE tickers need the .L suffix for Yahoo Finance
            return [f"{t}.L" for t in tables[4]['Ticker'].tolist()]
    except: return []

@st.cache_data(ttl=3600)
def get_intel(tickers, limit=12):
    """Ranks by Analyst Score and adds AI Favorability prediction."""
    data = []
    for t in tickers[:35]: # Sample subset for efficiency
        try:
            info = yf.Ticker(t).info
            score = info.get('recommendationMean', 5.0)
            curr, target = info.get('currentPrice', 0), info.get('targetMeanPrice', 0)
            if curr > 0 and target > 0:
                upside = ((target - curr) / curr * 100)
                # AI Favorability: Predictive heuristic based on agent logic
                favor = "HIGH 🔥" if upside > 15 and score < 1.8 else "MED ⚖️" if upside > 5 else "LOW"
                data.append({
                    "Ticker": t, "Company": info.get('longName', t),
                    "Price": curr, "Upside %": round(upside, 1),
                    "Score": score, "AI Favor": favor
                })
        except: continue
    return pd.DataFrame(data).sort_values("Score", ascending=True).head(8)

# --- 3. UI LAYOUT ---
st.set_page_config(page_title="Alpha Scout Command", layout="wide")

# Market Sentiment & Header
try:
    res = requests.get("https://production.dataviz.cnn.io/index/fearandgreed/graphdata", headers=HEADERS, timeout=10)
    fng = res.json()['fear_and_greed']
    val, text = int(fng['score']), fng['rating'].upper()
except: val, text = 43, "FEAR"

c1, c2 = st.columns([3, 1])
with c1:
    st.title("🛰️ Alpha Scout: Global Command")
    st.caption(f"Multi-Index Intelligence | {datetime.now().strftime('%Y-%m-%d %H:%M')}")
with c2:
    st.metric(f"SENTIMENT: {text}", f"{val}/100")
    st.progress(val / 100)

st.divider()

# --- 4. THE GLOBAL QUAD-GRID ---
def style_table(df):
    return df.style.map(lambda v: f"color: {'green' if v > 0 else 'red'}", subset=['Upside %']).map(
        lambda v: 'background-color: #004d00; color: white' if "HIGH" in str(v) else ('background-color: #333300; color: white' if "MED" in str(v) else ''),
        subset=['AI Favor']
    ).format({"Price": "${:.2f}", "Upside %": "{:.1f}%", "Score": "{:.2f}"})

row1_col1, row1_col2 = st.columns(2)
row2_col1, row2_col2 = st.columns(2)

indices = [("S&P 500", row1_col1), ("Nasdaq-100", row1_col2), ("DAX", row2_col1), ("FTSE 100", row2_col2)]
all_top_tickers = []

with st.spinner("Aggregating Global Conviction Data..."):
    for idx_name, col in indices:
        with col:
            st.subheader(f"🏛️ {idx_name}")
            tickers = get_tickers(idx_name)
            df = get_intel(tickers)
            if not df.empty:
                st.dataframe(style_table(df), use_container_width=True, hide_index=True)
                all_top_tickers.extend(df.to_dict('records'))
            else: st.write("Awaiting market data...")

st.divider()

# --- 5. SIMULTANEOUS AI COMMITTEE AUDIT ---
st.subheader("🤖 AI Committee Rapid Audit")
if all_top_tickers:
    ticker_map = {f"{r['Ticker']} - {r['Company']}": r for r in all_top_tickers}
    sel_label = st.selectbox("Select a stock from the grid to audit:", options=list(ticker_map.keys()))
    selected_data = ticker_map[sel_label]

    if st.button(f"🚀 INITIATE RAPID AUDIT: {selected_data['Company']}"):
        # IMAGE: 
        with st.status(f"Council is debating {selected_data['Company']} simultaneously...") as status:
            
            # Helper for simultaneous execution
            def get_agent_response(name, role):
                try:
                    res = client.models.generate_content(
                        model="gemini-2.0-flash", 
                        contents=f"Audit {selected_data['Company']} ({selected_data['Ticker']}). Price: {selected_data['Price']}. Data: {yf.Ticker(selected_data['Ticker']).info}", 
                        config=types.GenerateContentConfig(system_instruction=role)
                    )
                    return name, res.text
                except Exception as e: return name, f"Error: {e}"

            # Parallel Execution (ThreadPoolExecutor)
            votes = 0
            agent_outputs = {}
            with concurrent.futures.ThreadPoolExecutor() as executor:
                futures = {executor.submit(get_agent_response, n, r): n for n, r in AGENT_ROLES.items()}
                for future in concurrent.futures.as_completed(futures):
                    name, text = future.result()
                    agent_outputs[name] = text
                    if "VOTE: BUY" in text.upper(): votes += 1
            
            # UI Render
            cols = st.columns(3)
            for i, (name, text) in enumerate(agent_outputs.items()):
                with cols[i]:
                    st.write(f"### {name}")
                    st.write("✅ **BUY**" if "VOTE: BUY" in text.upper() else "❌ **REJECT**")
                    with st.expander("Show Detailed Reasoning"):
                        st.markdown(text.replace("VOTE: BUY", "").replace("VOTE: NO", ""))
            
            if votes >= 2:
                st.success(f"🏆 PASSED COMMITTEE ({votes}/3)")
                if votes == 3: confetti()
            else: st.error(f"🛑 REJECTED BY COMMITTEE ({votes}/3)")
            status.update(label="Audit Complete!", state="complete")
