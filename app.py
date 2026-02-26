import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests
from google import genai
from google.genai import types

# --- 1. SETTINGS & SECRETS ---
st.set_page_config(page_title="Alpha Scout Pro", page_icon="🛡️", layout="wide")

GEMINI_KEY = st.secrets.get("GEMINI_KEY")
TG_TOKEN = st.secrets.get("TG_TOKEN")
CHAT_ID = st.secrets.get("CHAT_ID")

# --- 2. THE GLOBAL WATCHLIST (Institutional Anchors) ---
# Combined US, EU, and Crypto
ASSET_MAP = {
    # Cryptocurrencies
    "BTC-USD": "Bitcoin", "ETH-USD": "Ethereum", "USDT-USD": "Tether", 
    "XRP-USD": "XRP", "BNB-USD": "Binance Coin",
    # S&P 10 (US Mega-Caps)
    "NVDA": "NVIDIA Corp", "AAPL": "Apple Inc.", "MSFT": "Microsoft Corp", 
    "AMZN": "Amazon.com Inc.", "GOOGL": "Alphabet Inc.", "META": "Meta Platforms", 
    "AVGO": "Broadcom Inc.", "TSLA": "Tesla Inc.", "BRK-B": "Berkshire Hathaway", 
    "LLY": "Eli Lilly & Co.",
    # FTSE 100 (UK) & DAX 40 (GER)
    "AZN.L": "AstraZeneca", "HSBA.L": "HSBC Holdings", "SHEL.L": "Shell PLC",
    "SAP.DE": "SAP SE", "ALV.DE": "Allianz SE"
}

# --- 3. DATA & VOLATILITY ENGINE ---
@st.cache_data(ttl=300)
def get_market_pulse():
    pulse_data = []
    # Scans for 24h volatility
    for ticker in list(ASSET_MAP.keys()):
        try:
            df = yf.download(ticker, period="2d", interval="1d", progress=False)
            if len(df) > 1:
                change = ((df['Close'].iloc[-1] - df['Close'].iloc[-2]) / df['Close'].iloc[-2]) * 100
                pulse_data.append({"Ticker": ticker, "Change": float(change)})
        except: continue
    return pd.DataFrame(pulse_data).sort_values(by="Change", key=abs, ascending=False)

def get_technical_analysis(ticker):
    df = yf.download(ticker, period="5d", interval="1h", progress=
