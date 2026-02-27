import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from google import genai
from google.genai import types

# --- 1. SETTINGS & CACHING ---
st.set_page_config(page_title="Alpha Scout: Committee Command", layout="wide")

# Cache data for 1 hour to prevent Yahoo Finance throttling
@st.cache_data(ttl=3600)
def get_investor_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        return {
            "Name": info.get('longName', ticker),
            "Analyst_Count": info.get('numberOfAnalystOpinions', 'N/A'),
            "Rec": info.get('recommendationKey', 'N/A').upper(),
            "Price": info.get('currentPrice', 0)
        }
    except Exception:
        return None

# --- 2. MULTI-AGENT ENGINE ---
def run_committee_scan():
    results = []
    # Progress bar is essential for hackathon demos
    progress_bar = st.progress(0)
    
    for idx, ticker in enumerate(WATCHLIST):
        data = get_investor_data(ticker)
        if not data: continue
        
        votes = []
        # Update UI so the judges see "Thinking" in progress
        with st.status(f"🕵️ Committee debating {ticker}...", expanded=False):
            for name, prompt in AGENT_PROMPTS.items():
                config = types.GenerateContentConfig(
                    # Adjust thinking budget to stay within latency limits
                    thinking_config=types.ThinkingConfig(include_thoughts=True),
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                    system_instruction=prompt
                )
                try:
                    res = client.models.generate_content(
                        model="gemini-2.5-flash", 
                        contents=f"Audit {ticker} with this data: {data}", 
                        config=config
                    )
                    votes.append(1 if "VOTE: BUY" in res.text.upper() else 0)
                except Exception as e:
                    st.error(f"Agent Error for {ticker}: {e}")
            
            if sum(votes) >= 2:
                results.append({"Ticker": ticker, "Votes": sum(votes), "Price": data['Price']})
        
        progress_bar.progress((idx + 1) / len(WATCHLIST))
    
    return sorted(results, key=lambda x: x['Votes'], reverse=True)[:5]

# --- 3. UI IMPROVEMENTS ---
st.title("🛰️ Alpha Scout: Weekly Committee")
# ... [Keep your sidebar and button logic]
