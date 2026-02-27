import os
import streamlit as st
import yfinance as yf
from google import genai
from google.genai import types

# --- 1. THE 5-AGENT COMMITTEE PERSONAS ---
# Each agent has a distinct "lens" to ensure diversity
AGENT_ROLES = {
    "🐂 Value Hunter": "Focus on turnaround potential and 5-year lows. Risk: Moderate.",
    "📈 Growth Specialist": "Look for revenue growth >20%. Accept higher P/E ratios.",
    "🐻 Cynical Auditor": "The 'Veto' agent. Look for debt traps, high SBC, or insiders selling.",
    "🌍 Macro Strategist": "Analyze sector trends and how 'Fear & Greed' affects this specific stock.",
    "⚖️ Governance Pro": "Focus on management quality and institutional ownership trends."
}

def get_secret(key):
    return os.environ.get(key) or st.secrets.get(key)

GEMINI_KEY = get_secret("GEMINI_KEY")
client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None

# --- 2. AUDIT LOGIC (3/5 PASS) ---
def run_5_agent_audit(ticker, data):
    votes = 0
    debate_details = []
    
    for name, instruction in AGENT_ROLES.items():
        # Using Gemini 2.0 Flash Thinking for deep reasoning
        config = types.GenerateContentConfig(
            system_instruction=f"{instruction} End your analysis with 'VOTE: BUY' or 'VOTE: NO'.",
            thinking_config=types.ThinkingConfig(include_thoughts=True) # Enables transparency
        )
        try:
            res = client.models.generate_content(
                model="gemini-2.0-flash-thinking-exp-01-21", 
                contents=f"Audit {ticker} using this data: {data}", 
                config=config
            )
            is_buy = "VOTE: BUY" in res.text.upper()
            if is_buy: votes += 1
            
            debate_details.append({
                "agent": name,
                "vote": "✅ BUY" if is_buy else "❌ NO",
                "reasoning": res.text.split("VOTE:")[0] # Capture the 'Why'
            })
        except:
            debate_details.append({"agent": name, "vote": "⚠️ ERROR", "reasoning": "Agent timed out."})
            
    return votes, debate_details

# --- 3. UI DASHBOARD ---
st.set_page_config(layout="wide")
st.title("🛰️ Alpha Scout: 5-Agent Committee")

# Logic to display 3/5 results
if st.button("🚀 RUN 5-AGENT AUDIT"):
    ticker = "PYPL" # Example
    stock_data = yf.Ticker(ticker).info
    
    votes, details = run_5_agent_audit(ticker, stock_data)
    
    # 3 out of 5 Threshold
    if votes >= 3:
        st.success(f"🏆 {ticker} PASSED (Vote: {votes}/5)")
    else:
        st.error(f"🛑 {ticker} REJECTED (Vote: {votes}/5)")

    # Display individual reasoning
    for d in details:
        with st.expander(f"{d['agent']} - {d['vote']}"):
            st.write(d['reasoning'])
