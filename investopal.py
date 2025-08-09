import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

st.set_page_config(layout="wide", page_title="InvestoPal", page_icon="📈")

# ---------- Styling ----------
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 1rem 0;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .badge {
        display: inline-block;
        padding: 0.4rem 0.8rem;
        border-radius: 8px;
        color: white;
        font-weight: bold;
    }
    .green { background-color: #28a745; }
    .red { background-color: #dc3545; }
    .yellow { background-color: #ffc107; color: black; }
</style>
""", unsafe_allow_html=True)

st.markdown(
    "<div class=\"main-header\"><h1>📈 InvestoPal: Smart Investment Platform</h1><p>Your AI-powered investment companion</p></div>",
    unsafe_allow_html=True
)

# ---------- Risk Categories ----------
RISK_CATEGORIES = {
    "Conservative": {
        "description": "Low risk, stable returns.",
        "examples": ["AAPL", "MSFT", "JNJ"],
        "color": "#28a745"
    },
    "Moderate": {
        "description": "Balanced risk-reward.",
        "examples": ["GOOGL", "AMZN", "NVDA"],
        "color": "#ffc107"
    },
    "Aggressive": {
        "description": "High risk, high returns.",
        "examples": ["TSLA", "GME", "AMC"],
        "color": "#dc3545"
    }
}

# ---------- Caching ----------
@st.cache_data(show_spinner=False)
def get_stock_data(ticker, start_date, end_date):
    try:
        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date)
        data = yf.download(ticker, start=start_date, end=end_date, progress=False)
        if data is None or data.empty:
            return None
        return data
    except Exception:
        return None

def calculate_risk_metrics(data, ticker):
    if data is None or data.empty:
        return None

    # Safely get adjusted close (support MultiIndex from yfinance)
    if isinstance(data.columns, pd.MultiIndex):
        if ("Adj Close", ticker) in data.columns:
            adj_close = data[("Adj Close", ticker)]
        elif ("Close", ticker) in data.columns:
            adj_close = data[("Close", ticker)]
        else:
            return None
    else:
        if "Adj Close" in data.columns:
            adj_close = data["Adj Close"]
        elif "Close" in data.columns:
            adj_close = data["Close"]
        else:
            return None

    adj_close = adj_close.dropna()
    if adj_close.empty:
        return None

    returns = adj_close.pct_change().dropna()
    rolling_vol = returns.rolling(30).std() * np.sqrt(252)

    return {
        "volatility": returns.std() * np.sqrt(252),
        "avg_return": returns.mean() * 252,
        "max_drawdown": ((adj_close / adj_close.cummax()) - 1).min(),
        "sharpe_ratio": (returns.mean() / returns.std()) * np.sqrt(252) if returns.std() != 0 else 0,
        "rolling_volatility": rolling_vol,
        "total_return": (adj_close.iloc[-1] / adj_close.iloc[0] - 1) * 100
    }

def categorize_risk(volatility):
    if volatility < 0.2:
        return "Conservative"
    elif volatility < 0.4:
        return "Moderate"
    return "Aggressive"

def create_advanced_chart(stock_data, metrics, ticker):
    # Get price and volume with safe access
    if isinstance(stock_data.columns, pd.MultiIndex):
        if ("Adj Close", ticker) in stock_data.columns:
            price_data = stock_data[("Adj Close", ticker)]
        elif ("Close", ticker) in stock_data.columns:
            price_data = stock_data[("Close", ticker)]
        else:
            return None
        volume_data = stock_data[("Volume", ticker)] if ("Volume", ticker) in stock_data.columns else None
    else:
        if "Adj Close" in stock_data.columns:
            price_data = stock_data["Adj Close"]
        elif "Close" in stock_data.columns:
            price_data = stock_data["Close"]
        else:
            return None
        volume_data = stock_data["Volume"] if "Volume" in stock_data.columns else None

    fig = make_subplots(rows=3, cols=1, subplot_titles=(f'{ticker} Price', 'Volume', 'Rolling Volatility'))
    fig.add_trace(go.Scatter(x=stock_data.index, y=price_data, name='Price'), row=1, col=1)
    if volume_data is not None:
        fig.add_trace(go.Bar(x=stock_data.index, y=volume_data, name='Volume'), row=2, col=1)
    # rolling_volatility might be a series indexed by dates; align with stock_data.index if needed
    rv = metrics.get('rolling_volatility')
    if rv is not None:
        # If rv is same index, plot directly; otherwise clip/align
        try:
            fig.add_trace(go.Scatter(x=rv.index, y=rv, name='Volatility'), row=3, col=1)
        except Exception:
            fig.add_trace(go.Scatter(x=stock_data.index, y=(rv.reindex(stock_data.index).fillna(method='ffill') if hasattr(rv, 'reindex') else rv), name='Volatility'), row=3, col=1)
    fig.update_layout(height=800, template='plotly_white')
    return fig

def generate_ai_advice(ticker, risk_category, metrics, selected_risk):
    advice = []
    if risk_category != selected_risk:
        advice.append(f"⚠️ Risk mismatch for {ticker}.")
    if metrics["sharpe_ratio"] > 1.5:
        advice.append(f"✅ Strong risk-adjusted returns.")
    elif metrics["sharpe_ratio"] < 0.5:
        advice.append(f"⚠️ Poor risk-adjusted returns.")
    return advice

def get_latest_news(ticker, limit=3):
    """
    Return up to `limit` latest news items for a ticker as a list of dicts.
    Each dict may contain keys like 'title', 'link', 'publisher', 'providerPublishTime'.
    This function uses safe .get() access to avoid KeyError if fields are missing.
    """
    try:
        ticker_obj = yf.Ticker(ticker)
        news = getattr(ticker_obj, "news", None)
        if not news:
            return []
        # Normalize/ensure items are dict-like
        cleaned = []
        for item in news[:limit]:
            if not isinstance(item, dict):
                continue
            title = item.get("title") or item.get("headline") or item.get("summary") or "No title"
            link = item.get("link") or item.get("url") or "#"
            publisher = item.get("publisher") or item.get("source") or "Unknown"
            ts = item.get("providerPublishTime") or item.get("pubDate") or None
            published = None
            if isinstance(ts, (int, float)):
                try:
                    published = datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d %H:%M")
                except Exception:
                    published = None
            cleaned.append({"title": title, "link": link, "publisher": publisher, "published": published})
        return cleaned
    except Exception:
        return []

# ---------- Sidebar ----------
st.sidebar.header("🎯 Investment Profile")
selected_risk = st.sidebar.selectbox("Risk level:", list(RISK_CATEGORIES.keys()))
risk_info = RISK_CATEGORIES[selected_risk]
st.sidebar.write(risk_info["description"])

investment_amount = st.sidebar.number_input("Initial Investment (₹):", min_value=1000, value=50000)
monthly_sip = st.sidebar.number_input("Monthly SIP (₹):", min_value=0, value=10000)
investment_years = st.sidebar.slider("Investment Period (Years):", min_value=1, max_value=30, value=15)
compare_tickers = st.sidebar.text_input("Compare with (comma-separated):")

# ---------- Main UI ----------
ticker = st.text_input("Stock Ticker:", value=risk_info['examples'][0]).upper()
date_preset = st.selectbox("Quick Select:", ["Custom", "1 Year", "3 Years", "5 Years", "10 Years"])

if date_preset != "Custom":
    years_back = {"1 Year": 1, "3 Years": 3, "5 Years": 5, "10 Years": 10}[date_preset]
    end_date = pd.to_datetime("today")
    start_date = end_date - pd.DateOffset(years=years_back)
else:
    start_date = st.date_input("Start Date:", pd.to_datetime("2020-01-01"))
    end_date = st.date_input("End Date:", pd.to_datetime("2024-01-01"))

if st.button("🚀 Run Analysis"):
    stock_data = get_stock_data(ticker, start_date, end_date)
    if stock_data is not None:
        metrics = calculate_risk_metrics(stock_data, ticker)
        if metrics:
            risk_category = categorize_risk(metrics["volatility"])

            # 1. Key Stats Table
            st.subheader("📊 Key Statistics")
            stats_df = pd.DataFrame({
                "Metric": ["Total Return %", "Annualized Return %", "Volatility %", "Sharpe Ratio", "Max Drawdown %"],
                "Value": [
                    f"{metrics['total_return']:.2f}%",
                    f"{metrics['avg_return']*100:.2f}%",
                    f"{metrics['volatility']*100:.2f}%",
                    f"{metrics['sharpe_ratio']:.2f}",
                    f"{metrics['max_drawdown']*100:.2f}%"
                ]
            })
            st.table(stats_df)

            # 2. Risk Gauge (color changes by volatility)
            st.subheader("📈 Risk Gauge")
            vol_pct = float(metrics['volatility'] * 100)
            if vol_pct < 20:
                gauge_color = "green"
            elif vol_pct < 40:
                gauge_color = "yellow"
            else:
                gauge_color = "red"

            gauge_fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=vol_pct,
                gauge={'axis': {'range': [0, 100]}, 'bar': {'color': gauge_color}}
            ))
            gauge_fig.update_layout(title_text="Volatility %", height=300)
            st.plotly_chart(gauge_fig, use_container_width=True)

            # 3. Recommendation Badge
            st.subheader("💡 Recommendation")
            if (risk_category == selected_risk) and (metrics['sharpe_ratio'] > 1):
                st.markdown('<div class="badge green">✅ Good Fit</div>', unsafe_allow_html=True)
            else:
                # Slightly more informative badge text
                reason = []
                if risk_category != selected_risk:
                    reason.append("risk mismatch")
                if metrics['sharpe_ratio'] <= 1:
                    reason.append("Sharpe ≤ 1")
                st.markdown(f'<div class="badge red">⚠️ Risky — {" & ".join(reason)}</div>', unsafe_allow_html=True)

            # 4. News Headlines (up to 3)
            st.subheader("📰 Latest News")
            news_list = get_latest_news(ticker, limit=3)
            if news_list:
                for n in news_list:
                    title = n.get('title', 'No title')
                    link = n.get('link', '#')
                    publisher = n.get('publisher', 'Unknown')
                    published = n.get('published')
                    if published:
                        st.markdown(f"[{title}]({link}) — *{publisher}* • {published}")
                    else:
                        st.markdown(f"[{title}]({link}) — *{publisher}*")
            else:
                st.write("No recent news found.")

            # Graphs Below
            chart = create_advanced_chart(stock_data, metrics, ticker)
            if chart:
                st.plotly_chart(chart)

        # Portfolio Comparison (unchanged)
        if compare_tickers:
            st.subheader("📊 Portfolio Comparison")
            for comp in [t.strip().upper() for t in compare_tickers.split(",")]:
                comp_data = get_stock_data(comp, start_date, end_date)
                if comp_data is not None:
                    comp_metrics = calculate_risk_metrics(comp_data, comp)
                    if comp_metrics:
                        st.write(f"{comp}: {comp_metrics['total_return']:.2f}% Return")
    else:
        st.error("No data available for the selected ticker and date range.")
