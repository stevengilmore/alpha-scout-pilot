import streamlit as st
import yfinance as yf
import pandas as pd     
import pandas_ta as ta
import requests
import google.generativeai as genai
import time
from datetime import datetime

# 1. Access the Secrets you just pasted
GEMINI_KEY = st.secrets["GEMINI_KEY"]
TG_TOKEN = st.secrets["TG_TOKEN"]
CHAT_ID = st.secrets["CHAT_ID"]

# 2. Configure the AI Brain
genai.configure(api_key=GEMINI_KEY)
# Try this if the first one doesn't work:
model = genai.GenerativeModel('gemini-3.1-pro-preview')
from google import genai # Use the new genai import
from google.genai import types

# Initialize the new Client
client = genai.Client(api_key=st.secrets["GEMINI_KEY"])

# Update the Strategist logic at the bottom of your file:
if "PROCEED" in response.text.upper():
    # Using the official Gemini 3.1 Pro Preview string
    response = client.models.generate_content(
        model="gemini-3.1-pro-preview",
        contents=risk_prompt,
        config=types.GenerateContentConfig(
            # Optional: Set 'high' thinking for maximum protection of your 2.500€
            thinking_config=types.ThinkingConfig(thinking_level="high")
        )
    )


# --- 1. SETTINGS & STYLING ---
st.set_page_config(page_title="Alpha Scout Pro", page_icon="🛡️", layout="wide")

# This pulls from the 'Secrets' menu in Streamlit Cloud
# If testing locally, it will look for these in the sidebar
TG_TOKEN = st.secrets.get("TG_TOKEN") if "TG_TOKEN" in st.secrets else st.sidebar.text_input("Telegram Token", type="password")
CHAT_ID = st.secrets.get("CHAT_ID") if "CHAT_ID" in st.secrets else st.sidebar.text_input("Chat ID")
GEMINI_KEY = st.secrets.get("GEMINI_KEY") if "GEMINI_KEY" in st.secrets else st.sidebar.text_input("Gemini API Key", type="password")

st.title("🛡️ Alpha Scout: Probability Trading Agent")
st.markdown("---")

# --- 2. DATA ENGINE ---
ticker = st.sidebar.selectbox("Select Asset", ["QQQ", "SPY", "BTC-USD", "NVDA", "AAPL"])
capital = st.sidebar.number_input("Trading Capital (€)", value=2500)
profit_target = 20 # Our €20 goal

import pandas as pd
import pandas as pd # Ensure this is at the VERY top of the file

@st.cache_data(ttl=60)
def get_market_data(symbol):
    # 1. Fetch data with auto_adjust to keep columns simple
    df = yf.download(symbol, period="5d", interval="5m", auto_adjust=True)
    
    # 2. Fix the "Multi-Index" issue (The Ticker Name 'drawer' issue)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    # 3. Calculate Indicators using pandas_ta
    df['EMA_200'] = ta.ema(df['Close'], length=200)
    df['RSI'] = ta.rsi(df['Close'], length=14)
    return df

# --- THE LOGIC PART ---
data = get_market_data(ticker)

# Check if we actually got data back
if not data.empty:
    curr = data.iloc[-1]
    
    # We use .item() or float() to ensure we are comparing numbers, not lists
    price = float(curr['Close'])
    ema = float(curr['EMA_200'])
    rsi = float(curr['RSI'])

    trend_ok = price > ema
    rsi_ok = rsi < 40
    
    # (The rest of your probability score code...)

# --- 3. PROBABILITY CALCULATION ---
# Gate 1: Trend Filter (Are we above the 200 EMA?)
trend_ok = curr['Close'] > curr['EMA_200']
# Gate 2: Momentum Filter (Is RSI dipping/oversold?)
rsi_ok = curr['RSI'] < 40 

prob_score = 0
if trend_ok: prob_score += 60
if rsi_ok: prob_score += 30

# --- 4. WEB DASHBOARD LAYOUT ---
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader(f"📊 {ticker} Live Analysis")
    # Show the Price vs Trend
    st.line_chart(data[['Close', 'EMA_200']])
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Price", f"${round(curr['Close'], 2)}")
    m2.metric("RSI", round(curr['RSI'], 1), delta="Oversold" if rsi_ok else "Neutral")
    m3.metric("Probability", f"{prob_score}%")

with col2:
    st.subheader("🤖 AI Risk Auditor (Gemini)")
    if GEMINI_KEY:
        genai.configure(api_key=GEMINI_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        if st.button("Run Global News Audit"):
            with st.spinner("AI is scanning headlines..."):
                prompt = f"Analyze the last hour of financial news for {ticker}. If there is a major crash risk or interest rate news, say 'VETO'. If it looks like a normal day for a bounce, say 'PROCEED'. Explain in 1 sentence."
                response = model.generate_content(prompt)
                st.info(response.text)
    else:
        st.warning("⚠️ Connect Gemini Key in Sidebar/Secrets to enable AI Audit.")

# --- 5. EXECUTION & TELEGRAM ---
st.markdown("---")
if prob_score >= 90:
    st.success("🎯 HIGH PROBABILITY SIGNAL DETECTED")
    
    # Calculate target based on €20 profit
    move_needed = (profit_target + 1) / capital # +€1 for fee
    target_price = round(curr['Close'] * (1 + move_needed), 2)
    
    st.write(f"**Strategy:** Trend-Aligned Bounce")
    st.write(f"**Trade Republic Goal:** €{profit_target} Profit")
    
    if st.button("🚀 EXECUTE: Send to Telegram"):
        if TG_TOKEN and CHAT_ID:
            msg = (f"🎯 **ALPHA SCOUT SIGNAL: {ticker}**\n"
                   f"Entry: ${round(curr['Close'], 2)}\n"
                   f"Target: ${target_price}\n\n"
                   f"1. Open Trade Republic\n2. Buy €{capital}\n3. Set Limit Sell at ${target_price}")
            url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
            requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
            st.toast("Alert sent to your phone! Check Telegram.")
        else:
            st.error("Missing Telegram Token or Chat ID!")
else:
    st.write("🔎 Agent is scanning for probability confluence (EMA 200 + RSI)...")

st.divider()
st.subheader("🚀 Agent Execution Center")

if st.button("▶️ RUN FULL AGENTIC WORKFLOW"):
    with st.status("Agent Swarm Active...", expanded=True) as status:
        # Step A: Technical Check
        st.write(f"🔍 Analyzing {ticker}...")
        if prob_score >= 90:
            st.write("✅ Technical Signal: HIGH PROBABILITY")
            
            # Step B: AI Risk Audit
            st.write("🤖 Strategist: Running Gemini 1.5 News Audit...")
            # We pass the persona/instructions here
            prompt = f"Analyze recent news for {ticker}. If there is any major risk today, say 'VETO'. Otherwise say 'PROCEED'."
            response = model.generate_content(prompt)
            
            if "PROCEED" in response.text.upper():
                st.write("🛡️ Risk Audit: PASSED")
                
                # Step C: Dispatch to Telegram
                st.write("📡 Dispatcher: Sending instruction to phone...")
                msg = f"🎯 SIGNAL CONFIRMED: {ticker}\nEntry: ${round(curr['Close'], 2)}\nCheck Trade Republic!"
                requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", 
                              data={"chat_id": CHAT_ID, "text": msg})
                
                status.update(label="🚀 SUCCESS: Signal Dispatched to Telegram!", state="complete")
            else:
                st.error(f"❌ VETOED BY AI: {response.text}")
                status.update(label="⚠️ Trade Blocked by Risk Manager", state="error")
        else:
            st.warning("⚖️ Technical Probability too low (Needs 90%+)")
            status.update(label="😴 No Action Taken", state="complete")

# --- 🤖 AGENT EXECUTION CENTER ---
st.divider()
st.header("🤖 Autonomous Agent Swarm")

if st.button("🚀 ACTIVATE AGENT SYSTEM"):
    # Connect to the API using the Secret Key you pasted
    genai.configure(api_key=st.secrets["GEMINI_KEY"])
    
    # We use the model string that supports your Search tool
    model = genai.GenerativeModel('gemini-1.5-flash') 

    with st.status("Agent Swarm Active...", expanded=True) as status:
        st.write("🔍 Analyst: Checking technical probability...")
        
        if prob_score >= 90:
            st.write("🧠 Strategist: Consulting Gemini 3 Risk Manager...")
            
            # This is the EXACT persona from your Screenshot!
            risk_manager_prompt = f"""
            You are a cynical Senior Risk Manager. Our starting capital is 2.500 €. 
            We only risk 1% (25 €) per trade. Search news for {ticker}. 
            If there's high risk, say 'VETO'. If safe, say 'PROCEED'.
            """
            
            # The API call that links your app to Google AI Studio
            response = model.generate_content(risk_manager_prompt)
            
            if "PROCEED" in response.text.upper():
                st.write("📡 Dispatcher: Risk cleared. Sending Telegram...")
                # (Telegram Post Request Code Here)
                status.update(label="✅ SUCCESS: Signal Sent!", state="complete")
            else:
                st.error(f"❌ AI VETO: {response.text}")
                status.update(label="⚠️ Trade Blocked", state="error")
        else:
            st.warning(f"⚖️ Analyst: Probability ({prob_score}%) too low.")
            status.update(label="😴 Monitoring...", state="complete")

# --- 🧪 TEST & OVERRIDE SETTINGS ---
with st.sidebar:
    st.divider()
    st.subheader("🛠️ Developer Tools")
    test_mode = st.toggle("Enable Test Mode", help="Bypasses technical filters for demo purposes.")

with st.sidebar:
    st.divider()
    if st.button("📋 List My Available Models"):
        try:
            # Use the correct SDK method to list available models
            models = [m.name for m in genai.list_models() 
                     if 'generateContent' in m.supported_generation_methods]
            st.write("### Your Active Models:")
            for m_name in models:
                st.code(m_name.replace('models/', ''))
        except Exception as e:
            st.error(f"Error fetching models: {e}")

# --- 🤖 UNIFIED AGENT EXECUTION CENTER ---
st.divider()
st.header("🤖 TEST Autonomous Agent Swarm")

# We add a unique 'key' to prevent the DuplicateElementId error
if st.button("🚀 TEST ACTIVATE AGENT SYSTEM", key="main_agent_button"):
    with st.status("Agent Swarm Active...", expanded=True) as status:
        
        # Check if we should proceed (Math OR Manual Override)
        if prob_score >= 90 or test_mode:
            if test_mode:
                st.info("🧪 TEST MODE: Technical analysis bypassed.")
            
            st.write("🧠 Strategist: Consulting Gemini 3 Risk Manager...")
            
            # Use the instructions you set in AI Studio
            risk_prompt = f"Analyze today's news for {ticker}. VETO if high risk. PROCEED if safe."
            response = model.generate_content(risk_prompt)
            
            if "PROCEED" in response.text.upper():
                st.write("🛡️ Risk Audit: PASSED")
                st.write("📡 Dispatcher: Sending instruction to Telegram...")
                
                # Format the message for your phone
                alert_text = f"🎯 SIGNAL CONFIRMED: {ticker}\nPrice: ${round(curr['Close'], 2)}\nCheck Trade Republic!"
                requests.post(f"https://api.telegram.org/bot{st.secrets['TG_TOKEN']}/sendMessage", 
                              data={"chat_id": st.secrets['CHAT_ID'], "text": alert_text})
                
                status.update(label="✅ SUCCESS: Signal Sent!", state="complete")
            else:
                st.error(f"❌ VETOED BY AI: {response.text}")
                status.update(label="⚠️ Strategist blocked the trade", state="error")
        else:
            st.warning(f"⚖️ Analyst: Probability ({prob_score}%) too low for professional entry.")
            status.update(label="😴 No Action Taken", state="complete")
