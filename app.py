import os
import sys
import streamlit as st
import yfinance as yf
import requests
from google import genai
from google.genai import types

# --- 1. PORTABLE SECRETS FETCHING ---
def get_secret(key):
    # Railway/Env Var check first to avoid Streamlit .toml errors
    val = os.environ.get(key)
    if val:
        return val
    
    # Fallback for local development or Streamlit Cloud
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return None

GEMINI_KEY = get_secret("GEMINI_KEY")
TG_TOKEN = get_secret("TG_TOKEN")
CHAT_ID = get_secret("CHAT_ID")

# Initialize Gemini Client
if GEMINI_KEY:
    client = genai.Client(api_key=GEMINI_KEY)

# --- 2. CONFIGURATION & PERSONAS ---
WATCHLIST = ["INTC", "PYPL", "DIS", "F", "TSLA", "WBD", "T", "PFE", "BABA", "NKE"]

AGENT_PROMPTS = {
    "🐂 Value Hunter": "Focus on turnaround potential and 5-year lows. End with 'VOTE: BUY' or 'VOTE: NO'.",
    "📈 Momentum Pro": "Focus on positive catalysts and breakouts. End with 'VOTE: BUY' or 'VOTE: NO'.",
    "🐻 Cynical Bear": "Hunt for debt traps and reasons to VETO. End with 'VOTE: BUY' or 'VOTE: NO'."
}

# --- 3. CORE ENGINE FUNCTIONS ---
def get_stock_data(ticker):
    """Fetches real-time investor data"""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        return {
            "Name": info.get('longName', ticker),
            "Price": info.get('currentPrice', 0),
            "Rec": info.get('recommendationKey', 'N/A').upper()
        }
    except Exception:
        return None

def run_committee_scan():
    """Runs the 3-agent 2:1 consensus logic"""
    results = []
    for ticker in WATCHLIST:
        data = get_stock_data(ticker)
        if not data: continue
        
        votes = []
        for name, prompt in AGENT_PROMPTS.items():
            config = types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(include_thoughts=True),
                tools=[types.Tool(google_search=types.GoogleSearch())],
                system_instruction=prompt
            )
            try:
                res = client.models.generate_content(
                    model="gemini-2.0-flash-thinking-exp-01-21", 
                    contents=f"Audit {ticker}: {data}", 
                    config=config
                )
                votes.append(1 if "VOTE: BUY" in res.text.upper() else 0)
            except Exception:
                votes.append(0)
        
        if sum(votes) >= 2:
            results.append({"Ticker": ticker, "Votes": sum(votes), "Price": data['Price']})
    
    return sorted(results, key=lambda x: x['Votes'], reverse=True)[:5]

def send_telegram(picks):
    """Dispatches results to Telegram"""
    if not picks or not TG_TOKEN: return
    msg = "🎯 **ALPHA SCOUT: WEEKLY PICKS**\n\n" + "\n".join(
        [f"• {p['Ticker']} (${p['Price']}) - {p['Votes']}/3 Votes" for p in picks]
    )
