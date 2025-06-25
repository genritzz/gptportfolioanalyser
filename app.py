import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import requests
import time

# === CONFIG ===
ALPHA_VANTAGE_API_KEY = st.secrets["ALPHA_VANTAGE_API_KEY"] if "ALPHA_VANTAGE_API_KEY" in st.secrets else st.text_input("Enter Alpha Vantage API Key")
SLEEP_BETWEEN_CALLS = 15

# === FUNCTIONS ===
def get_yahoo_data(ticker):
    stock = yf.Ticker(ticker)
    info = stock.info
    return {
        "price": info.get("regularMarketPrice"),
        "sector": info.get("sector", "Unknown"),
        "marketCap": info.get("marketCap"),
        "peRatio": info.get("trailingPE")
    }

def classify_market_cap(cap):
    if cap is None:
        return "Unknown"
    elif cap >= 10e9:
        return "Large Cap"
    elif cap >= 2e9:
        return "Mid Cap"
    else:
        return "Small Cap"

def get_sentiment_alpha(ticker, api_key):
    url = f'https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={ticker}&apikey={api_key}'
    try:
        r = requests.get(url)
        data = r.json()
        sentiments = [a.get('overall_sentiment_score', 0) for a in data.get('feed', [])]
        return sum(sentiments) / len(sentiments) if sentiments else None
    except:
        return None

def recommend_action(sentiment, return_pct):
    if sentiment is None:
        return "No Data"
    elif sentiment > 0.3 and return_pct > 0:
        return "🚀 Increase Exposure"
    elif sentiment < -0.3 and return_pct < 0:
        return "🔻 Cut Exposure"
    elif -0.2 < sentiment < 0.2:
        return "⏸️ Hold"
    else:
        return "👀 Watch Closely"

# === STREAMLIT UI ===
st.title("📊 Portfolio Dashboard")
st.markdown("Analyze your portfolio by sector, market cap, P/E, and sentiment.")

with st.sidebar:
    st.header("Add Stock")
    ticker = st.text_input("Ticker Symbol").upper()
    buy_price = st.number_input("Buy Price", min_value=0.0, step=0.1)
    quantity = st.number_input("Quantity", min_value=1, step=1)
    add = st.button("Add to Portfolio")

if "portfolio" not in st.session_state:
    st.session_state.portfolio = []

if add and ticker:
    st.session_state.portfolio.append({"ticker": ticker, "buy_price": buy_price, "quantity": quantity})

if st.session_state.portfolio:
    rows = []
    for asset in st.session_state.portfolio:
        ticker = asset["ticker"]
        buy_price = asset["buy_price"]
        quantity = asset["quantity"]

        data = get_yahoo_data(ticker)
        price = data["price"]
        sector = data["sector"]
        mcap = data["marketCap"]
        pe = data["peRatio"]
        cap_class = classify_market_cap(mcap)

        sentiment = get_sentiment_alpha(ticker, ALPHA_VANTAGE_API_KEY)
        time.sleep(15)

        if price:
            value = price * quantity
            pnl = (price - buy_price) * quantity
            return_pct = (pnl / (buy_price * quantity)) * 100
        else:
            value = pnl = return_pct = None

        action = recommend_action(sentiment, return_pct)

        rows.append({
            "Ticker": ticker,
            "Sector": sector,
            "Market Cap Class": cap_class,
            "P/E Ratio": pe,
            "Quantity": quantity,
            "Buy Price": buy_price,
            "Current Price": price,
            "Value ($)": round(value, 2) if value else "N/A",
            "Return (%)": round(return_pct, 2) if return_pct else "N/A",
            "Sentiment": round(sentiment, 3) if sentiment else "N/A",
            "Action": action
        })

    df = pd.DataFrame(rows)
    st.subheader("📋 Portfolio Overview")
    st.dataframe(df)

    # === Charts ===
    st.subheader("📊 Sector Allocation")
    sector_chart = df.groupby("Sector")["Value ($)"].sum().reset_index()
    fig1 = px.pie(sector_chart, names="Sector", values="Value ($)", title="Sector Allocation")
    st.plotly_chart(fig1)

    st.subheader("🏛️ Market Cap Distribution")
    cap_chart = df.groupby("Market Cap Class")["Value ($)"].sum().reset_index()
    fig2 = px.bar(cap_chart, x="Market Cap Class", y="Value ($)", title="Market Cap Allocation")
    st.plotly_chart(fig2)

    st.subheader("📈 P/E vs Return")
    pe_data = df[(df["P/E Ratio"].notna()) & (df["Return (%)"] != "N/A")]
    if not pe_data.empty:
        fig3 = px.scatter(pe_data, x="P/E Ratio", y="Return (%)", text="Ticker", title="P/E vs Return")
        st.plotly_chart(fig3)

    st.subheader("🔁 Rebalancing Suggestions")
    for row in rows:
        st.markdown(f"**{row['Ticker']}** → {row['Action']}")
else:
    st.info("Add stocks from the sidebar to begin.")
