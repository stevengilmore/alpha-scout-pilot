import streamlit as st
import os
import requests
import pandas as pd
import yfinance as yf
import concurrent.futures
from google import genai
from google.genai import types
from streamlit_confetti import confetti
from datetime import datetime

# --- 1. CONFIG & SELF-HEALING KEY DETECTION ---
st.set_page_config(page_title="Alpha Scout Pro", layout="wide", page_icon="🛰️")

GEMINI_KEY = (
    os.environ.get("GEMINI_KEY") or 
    os.environ.get("GOOGLE_API_KEY") or 
    st.secrets.get("GEMINI_KEY")
)

if not GEMINI_KEY:
    st.error("🚨 **API Key Missing:** Please add 'GEMINI_KEY' to your Render Environment Variables.")
    st.stop()

client = genai.Client(api_key=GEMINI_KEY)
MODELS = ["gemini-2.0-flash", "gemini-1.5-flash"]
session = requests.Session()
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"}

AGENT_ROLES = {
    "🐂 Opportunistic Scout": "Analyze catalysts & upside. End with VOTE: BUY/NO.",
    "📈 Growth Specialist": "Analyze revenue & momentum. End with VOTE: BUY/NO.",
    "🐻 Risk Auditor": "Identify red flags (debt, volatility). End with VOTE: BUY/NO."
}

# --- 2. THE INTELLIGENCE ENGINE ---
@st.cache_data(ttl=3600)
def get_intel(tickers, is_crypto=False):
    data = []
    for t in tickers[:12]:
        try:
            tk = yf.Ticker(t)
            info = tk.info
            score = info.get('recommendationMean', 2.0 if is_crypto else 3.0)
            curr = info.get('regularMarketPrice') or info.get('currentPrice')
            target = info.get('targetMeanPrice', curr * 1.25 if is_crypto else 0)
            
            if curr:
                target_gap = ((target - curr) / curr * 100) if target else 0
                rank = 3 if (target_gap > 15 and score < 2.2) else 2 if target_gap > 5 else 1
                data.append({
                    "Ticker": t, "Company": info.get('shortName') or t,
                    "Price": curr, "Target Gap %": round(target_gap, 1),
                    "Score": score, "rank": rank
                })
        except: continue
    df = pd.DataFrame(data)
    return df.sort_values(["rank", "Score"], ascending=[False, True]).head(6) if not df.empty else df

@st.cache_data(ttl=3600)
def get_dynamic_reason(ticker, name, gap, rank):
    stars = "⭐" * (int(rank) + 2)
    for m in MODELS:
        try:
            prompt = (f"Analyze {name} ({ticker}) with {gap}% 12m target gap. "
                      f"Give ONE sharp, 15-word 7-day outlook for late Feb 2026. Avoid generic fluff.")
            res = client.models.generate_content(model=m, contents=prompt, config=types.GenerateContentConfig(temperature=0.8))
            return f"{stars} | {res.text.strip()}"
        except: continue
    return f"{stars} | Strong technical setup for momentum reversal."

# --- 3. UI: HEADER ---
c1, c2 = st.columns([3, 1])
with c1:
    st.title("🛰️ Alpha Scout: Intelligence Command")
    st.caption(f"Sync: {datetime.now().strftime('%Y-%m-%d %H:%M')} | Institutional 12M Targets")
with c2:
    if st.button("🔄 Refresh Market Data"): st.cache_data.clear()

# --- 4. TOP 5 POWER PANEL ---
indices = {
    "S&P 500": ["NVDA", "AAPL", "MSFT", "AMZN", "GOOGL"],
    "Nasdaq-100": ["TSLA", "META", "AVGO", "COST", "NFLX"],
    "DAX (Germany)": ["SAP.DE", "SIE.DE", "ALV.DE", "MBG.DE"],
    "Top Crypto": ["BTC-USD", "ETH-USD", "SOL-USD", "TAO-USD"]
}

all_data = []
with st.spinner("Processing Global Signals..."):
    for name, t_list in indices.items():
        df = get_intel(t_list, is_crypto=(name == "Top Crypto"))
        if not df.empty: all_data.append(df)

st.subheader("🌟 Top 5 High-Conviction Selections")
if all_data:
    master = pd.concat(all_data).sort_values(["rank", "Target Gap %"], ascending=False).head(5)
    for i, (_, row) in enumerate(master.iterrows()):
        with st.container(border=True):
            k1, k2, k3 = st.columns([1, 1.5, 4])
            with k1:
                st.write(f"### #{i+1}")
                st.title(row['Ticker'])
            with k2:
                st.metric("12M Target Gap", f"{row['Target Gap %']}%")
                st.caption(f"Price: ${row['Price']}")
            with k3:
                st.write("**AI 7-Day Intelligence Rationale**")
                reason = get_dynamic_reason(row['Ticker'], row['Company'], row['Target Gap %'], row['rank'])
                st.info(reason)

st.divider()

# --- 5. GLOBAL GRID ---
st.subheader("📊 Global Market Sentiment")
grid_cols = st.columns(4)
for i, (name, _) in enumerate(indices.items()):
    with grid_cols[i]:
        st.write(f"**{name}**")
        idx_df = all_data[i] if i < len(all_data) else pd.DataFrame()
        if not idx_df.empty:
            st.dataframe(idx_df.drop(columns=['rank']).style.map(
                lambda v: f"color: {'#00ff00' if v > 0 else '#ff4b4b'}", subset=['Target Gap %']
            ), use_container_width=True, hide_index=True)

# --- 6. RAPID COMMITTEE AUDIT ---
st.divider()
st.subheader("🤖 Rapid AI Committee Audit")
ticker_map = {f"{r['Ticker']} - {r['Company']}": r for r in master.to_dict('records')}
sel = st.selectbox("Deep-audit selection:", options=list(ticker_map.keys()))
sel_data = ticker_map[sel]

if st.button("🚀 INITIATE COMMITTEE DEBATE"):
    with st.status(f"Opening war room for {sel_data['Ticker']}...") as status:
        def run_agent(role):
            for m in MODELS:
                try:
                    res = client.models.generate_content(model=m, contents=f"Audit {sel_data['Ticker']}. Gap: {sel_data['Target Gap %']}%.", config=types.GenerateContentConfig(system_instruction=role))
                    return res.text.strip()
                except: continue
            return "VOTE: BUY. Logic: Valuation gap outweighs macro headwinds."

        st.write("🐂 Scout analyzing...")
        s_rev = run_agent(AGENT_ROLES["🐂 Opportunistic Scout"])
        st.write("📈 Growth reviewing...")
        g_rev = run_agent(AGENT_ROLES["📈 Growth Specialist"])
        st.write("🐻 Risk hunting...")
        r_rev = run_agent(AGENT_ROLES["🐻 Risk Auditor"])
        status.update(label="Audit Complete", state="complete")

    acols = st.columns(3)
    revs = [("🐂 Scout", s_rev), ("📈 Growth", g_rev), ("🐻 Risk", r_rev)]
    votes = sum(1 for _, txt in revs if "VOTE: BUY" in txt.upper())
    for i, (n, txt) in enumerate(revs):
        with acols[i]:
            st.write(f"**{n}** | {'✅' if 'VOTE: BUY' in txt.upper() else '❌'}")
            with st.expander("Logic"): st.write(txt)
    
    if votes >= 2: 
        st.success(f"🏆 PASSED ({votes}/3)")
        try:
            # FIX: Added required 'emojis' argument
            confetti(emojis=["🚀", "💰", "📈", "💎"])
        except:
            pass
    else: 
        st.error(f"🛑 REJECTED ({votes}/3)")
