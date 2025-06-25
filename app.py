import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime

# Initialize session state
if "portfolio" not in st.session_state:
    st.session_state.portfolio = {}
if "realized_profit" not in st.session_state:
    st.session_state.realized_profit = 0.0

# Load API key
if "ALPHA_VANTAGE_API_KEY" in st.secrets:
    ALPHA_VANTAGE_API_KEY = st.secrets["ALPHA_VANTAGE_API_KEY"]
else:
    ALPHA_VANTAGE_API_KEY = st.text_input("Enter Alpha Vantage API Key")

st.title("📊 Portfolio Dashboard")
st.caption("Analyze your portfolio by sector, market cap, P/E, and sentiment.")

# Sidebar inputs
st.sidebar.header("Add Transaction")
ticker = st.sidebar.text_input("Ticker Symbol").upper()
buy_price = st.sidebar.number_input("Price", min_value=0.0)
quantity = st.sidebar.number_input("Quantity", min_value=1, step=1)
transaction_type = st.sidebar.selectbox("Transaction Type", ["Buy", "Sell"])

if st.sidebar.button("Add to Portfolio"):
    if ticker:
        stock = yf.Ticker(ticker)
        info = stock.info
        name = info.get("longName", ticker)

        if ticker not in st.session_state.portfolio:
            st.session_state.portfolio[ticker] = {
                "name": name,
                "quantity": 0,
                "average_cost": 0,
                "transactions": []
            }

        record = st.session_state.portfolio[ticker]

        if transaction_type == "Buy":
            total_cost = record["average_cost"] * record["quantity"] + buy_price * quantity
            record["quantity"] += quantity
            record["average_cost"] = total_cost / record["quantity"]

        elif transaction_type == "Sell":
            sell_quantity = min(quantity, record["quantity"])
            if sell_quantity > 0:
                profit = (buy_price - record["average_cost"]) * sell_quantity
                st.session_state.realized_profit += profit
                record["quantity"] -= sell_quantity
                if record["quantity"] == 0:
                    record["average_cost"] = 0

        record["transactions"].append({
            "type": transaction_type.lower(),
            "price": buy_price,
            "quantity": quantity,
            "date": datetime.today().strftime("%Y-%m-%d")
        })

# Display portfolio
if not st.session_state.portfolio:
    st.info("Add stocks from the sidebar to begin.")
else:
    data = []
    for ticker, record in st.session_state.portfolio.items():
        if record["quantity"] == 0:
            continue
        stock = yf.Ticker(ticker)
        info = stock.info
        price = info.get("regularMarketPrice", 0)
        sector = info.get("sector", "N/A")
        market_cap = info.get("marketCap", 0)
        pe_ratio = info.get("trailingPE", None)

        # Determine market cap category
        if market_cap >= 10**10:
            cap_category = "Large Cap"
        elif market_cap >= 2*10**9:
            cap_category = "Mid Cap"
        else:
            cap_category = "Small Cap"

        # Alpha Vantage Sentiment
        sentiment_score = None
        if ALPHA_VANTAGE_API_KEY:
            url = f"https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={ticker}&apikey={ALPHA_VANTAGE_API_KEY}"
            try:
                response = requests.get(url)
                articles = response.json().get("feed", [])
                if articles:
                    sentiment_score = float(articles[0].get("overall_sentiment_score", 0))
            except:
                sentiment_score = None

        current_value = record["quantity"] * price
        unrealized_pnl = (price - record["average_cost"]) * record["quantity"]

        data.append({
            "Ticker": ticker,
            "Company": record["name"],
            "Quantity": record["quantity"],
            "Avg Cost": round(record["average_cost"], 2),
            "Current Price": round(price, 2),
            "Value": round(current_value, 2),
            "Unrealized PnL": round(unrealized_pnl, 2),
            "Sector": sector,
            "Market Cap": cap_category,
            "P/E": pe_ratio,
            "Sentiment": sentiment_score
        })

    df = pd.DataFrame(data)
    st.dataframe(df)

    # Portfolio summary
    total_value = df["Value"].sum()
    st.metric("Total Portfolio Market Value", f"${total_value:,.2f}")
    st.metric("Realized Profit", f"${st.session_state.realized_profit:,.2f}")
    st.metric("Combined Portfolio Value", f"${total_value + st.session_state.realized_profit:,.2f}")

    # Charts
    if "Sector" in df:
        fig_sector = px.pie(df, names="Sector", values="Value", title="Sector Allocation")
        st.plotly_chart(fig_sector)

    if "Market Cap" in df:
        fig_cap = px.histogram(df, x="Market Cap", y="Value", title="Market Cap Distribution", histfunc="sum")
        st.plotly_chart(fig_cap)

    if "P/E" in df:
        fig_pe = px.scatter(df, x="P/E", y="Unrealized PnL", text="Ticker", title="P/E vs. Unrealized PnL")
        st.plotly_chart(fig_pe)

