import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime

# Page config
st.set_page_config(layout="wide", page_title="InvestoPal", page_icon="📈")

# ---------- Background & Styling ----------
BACKGROUND_URL = "https://images.unsplash.com/photo-1559526324-593bc073d938?auto=format&fit=crop&w=1950&q=80"

st.markdown(f"""
<style>
body {{
    background-image: url('{BACKGROUND_URL}');
    background-size: cover;
    background-attachment: fixed;
}}
.app-overlay {{
    backdrop-filter: blur(6px);
    background: rgba(5,15,25,0.55);
    padding: 1.25rem;
    border-radius: 10px;
}}
.header {{
    text-align: left;
    color: #ffffff;
    padding-bottom: 0.5rem;
}}
.card {{
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    padding: 1rem;
    border-radius:8px;
    color: #fff;
}}
.metric {{
    font-size: 1.25rem;
    font-weight:700;
}}
.news-ticker {{
    overflow-x:auto;
    white-space:nowrap;
    padding:0.5rem 0.25rem;
}}
.news-item {{
    display:inline-block;
    margin-right:1rem;
}}
.small {{
    font-size:0.85rem;
    color:#cbd5e1;
}}
</style>
""", unsafe_allow_html=True)

# Main container
st.markdown('<div class="app-overlay">', unsafe_allow_html=True)

# ---------- Header ----------
col1, col2 = st.columns([3,1])
with col1:
    st.markdown('<div class="header"><h1>InvestoPal</h1><h4>Your AI-powered investment dashboard</h4></div>', unsafe_allow_html=True)

# ---------- Sidebar Inputs ----------
st.sidebar.markdown("## 🔧 Investor Inputs")
currency = st.sidebar.selectbox("Currency", ["INR (₹)","USD ($)"], index=0)
currency_sym = "₹" if "INR" in currency else "$"

investment_amount = st.sidebar.number_input("Lump-sum Investment", min_value=0, value=50000, step=1000, format="%d")
monthly_sip = st.sidebar.number_input("Monthly SIP", min_value=0, value=10000, step=500, format="%d")
investment_years = st.sidebar.slider("Investment Period (years)", 1, 40, 15)
expected_return_pct = st.sidebar.slider("Expected Annual Return (%)", 0.0, 40.0, 10.0, step=0.1)
risk_level = st.sidebar.selectbox("Risk Tolerance", ["Conservative","Moderate","Aggressive"])
compare_tickers = st.sidebar.text_input("Compare (comma-separated tickers)", placeholder="AAPL,MSFT,GOOGL")

# Stock input
st.markdown("### 🔎 Stock Analysis")
ticker = st.text_input("Enter stock ticker (e.g. AAPL, TSLA, RELIANCE.NS):", value="AAPL").upper().strip()

date_col1, date_col2 = st.columns(2)
with date_col1:
    start_date = st.date_input("Start date", pd.to_datetime("2020-01-01"))
with date_col2:
    end_date = st.date_input("End date", pd.to_datetime("today"))

run = st.button("🚀 Run Analysis")

# ---------- Helpers ----------
@st.cache_data(show_spinner=False)
def fetch_price_history(ticker, start_date, end_date):
    try:
        df = yf.download(ticker, start=start_date, end=end_date, progress=False)
        if df.empty:
            return None
        return df
    except:
        return None

@st.cache_data(show_spinner=False)
def fetch_ticker_obj(ticker):
    try:
        return yf.Ticker(ticker)
    except:
        return None

def get_latest_news(ticker, limit=3):
    t = fetch_ticker_obj(ticker)
    if not t:
        return []
    news = getattr(t, "news", None)
    if not news:
        return []
    cleaned = []
    for item in news[:limit]:
        if not isinstance(item, dict):
            continue
        title = item.get("title", "No title")
        link = item.get("link", "#")
        publisher = item.get("publisher", "Unknown")
        ts = item.get("providerPublishTime")
        published = None
        if isinstance(ts, (int, float)):
            try:
                published = datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d %H:%M")
            except:
                published = None
        cleaned.append({"title": title, "link": link, "publisher": publisher, "published": published})
    return cleaned

def compute_metrics_from_series(series):
    s = series.dropna()
    if s.empty:
        return None
    returns = s.pct_change().dropna()
    vol = returns.std() * np.sqrt(252)
    ann_return = returns.mean() * 252
    sharpe = (returns.mean()/returns.std())*np.sqrt(252) if returns.std() != 0 else 0.0
    max_dd = ((s / s.cummax()) - 1).min()
    rolling_vol = returns.rolling(30).std() * np.sqrt(252)
    total_return = (s.iloc[-1] / s.iloc[0] - 1) * 100
    return {"volatility": vol, "avg_return": ann_return, "sharpe_ratio": sharpe, "max_drawdown": max_dd, "rolling_volatility": rolling_vol, "total_return": total_return}

def asset_allocation_suggestion(risk):
    if risk == "Conservative":
        return {"Equity": 30, "Bonds": 55, "Cash": 15}
    elif risk == "Moderate":
        return {"Equity": 60, "Bonds": 30, "Cash": 10}
    else:
        return {"Equity": 85, "Bonds": 10, "Cash": 5}

def create_advanced_chart(stock_data, metrics, ticker):
    if isinstance(stock_data.columns, pd.MultiIndex):
        if ("Adj Close", ticker) in stock_data.columns:
            price_data = stock_data[("Adj Close", ticker)]
        elif ("Close", ticker) in stock_data.columns:
            price_data = stock_data[("Close", ticker)]
        else:
            return None
        volume_data = stock_data[("Volume", ticker)] if ("Volume", ticker) in stock_data.columns else None
    else:
        price_data = stock_data["Adj Close"] if "Adj Close" in stock_data.columns else stock_data["Close"]
        volume_data = stock_data["Volume"] if "Volume" in stock_data.columns else None

    fig = make_subplots(rows=3, cols=1, subplot_titles=(f'{ticker} Price', 'Volume', 'Rolling Volatility'))
    fig.add_trace(go.Scatter(x=stock_data.index, y=price_data, name='Price'), row=1, col=1)
    if volume_data is not None:
        fig.add_trace(go.Bar(x=stock_data.index, y=volume_data, name='Volume'), row=2, col=1)
    fig.add_trace(go.Scatter(x=stock_data.index, y=metrics['rolling_volatility'], name='Volatility'), row=3, col=1)
    fig.update_layout(height=800, template='plotly_white')
    return fig

# ---------- Run ----------
if run and ticker:
    hist = fetch_price_history(ticker, start_date, end_date)
    t_obj = fetch_ticker_obj(ticker)
    if hist is None:
        st.error("No historical data found for this ticker.")
    else:
        price = hist["Adj Close"] if "Adj Close" in hist.columns else hist["Close"]
        metrics = compute_metrics_from_series(price)
        if metrics:
            # Metric cards
            live_price = None
            try:
                fast = getattr(t_obj, "fast_info", None)
                if fast and getattr(fast, "last_price", None):
                    live_price = fast.last_price
                else:
                    recent = t_obj.history(period="1d")
                    if not recent.empty:
                        live_price = recent['Close'].iloc[-1]
            except:
                live_price = None

            c1, c2, c3, c4 = st.columns(4)
            c1.markdown(f"<div class='card'><div class='metric'>{ticker} {currency_sym}{(live_price if live_price else price.iloc[-1]):,.2f}</div><div class='small'>Live Price</div></div>", unsafe_allow_html=True)
            c2.markdown(f"<div class='card'><div class='metric'>{metrics['total_return']:.2f}%</div><div class='small'>Total Return</div></div>", unsafe_allow_html=True)
            c3.markdown(f"<div class='card'><div class='metric'>{metrics['volatility']*100:.2f}%</div><div class='small'>Volatility</div></div>", unsafe_allow_html=True)
            c4.markdown(f"<div class='card'><div class='metric'>{metrics['sharpe_ratio']:.2f}</div><div class='small'>Sharpe Ratio</div></div>", unsafe_allow_html=True)

            # News ticker
            news_items = get_latest_news(ticker, limit=3)
            st.markdown("<div class='news-ticker'>", unsafe_allow_html=True)
            for it in news_items:
                st.markdown(f"<span class='news-item'><a href='{it['link']}' target='_blank' style='color:#cbd5e1'>{it['title']}</a> <span class='small'>— {it['publisher']} {('• '+it['published']) if it['published'] else ''}</span></span>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

            # Asset allocation
            st.subheader("Asset Allocation Suggestion")
            allocation = asset_allocation_suggestion(risk_level)
            alloc_fig = px.pie(values=list(allocation.values()), names=list(allocation.keys()), hole=0.4)
            st.plotly_chart(alloc_fig, use_container_width=True)

            # Projection
            st.subheader("Investment Projection")
            months = investment_years * 12
            monthly_return = (expected_return_pct/100) / 12
            vals = [float(investment_amount)]
            cur = float(investment_amount)
            for _ in range(months):
                cur = cur * (1 + monthly_return) + float(monthly_sip)
                vals.append(cur)
            proj_fig = go.Figure()
            proj_fig.add_trace(go.Scatter(x=list(range(len(vals))), y=vals, fill='tozeroy'))
            proj_fig.update_layout(xaxis_title="Months", yaxis_title=f"Portfolio Value ({currency_sym})", template='plotly_white')
            st.plotly_chart(proj_fig, use_container_width=True)

            # Technical chart
            chart = create_advanced_chart(hist, metrics, ticker)
            if chart:
                st.plotly_chart(chart, use_container_width=True)

            # Comparison
            if compare_tickers:
                comps = []
                for c in [t.strip().upper() for t in compare_tickers.split(",") if t.strip()]:
                    chist = fetch_price_history(c, start_date, end_date)
                    if chist is not None:
                        cprice = chist["Adj Close"] if "Adj Close" in chist.columns else chist["Close"]
                        cm = compute_metrics_from_series(cprice)
                        if cm:
                            comps.append({"Ticker": c, "Total Return %": f"{cm['total_return']:.2f}", "Sharpe Ratio": f"{cm['sharpe_ratio']:.2f}"})
                if comps:
                    st.table(pd.DataFrame(comps))

# Close main overlay
st.markdown('</div>', unsafe_allow_html=True)


