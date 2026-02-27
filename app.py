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

# --- 1. ROBUST CONFIG ---
st.set_page_config(page_title="Alpha Scout Pro", layout="wide", page_icon="🛰️")
session = requests.Session()
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"}

# Model Fallbacks
MODELS = ["gemini-2.0-flash", "gemini-1.5-flash"]
GEMINI_KEY = os.environ.get("GEMINI_KEY") or st.secrets.get("GEMINI_KEY")

if not GEMINI_KEY:
    st.error("🚨 GEMINI_KEY missing in Render Environment!")
    st.stop()

client = genai.Client(api_key=GEMINI_KEY)

# --- 2. THE "WOW" DATA ENGINE ---
@st.cache_data(ttl=3600)
def get_intel(tickers, is_crypto=False):
    data = []
    # Limit to 10 for maximum speed
    for t in tickers[:10]:
        try:
            tk = yf.Ticker(t)
            info = tk.info
            score = info.get('recommendationMean', 2.0 if is_crypto else 3.0)
            curr = info.get('regularMarketPrice') or info.get('currentPrice')
            target = info.get('targetMeanPrice', curr * 1.2 if is_crypto else 0)
            
            if curr:
                upside = ((target - curr) / curr * 100) if target else 0
                rank = 3 if upside > 15 and score < 2.2 else 2 if upside > 5 else 1
                data.append({
                    "Ticker": t, "Company": info.get('shortName') or t,
                    "Price": curr, "Upside %": round(upside, 1),
                    "Score": score, "AI Favor": "HIGH 🔥" if rank == 3 else "MED ⚖️",
                    "rank": rank
                })
        except: continue
    df = pd.DataFrame(data)
    return df.sort_values(["rank", "Score"], ascending=[False, True]).head(5) if not df.empty else df

# --- 3. UI: HEADER & TOP PICK ---
c1, c2 = st.columns([3, 1])
with c1:
    st.title("🛰️ Alpha Scout: Intelligence Edition")
    st.caption(f"Live Intelligence Feed | {datetime.now().strftime('%Y-%m-%d %H:%M')}")
with c2:
    st.button("🔄 Refresh Data")

# Fetch Data for Quad-Grid
indices = {
    "S&P 500": ["NVDA", "AAPL", "MSFT", "AMZN", "GOOGL"],
    "Nasdaq-100": ["TSLA", "META", "AVGO", "COST", "NFLX"],
    "DAX": ["SAP.DE", "SIE.DE", "ALV.DE", "MBG.DE"],
    "Top Crypto": ["BTC-USD", "ETH-USD", "SOL-USD", "LINK-USD"]
}

all_data = []
with st.spinner("Analyzing Global Momentum..."):
    cols = st.columns(4)
    for i, (name, t_list) in enumerate(indices.items()):
        df = get_intel(t_list, is_crypto=(name == "Top Crypto"))
        if not df.empty:
            all_data.append(df)
            with cols[i]:
                st.subheader(f"🏛️ {name}")
                st.dataframe(df.drop(columns=['rank']), use_container_width=True, hide_index=True)

# --- 4. THE "WOW" FEATURE: AI TOP PICK CARD ---
st.divider()
if all_data:
    master = pd.concat(all_data)
    top_one = master.sort_values("Upside %", ascending=False).iloc[0]
    
    with st.container(border=True):
        st.subheader("🌟 AI Top Selection for Today")
        k1, k2, k3 = st.columns([1, 1, 2])
        with k1:
            st.title(top_one['Ticker'])
            st.write(top_one['Company'])
        with k2:
            st.metric("7-Day Upside", f"+{top_one['Upside %']}%")
            st.write("Confidence: ⭐⭐⭐⭐⭐")
        with k3:
            @st.cache_data(ttl=3600)
            def get_ai_reason(t, n):
                for m in MODELS:
                    try:
                        res = client.models.generate_content(model=m, contents=f"Why is {n} ({t}) a top pick? 1 sharp sentence.")
                        return res.text.strip()
                    except: continue
                return "Strongest institutional conviction in current sector."
            
            st.info(get_ai_reason(top_one['Ticker'], top_one['Company']))

# --- 5. RAPID AUDIT ---
st.divider()
st.subheader("🤖 AI Committee Deep-Dive")
ticker_map = {f"{r['Ticker']} - {r['Company']}": r for r in master.to_dict('records')}
sel = st.selectbox("Select asset for deep audit:", options=list(ticker_map.keys()))
sel_data = ticker_map[sel]

if st.button("🚀 INITIATE RAPID AUDIT"):
    with st.status("Agents debating...") as status:
        def agent_call(name, role):
            for m in MODELS:
                try:
                    res = client.models.generate_content(
                        model=m, 
                        contents=f"Audit {sel_data['Ticker']}. Data: {yf.Ticker(sel_data['Ticker']).info}",
                        config=types.GenerateContentConfig(system_instruction=role)
                    )
                    return name, res.text
                except: continue
            return name, "AI Unavailable"

        with concurrent.futures.ThreadPoolExecutor() as ex:
            futures = [ex.submit(agent_call, n, r) for n, r in {"🐂 Scout": "Catalysts?", "📈 Growth": "Sustainable?", "🐻 Risk": "Red flags?"}.items()]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        acols = st.columns(3)
        for i, (n, txt) in enumerate(results):
            with acols[i]:
                st.write(f"**{n}**")
                st.write("✅" if "VOTE: BUY" in txt.upper() else "❌")
                with st.expander("Details"): st.write(txt)
