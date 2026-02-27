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

# Updated Model Logic: Try 2.0 Stable, Fallback to 1.5
PRIMARY_MODEL = "gemini-2.0-flash-001"
FALLBACK_MODEL = "gemini-1.5-flash"

GEMINI_KEY = os.environ.get("GEMINI_KEY") or st.secrets.get("GEMINI_KEY")
client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None

AGENT_ROLES = {
    "🐂 Opportunistic Scout": "Analyze catalysts & upside. Explain logic. End with VOTE: BUY/NO.",
    "📈 Growth Specialist": "Analyze revenue & momentum. Explain logic. End with VOTE: BUY/NO.",
    "🐻 Risk Auditor": "Identify red flags (debt, volatility). List rejection reasons. End with VOTE: BUY/NO."
}

# --- 2. DATA ENGINES ---
@st.cache_data(ttl=86400)
def get_tickers(index_name):
    if index_name == "Top Crypto":
        return ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD", "AVAX-USD", "DOGE-USD", "LINK-USD"]
    urls = {
        "S&P 500": "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
        "Nasdaq-100": "https://en.wikipedia.org/wiki/Nasdaq-100",
        "DAX": "https://en.wikipedia.org/wiki/DAX"
    }
    try:
        res = session.get(urls[index_name], headers=HEADERS, timeout=10)
        tables = pd.read_html(res.text)
        if index_name == "S&P 500": return tables[0]['Symbol'].str.replace('.', '-', regex=False).tolist()
        if index_name == "Nasdaq-100": return tables[4]['Ticker'].tolist()
        if index_name == "DAX": return tables[4]['Ticker'].tolist()
    except: return []

@st.cache_data(ttl=3600)
def get_intel(tickers, is_crypto=False):
    data = []
    for t in tickers[:15]: 
        try:
            info = yf.Ticker(t).info
            score = info.get('recommendationMean', 2.0 if is_crypto else 5.0)
            curr = info.get('regularMarketPrice') or info.get('currentPrice')
            target = info.get('targetMeanPrice', curr * 1.15 if is_crypto else 0)
            if curr:
                upside = ((target - curr) / curr * 100) if target else 0
                favor_rank = 3 if upside > 15 and score < 2.2 else 2 if upside > 5 else 1
                favor_text = "HIGH 🔥" if favor_rank == 3 else "MED ⚖️" if favor_rank == 2 else "LOW"
                data.append({
                    "Ticker": t, "Company": info.get('shortName') or info.get('longName', t),
                    "Price": curr, "Upside %": round(upside, 1),
                    "Score": score, "AI Favor": favor_text, "rank": favor_rank
                })
        except: continue
    if not data: return pd.DataFrame()
    return pd.DataFrame(data).sort_values(by=["rank", "Score"], ascending=[False, True]).drop(columns=["rank"]).head(6)

# --- 3. UI LAYOUT ---
st.set_page_config(page_title="Alpha Scout Pro", layout="wide")

try:
    fng_res = session.get("https://production.dataviz.cnn.io/index/fearandgreed/graphdata", headers=HEADERS, timeout=5).json()
    val, text = int(fng_res['fear_and_greed']['score']), fng_res['fear_and_greed']['rating'].upper()
except: val, text = 50, "NEUTRAL"

c1, c2 = st.columns([3, 1])
with c1:
    st.title("🛰️ Alpha Scout: Global Command")
    st.caption(f"Sync Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
with c2:
    st.metric(f"SENTIMENT: {text}", f"{val}/100")
    st.progress(val / 100)

st.divider()

# --- 4. GLOBAL GRID ---
row1_col1, row1_col2 = st.columns(2)
row2_col1, row2_col2 = st.columns(2)
indices = [("S&P 500", row1_col1), ("Nasdaq-100", row1_col2), ("DAX", row2_col1), ("Top Crypto", row2_col2)]
all_top_tickers = []

with st.spinner("Aggregating Conviction Data..."):
    for idx_name, col in indices:
        with col:
            st.subheader(f"🏛️ {idx_name}")
            df = get_intel(get_tickers(idx_name), is_crypto=(idx_name == "Top Crypto"))
            if not df.empty:
                st.dataframe(df.style.map(lambda v: f"color: {'#00ff00' if v > 0 else '#ff4b4b'}", subset=['Upside %']), 
                             use_container_width=True, hide_index=True)
                all_top_tickers.extend(df.to_dict('records'))

st.divider()

# --- 5. ROBUST AI TOP PICK (FAILOVER ENABLED) ---
st.subheader("🌟 AI Top Pick for Today")
high_favor = [t for t in all_top_tickers if "HIGH" in str(t['AI Favor'])]
top_list = high_favor if high_favor else all_top_tickers

if top_list and client:
    top_one = max(top_list, key=lambda x: x['Upside %'])
    
    @st.cache_data(ttl=3600)
    def get_robust_reason(ticker, name):
        # Try primary, then fallback
        for model in [PRIMARY_MODEL, FALLBACK_MODEL]:
            try:
                res = client.models.generate_content(model=model, contents=f"Why is {name} ({ticker}) a top pick? 1 sentence.")
                return res.text.strip()
            except: continue
        return "Strong institutional momentum and sector-leading price targets."
    
    st.success(f"**{top_one['Company']} ({top_one['Ticker']})** — {get_robust_reason(top_one['Ticker'], top_one['Company'])}")

st.divider()

# --- 6. RAPID SIMULTANEOUS AUDIT ---
st.subheader("🤖 AI Committee Deep-Dive")
if all_top_tickers:
    ticker_map = {f"{r['Ticker']} - {r['Company']}": r for r in all_top_tickers}
    sel_label = st.selectbox("Select asset to audit:", options=list(ticker_map.keys()))
    sel_data = ticker_map[sel_label]

    if st.button("🚀 RUN RAPID AUDIT"):
        with st.status("Council is debating...") as status:
            def robust_agent_call(name, role):
                for model in [PRIMARY_MODEL, FALLBACK_MODEL]:
                    try:
                        res = client.models.generate_content(
                            model=model, 
                            contents=f"Audit {sel_data['Company']} ({sel_data['Ticker']}). Price: {sel_data['Price']}. Context: {yf.Ticker(sel_data['Ticker']).info}",
                            config=types.GenerateContentConfig(system_instruction=role)
                        )
                        return name, res.text
                    except: continue
                return name, "Critical failure: AI Models unavailable."

            outputs = {}
            with concurrent.futures.ThreadPoolExecutor() as executor:
                futures = {executor.submit(robust_agent_call, n, r): n for n, r in AGENT_ROLES.items()}
                for f in concurrent.futures.as_completed(futures):
                    n, text = f.result()
                    outputs[n] = text
            
            cols = st.columns(3)
            votes = sum(1 for t in outputs.values() if "VOTE: BUY" in t.upper())
            for i, (n, text) in enumerate(outputs.items()):
                with cols[i]:
                    st.write(f"### {n}")
                    st.write("✅ **BUY**" if "VOTE: BUY" in text.upper() else "❌ **REJECT**")
                    with st.expander("Reasoning"): st.markdown(text.replace("VOTE: BUY", "").replace("VOTE: NO", ""))
            
            if votes >= 2:
                st.success(f"🏆 PASSED ({votes}/3)")
                if votes == 3: confetti()
            else: st.error(f"🛑 REJECTED ({votes}/3)")
