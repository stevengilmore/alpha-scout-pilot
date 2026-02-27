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

# --- 1. SELF-HEALING CONFIG & KEYS ---
session = requests.Session()
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"}

# Multi-stage Fallback for 2026 Model IDs
MODELS_TO_TRY = ["gemini-2.0-flash", "gemini-2.0-flash-001", "gemini-1.5-flash"]

# Key Detection: Checks Render Env and Streamlit Secrets
GEMINI_KEY = (
    os.environ.get("GEMINI_KEY") or 
    os.environ.get("GOOGLE_API_KEY") or 
    st.secrets.get("GEMINI_KEY")
)

if not GEMINI_KEY:
    st.error("🚨 API Key Missing: Please add 'GEMINI_KEY' to your Render Environment Variables.")
    st.stop()

client = genai.Client(api_key=GEMINI_KEY)

AGENT_ROLES = {
    "🐂 Opportunistic Scout": "Analyze catalysts & upside. Explain logic. End with VOTE: BUY/NO.",
    "📈 Growth Specialist": "Analyze revenue & momentum. Explain logic. End with VOTE: BUY/NO.",
    "🐻 Risk Auditor": "Identify red flags (debt, volatility). List rejection reasons. End with VOTE: BUY/NO."
}

# --- 2. GLOBAL DATA ENGINES ---
@st.cache_data(ttl=86400)
def get_tickers(index_name):
    if index_name == "Top Crypto":
        return ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD", "AVAX-USD", "LINK-USD"]
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
                rank = 3 if upside > 15 and score < 2.2 else 2 if upside > 5 else 1
                data.append({
                    "Ticker": t, "Company": info.get('shortName') or info.get('longName', t),
                    "Price": curr, "Upside %": round(upside, 1),
                    "Score": score, "AI Favor": "HIGH 🔥" if rank == 3 else "MED ⚖️" if rank == 2 else "LOW",
                    "rank": rank
                })
        except: continue
    if not data: return pd.DataFrame()
    # SORTING: AI Favor first, then Institutional Score
    return pd.DataFrame(data).sort_values(by=["rank", "Score"], ascending=[False, True]).drop(columns=["rank"]).head(6)

# --- 3. UI LAYOUT ---
st.set_page_config(page_title="Alpha Scout Command", layout="wide")

try:
    fng = session.get("https://production.dataviz.cnn.io/index/fearandgreed/graphdata", headers=HEADERS).json()['fear_and_greed']
    val, text = int(fng['score']), fng['rating'].upper()
except: val, text = 50, "NEUTRAL"

c1, c2 = st.columns([3, 1])
with c1:
    st.title("🛰️ Alpha Scout: Global Command")
    st.caption(f"Sync: {datetime.now().strftime('%H:%M')} | Key Status: ACTIVE")
with c2:
    st.metric(f"SENTIMENT: {text}", f"{val}/100")
    st.progress(val / 100)

st.divider()

# --- 4. THE QUAD-GRID ---
row1 = st.columns(2)
row2 = st.columns(2)
indices = [("S&P 500", row1[0]), ("Nasdaq-100", row1[1]), ("DAX", row2[0]), ("Top Crypto", row2[1])]
all_top_tickers = []

with st.spinner("Syncing markets..."):
    for idx_name, col in indices:
        with col:
            st.subheader(f"🏛️ {idx_name}")
            df = get_intel(get_tickers(idx_name), is_crypto=(idx_name == "Top Crypto"))
            if not df.empty:
                st.dataframe(df.style.map(lambda v: f"color: {'#00ff00' if v > 0 else '#ff4b4b'}", subset=['Upside %']), 
                             use_container_width=True, hide_index=True)
                all_top_tickers.extend(df.to_dict('records'))

st.divider()

# --- 5. AI TOP PICK (ROBUST) ---
st.subheader("🌟 AI Top Pick for Today")
high_favor = [t for t in all_top_tickers if "HIGH" in str(t['AI Favor'])]
top_list = high_favor if high_favor else all_top_tickers

if top_list and client:
    top_one = max(top_list, key=lambda x: x['Upside %'])
    
    @st.cache_data(ttl=3600)
    def get_reason(ticker, name):
        for m in MODELS_TO_TRY:
            try:
                res = client.models.generate_content(model=m, contents=f"Why is {name} ({ticker}) a top pick? 1 sentence.")
                return f"{res.text.strip()}"
            except: continue
        return "Asset with sector-leading institutional conviction and growth metrics."
    
    st.success(f"**{top_one['Company']} ({top_one['Ticker']})** — {get_reason(top_one['Ticker'], top_one['Company'])}")

st.divider()

# --- 6. SIMULTANEOUS COMMITTEE AUDIT ---
st.subheader("🤖 AI Committee Deep-Dive")
if all_top_tickers:
    ticker_map = {f"{r['Ticker']} - {r['Company']}": r for r in all_top_tickers}
    sel_label = st.selectbox("Select asset to audit:", options=list(ticker_map.keys()))
    sel_data = ticker_map[sel_label]

    if st.button("🚀 RUN RAPID AUDIT"):
        with st.status("Council is debating...") as status:
            def robust_agent_call(name, role):
                for m in MODELS_TO_TRY:
                    try:
                        res = client.models.generate_content(
                            model=m, 
                            contents=f"Audit {sel_data['Company']} ({sel_data['Ticker']}). Data: {yf.Ticker(sel_data['Ticker']).info}",
                            config=types.GenerateContentConfig(system_instruction=role)
                        )
                        return name, res.text, m
                    except: continue
                return name, "Critical failure: Gemini Models unavailable.", "NONE"

            outputs = []
            with concurrent.futures.ThreadPoolExecutor() as executor:
                futures = [executor.submit(robust_agent_call, n, r) for n, r in AGENT_ROLES.items()]
                for f in concurrent.futures.as_completed(futures):
                    outputs.append(f.result())
            
            cols = st.columns(3)
            votes = sum(1 for t in outputs if "VOTE: BUY" in t[1].upper())
            for i, (n, text, model_used) in enumerate(outputs):
                with cols[i]:
                    is_buy = "VOTE: BUY" in text.upper()
                    st.write(f"### {n}")
                    st.write("✅ **BUY**" if is_buy else "❌ **REJECT**")
                    with st.expander("Reasoning"): 
                        st.caption(f"Model: {model_used}")
                        st.markdown(text.replace("VOTE: BUY", "").replace("VOTE: NO", ""))
            
            if votes >= 2:
                st.success(f"🏆 PASSED ({votes}/3)"); 
                if votes == 3: confetti()
            else: st.error(f"🛑 REJECTED ({votes}/3)")
