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

# --- 1. CONFIG & SELF-HEALING KEYS ---
st.set_page_config(page_title="Alpha Scout Pro", layout="wide", page_icon="🛰️")
session = requests.Session()
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"}

# Multi-stage Fallback for 2026 Model Stability
MODELS_TO_TRY = ["gemini-2.0-flash", "gemini-1.5-flash"]

GEMINI_KEY = os.environ.get("GEMINI_KEY") or st.secrets.get("GEMINI_KEY")
if not GEMINI_KEY:
    st.error("🚨 API Key Missing: Please add 'GEMINI_KEY' to Render Environment Variables.")
    st.stop()

client = genai.Client(api_key=GEMINI_KEY)

# --- 2. THE INTELLIGENCE ENGINE ---
@st.cache_data(ttl=3600)
def get_intel(tickers, is_crypto=False):
    """Calculates institutional conviction and AI favorability."""
    data = []
    # Scanning top 10 for maximum responsiveness
    for t in tickers[:10]:
        try:
            tk = yf.Ticker(t)
            info = tk.info
            # Recommendation Mean: 1.0 (Strong Buy) to 5.0 (Sell)
            score = info.get('recommendationMean', 2.0 if is_crypto else 3.0)
            curr = info.get('regularMarketPrice') or info.get('currentPrice')
            # 2026 Crypto assumes a higher volatility baseline for targets
            target = info.get('targetMeanPrice', curr * 1.25 if is_crypto else 0)
            
            if curr:
                upside = ((target - curr) / curr * 100) if target else 0
                # Rank 3 = HIGH 🔥, Rank 2 = MED ⚖️, Rank 1 = LOW
                rank = 3 if (upside > 15 and score < 2.2) or (is_crypto and upside > 20) else 2 if upside > 5 else 1
                data.append({
                    "Ticker": t,
                    "Company": info.get('shortName') or info.get('longName', t),
                    "Price": curr,
                    "Upside %": round(upside, 1),
                    "Score": score,
                    "AI Favor": "HIGH 🔥" if rank == 3 else "MED ⚖️" if rank == 2 else "LOW",
                    "rank": rank
                })
        except: continue
    df = pd.DataFrame(data)
    if df.empty: return df
    # Priority Sorting: AI Rank first, then institutional consensus
    return df.sort_values(["rank", "Score"], ascending=[False, True]).head(6)

# --- 3. UI: HEADER & QUAD-GRID ---
c1, c2 = st.columns([3, 1])
with c1:
    st.title("🛰️ Alpha Scout: Intelligence Command")
    st.caption(f"Institutional Data Sync: {datetime.now().strftime('%Y-%m-%d %H:%M')} | Status: ACTIVE")
with c2:
    if st.button("🔄 Refresh Market Data"):
        st.cache_data.clear()

st.divider()

# Pre-defined high-performance indices for 2026
indices = {
    "S&P 500": ["NVDA", "AAPL", "MSFT", "AMZN", "GOOGL", "META"],
    "Nasdaq-100": ["TSLA", "AVGO", "COST", "NFLX", "AMD", "PLTR"],
    "DAX (Germany)": ["SAP.DE", "SIE.DE", "ALV.DE", "MBG.DE", "VOW3.DE"],
    "Top Crypto": ["BTC-USD", "ETH-USD", "SOL-USD", "TAO-USD", "LINK-USD"]
}

all_data = []
with st.spinner("Analyzing Global Signals..."):
    cols = st.columns(4)
    for i, (name, t_list) in enumerate(indices.items()):
        df = get_intel(t_list, is_crypto=(name == "Top Crypto"))
        if not df.empty:
            all_data.append(df)
            with cols[i]:
                st.subheader(f"🏛️ {name}")
                # Color code the upside for visual 'Wow'
                st.dataframe(
                    df.drop(columns=['rank']).style.map(lambda v: f"color: {'#00ff00' if v > 0 else '#ff4b4b'}", subset=['Upside %']),
                    use_container_width=True, hide_index=True
                )

# --- 4. THE "WOW" FEATURE: TOP 5 INTELLIGENCE PANEL ---
st.divider()
st.subheader("🌟 Top 5 AI Selections for the Week")

if all_data:
    master_df = pd.concat(all_data).sort_values(["rank", "Upside %"], ascending=False).head(5)
    
    @st.cache_data(ttl=3600)
    def get_robust_reason(ticker, name, upside):
        """Fetches sharp AI rationale with model failover."""
        for m in MODELS_TO_TRY:
            try:
                prompt = f"In 15 words or less, why is {name} ({ticker}) a top pick today with {upside}% upside?"
                res = client.models.generate_content(model=m, contents=prompt)
                return res.text.strip()
            except: continue
        return "Strong institutional accumulation and sector-leading technical momentum."

    # Render Top 5 as high-end Cards
    for i, (_, row) in enumerate(master_df.iterrows()):
        with st.container(border=True):
            k1, k2, k3, k4 = st.columns([0.5, 1.5, 2, 4])
            with k1:
                st.write(f"### #{i+1}")
            with k2:
                st.title(row['Ticker'])
                # Star System: 4-5 stars for top picks
                st.write("⭐" * (int(row['rank']) + 2))
            with k3:
                st.metric("7-Day Upside", f"+{row['Upside %']}%")
                st.caption(f"Score: {row['Score']}/5.0")
            with k4:
                st.write("**Intelligence Rationale**")
                reason = get_robust_reason(row['Ticker'], row['Company'], row['Upside %'])
                st.info(reason)

# --- 5. THE RAPID AUDIT (SIMULTANEOUS) ---
st.divider()
st.subheader("🤖 Rapid AI Committee Audit")
if all_data:
    ticker_map = {f"{r['Ticker']} - {r['Company']}": r for r in master_df.to_dict('records')}
    sel_label = st.selectbox("Select asset for deep-dive validation:", options=list(ticker_map.keys()))
    sel_data = ticker_map[sel_label]

    if st.button("🚀 INITIATE COMMITTEE DEBATE"):
        with st.status("Agents debating in parallel...") as status:
            def agent_call(name, role):
                for m in MODELS_TO_TRY:
                    try:
                        res = client.models.generate_content(
                            model=m, 
                            contents=f"Audit {sel_data['Ticker']}. Context: {yf.Ticker(sel_data['Ticker']).info}",
                            config=types.GenerateContentConfig(system_instruction=role)
                        )
                        return name, res.text
                    except: continue
                return name, "Agent disconnected."

            roles = {"🐂 Scout": "Catalysts?", "📈 Growth": "Sustainable?", "🐻 Risk": "Red flags?"}
            with concurrent.futures.ThreadPoolExecutor() as ex:
                futures = [ex.submit(agent_call, n, r) for n, r in roles.items()]
                results = [f.result() for f in concurrent.futures.as_completed(futures)]
            
            acols = st.columns(3)
            votes = sum(1 for t in results if "VOTE: BUY" in t[1].upper())
            for i, (n, txt) in enumerate(results):
                with acols[i]:
                    st.write(f"**{n}**")
                    st.write("✅ **BUY**" if "VOTE: BUY" in txt.upper() else "❌ **NO**")
                    with st.expander("Show Logic"): st.write(txt.replace("VOTE: BUY", "").replace("VOTE: NO", ""))
            
            if votes >= 2:
                st.success(f"🏆 AUDIT PASSED ({votes}/3)")
                if votes == 3: confetti()
            else: st.error(f"🛑 AUDIT REJECTED ({votes}/3)")
