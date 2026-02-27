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
session = requests.Session()
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"}
GEMINI_KEY = os.environ.get("GEMINI_KEY") or st.secrets.get("GEMINI_KEY")
client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None

AGENT_ROLES = {
    "🐂 Opportunistic Scout": "Analyze catalysts & upside. Explain logic before voting. End with VOTE: BUY/NO.",
    "📈 Growth Specialist": "Analyze revenue & momentum. Explain logic before voting. End with VOTE: BUY/NO.",
    "🐻 Risk Auditor": "Identify red flags (debt, SBC, insider selling). List rejection reasons. End with VOTE: BUY/NO."
}

# --- 2. FAST DATA ENGINES ---
@st.cache_data(ttl=86400)
def get_tickers(index_name):
    urls = {
        "S&P 500": "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
        "Nasdaq-100": "https://en.wikipedia.org/wiki/Nasdaq-100",
        "DAX": "https://en.wikipedia.org/wiki/DAX",
        "FTSE 100": "https://en.wikipedia.org/wiki/FTSE_100_Index"
    }
    try:
        res = session.get(urls[index_name], headers=HEADERS, timeout=10)
        tables = pd.read_html(res.text)
        if index_name == "S&P 500": return tables[0]['Symbol'].str.replace('.', '-', regex=False).tolist()
        if index_name == "Nasdaq-100": return tables[4]['Ticker'].tolist()
        if index_name == "DAX": return tables[4]['Ticker'].tolist()
        if index_name == "FTSE 100": return [f"{t}.L" for t in tables[4]['Ticker'].tolist()]
    except: return []

@st.cache_data(ttl=3600)
def get_intel(tickers):
    data = []
    # Optimization: Scanning 12 keeps the 'snappy' feel on Render
    for t in tickers[:12]: 
        try:
            info = yf.Ticker(t).info
            score = info.get('recommendationMean', 5.0)
            curr, target = info.get('currentPrice', 0), info.get('targetMeanPrice', 0)
            if curr > 0 and target > 0:
                upside = ((target - curr) / curr * 100)
                # Heuristic Favor (Fast)
                favor = "HIGH 🔥" if upside > 15 and score < 2.0 else "MED ⚖️" if upside > 5 else "LOW"
                data.append({
                    "Ticker": t, "Company": info.get('longName', t),
                    "Price": curr, "Upside %": round(upside, 1),
                    "Score": score, "AI Favor": favor
                })
        except: continue
    if not data: return pd.DataFrame(columns=["Ticker", "Company", "Price", "Upside %", "Score", "AI Favor"])
    return pd.DataFrame(data).sort_values("Score", ascending=True).head(6)

# --- 3. UI LAYOUT ---
st.set_page_config(page_title="Alpha Scout Pro", layout="wide")

# Header
try:
    fng_data = session.get("https://production.dataviz.cnn.io/index/fearandgreed/graphdata", headers=HEADERS, timeout=5).json()
    val, text = int(fng_data['fear_and_greed']['score']), fng_data['fear_and_greed']['rating'].upper()
except: val, text = 50, "NEUTRAL"

c1, c2 = st.columns([3, 1])
with c1:
    st.title("🛰️ Alpha Scout: Global Command")
    st.caption(f"Institutional Intelligence Dashboard | {datetime.now().strftime('%Y-%m-%d')}")
with c2:
    st.metric(f"SENTIMENT: {text}", f"{val}/100")
    st.progress(val / 100)

st.divider()

# --- 4. GLOBAL GRID ---
row1_col1, row1_col2 = st.columns(2)
row2_col1, row2_col2 = st.columns(2)
indices = [("S&P 500", row1_col1), ("Nasdaq-100", row1_col2), ("DAX", row2_col1), ("FTSE 100", row2_col2)]
all_top_tickers = []

with st.spinner("Syncing Global Markets..."):
    for idx_name, col in indices:
        with col:
            st.subheader(f"🏛️ {idx_name}")
            df = get_intel(get_tickers(idx_name))
            if not df.empty:
                st.dataframe(df, use_container_width=True, hide_index=True)
                all_top_tickers.extend(df.to_dict('records'))

st.divider()

# --- 5. AI TOP PICK (AUTO-LOADED) ---
st.subheader("🌟 AI Top Pick for Today")
high_favor_candidates = [t for t in all_top_tickers if "HIGH" in str(t['AI Favor'])]

if high_favor_candidates and client:
    # Pick the mathematically best one (highest upside)
    top_one = max(high_favor_candidates, key=lambda x: x['Upside %'])
    
    @st.cache_data(ttl=3600)
    def generate_top_pick_reason(ticker, name, upside):
        try:
            res = client.models.generate_content(
                model="gemini-2.0-flash", 
                contents=f"Why is {name} ({ticker}) a top pick with {upside}% upside? 1 short sentence."
            )
            return res.text.strip()
        except: return "Strongest institutional conviction and significant price-to-target gap."

    reason = generate_top_pick_reason(top_one['Ticker'], top_one['Company'], top_one['Upside %'])
    st.success(f"**{top_one['Company']} ({top_one['Ticker']})** — {reason}")
else:
    st.info("Scanning for high-conviction signals...")

st.divider()

# --- 6. PARALLEL AUDIT ---
st.subheader("🤖 AI Committee Deep-Dive")
if all_top_tickers:
    ticker_map = {f"{r['Ticker']} - {r['Company']}": r for r in all_top_tickers}
    sel_label = st.selectbox("Select stock to audit:", options=list(ticker_map.keys()))
    sel_data = ticker_map[sel_label]

    if st.button("🚀 RUN RAPID AUDIT"):
        with st.status("Council is debating...") as status:
            def agent_call(name, role):
                res = client.models.generate_content(
                    model="gemini-2.0-flash", 
                    contents=f"Audit {sel_data['Company']} ({sel_data['Ticker']}). Price: {sel_data['Price']}. Data: {yf.Ticker(sel_data['Ticker']).info}",
                    config=types.GenerateContentConfig(system_instruction=role)
                )
                return name, res.text

            votes = 0
            outputs = {}
            with concurrent.futures.ThreadPoolExecutor() as executor:
                futures = {executor.submit(agent_call, n, r): n for n, r in AGENT_ROLES.items()}
                for f in concurrent.futures.as_completed(futures):
                    n, text = f.result()
                    outputs[n] = text
                    if "VOTE: BUY" in text.upper(): votes += 1
            
            cols = st.columns(3)
            for i, (n, text) in enumerate(outputs.items()):
                with cols[i]:
                    st.write(f"### {n}")
                    st.write("✅ **BUY**" if "VOTE: BUY" in text.upper() else "❌ **REJECT**")
                    with st.expander("Why?"): st.markdown(text.replace("VOTE: BUY", "").replace("VOTE: NO", ""))
            
            if votes >= 2:
                st.success(f"🏆 PASSED ({votes}/3)")
                if votes == 3: confetti()
            else: st.error(f"🛑 REJECTED ({votes}/3)")
