import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px

st.set_page_config(layout="wide", page_title="InvestoPal", page_icon="📈")

# Custom CSS for better styling
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
    .metric-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #667eea;
    }
    .risk-badge {
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-weight: bold;
        color: white;
    }
    .conservative { background-color: #28a745; }
    .moderate { background-color: #ffc107; color: black; }
    .aggressive { background-color: #dc3545; }
</style>
""", unsafe_allow_html=True)

st.markdown("<div class=\"main-header\"><h1>📈 InvestoPal: Smart Investment Platform</h1><p>Your AI-powered investment companion for smarter financial decisions</p></div>", unsafe_allow_html=True)

# Risk categories with enhanced data
RISK_CATEGORIES = {
    "Conservative": {
        "description": "Low risk, stable returns. Perfect for beginners and risk-averse investors.",
        "examples": ["AAPL", "MSFT", "JNJ", "PG", "KO", "WMT", "VZ"],
        "color": "#28a745",
        "expected_return": "6-10%",
        "volatility": "Low (10-20%)"
    },
    "Moderate": {
        "description": "Balanced risk-reward. Mix of growth and stability for experienced investors.",
        "examples": ["GOOGL", "AMZN", "NVDA", "V", "MA", "NFLX", "CRM"],
        "color": "#ffc107",
        "expected_return": "10-15%",
        "volatility": "Medium (20-40%)"
    },
    "Aggressive": {
        "description": "High risk, high potential returns. For experienced investors with high risk tolerance.",
        "examples": ["TSLA", "GME", "AMC", "PLTR", "COIN", "ARKK", "SPCE"],
        "color": "#dc3545",
        "expected_return": "15%+",
        "volatility": "High (40%+)"
    }
}

def get_stock_data(ticker, start_date, end_date):
    """Fetches historical stock data for a given ticker."""
    try:
        data = yf.download(ticker, start=start_date, end=end_date)
        if data.empty:
            st.warning(f"No data found for {ticker} between {start_date} and {end_date}.")
            return None
        return data
    except Exception as e:
        st.error(f"Error fetching data for {ticker}: {e}")
        return None

def calculate_risk_metrics(data, ticker):
    """Calculate comprehensive risk metrics for the stock."""
    if data is None or data.empty:
        return None
    
    # Extract 'Adj Close' price series
    if isinstance(data.columns, pd.MultiIndex):
        # Try to access using MultiIndex (e.g., ('Adj Close', 'AAPL'))
        try:
            adj_close = data.loc[:, ('Adj Close', ticker)]
        except KeyError:
            # If the specific ticker is not found in the second level of MultiIndex, it might be a single-level 'Adj Close'
            # This happens when yfinance returns data for a single ticker without a MultiIndex for columns like 'Adj Close'
            if 'Adj Close' in data.columns:
                adj_close = data['Adj Close']
            else:
                # If 'Adj Close' is not found at all, return empty Series to avoid further errors
                adj_close = pd.Series()
    else:
        # If single-level index, directly access 'Adj Close'
        adj_close = data['Adj Close']
    
    returns = adj_close.pct_change().dropna()
    
    # Calculate rolling metrics
    rolling_volatility = returns.rolling(window=30).std() * np.sqrt(252)
    
    metrics = {
        "volatility": returns.std() * np.sqrt(252),
        "avg_return": returns.mean() * 252,
        "max_drawdown": ((adj_close / adj_close.cummax()) - 1).min(),
        "sharpe_ratio": (returns.mean() / returns.std()) * np.sqrt(252) if returns.std() != 0 else 0,
        "var_95": np.percentile(returns, 5),  # Value at Risk
        "cvar_95": returns[returns <= np.percentile(returns, 5)].mean(),  # Conditional VaR
        "rolling_volatility": rolling_volatility,
        "total_return": (adj_close.iloc[-1] / adj_close.iloc[0] - 1) * 100
    }
    
    return metrics

def categorize_risk(volatility):
    """Categorize stock based on volatility."""
    if volatility < 0.2:
        return "Conservative"
    elif volatility < 0.4:
        return "Moderate"
    else:
        return "Aggressive"

def simulate_investment(initial_amount, annual_return, years, monthly_contribution=0):
    """Simulate investment growth with compound interest."""
    months = years * 12
    monthly_return = annual_return / 12
    
    values = [initial_amount]
    current_value = initial_amount
    
    for month in range(1, months + 1):
        current_value = current_value * (1 + monthly_return) + monthly_contribution
        values.append(current_value)
    
    return values

def create_advanced_chart(stock_data, metrics, ticker):
    """Create advanced multi-panel chart with price, volume, and volatility."""
    fig = make_subplots(
        rows=3, cols=1,
        subplot_titles=(f'{ticker} Price Movement', 'Volume', 'Rolling Volatility'),
        vertical_spacing=0.08,
        row_heights=[0.6, 0.2, 0.2]
    )

    # Extract price and volume series
    if isinstance(stock_data.columns, pd.MultiIndex):
        try:
            adj_close = stock_data.loc[:, ("Adj Close", ticker)]
            volume = stock_data.loc[:, ("Volume", ticker)]
        except KeyError:
            # Fallback if the specific ticker is not found in the second level of MultiIndex
            # This happens when yfinance returns data for a single ticker without a MultiIndex for columns
            adj_close = stock_data["Adj Close"]
            volume = stock_data["Volume"]
    else:
        adj_close = stock_data["Adj Close"]
        volume = stock_data["Volume"]
    fig.add_trace(
        go.Scatter(x=stock_data.index, y=adj_close,
                  name='Price', line=dict(color='#1f77b4', width=2)),
        row=1, col=1
    )

    # Add moving averages
    ma_20 = adj_close.rolling(window=20).mean()
    ma_50 = adj_close.rolling(window=50).mean()

    fig.add_trace(
        go.Scatter(x=stock_data.index, y=ma_20,
                  name='MA 20', line=dict(color='orange', width=1, dash='dash')),
        row=1, col=1
    )

    fig.add_trace(
        go.Scatter(x=stock_data.index, y=ma_50,
                  name='MA 50', line=dict(color='red', width=1, dash='dot')),
        row=1, col=1
    )

    # Volume chart
    fig.add_trace(
        go.Bar(x=stock_data.index, y=volume,
               name='Volume', marker_color='lightblue'),
        row=2, col=1
    )

    # Rolling volatility
    fig.add_trace(
        go.Scatter(x=stock_data.index, y=metrics['rolling_volatility'],
                  name='30-Day Volatility', line=dict(color='purple', width=2)),
        row=3, col=1
    )

    fig.update_layout(
        height=800,
        title_text=f"Comprehensive Analysis - {ticker}",
        showlegend=True,
        template='plotly_white'
    )

    return fig

def create_investment_chart(values, years, initial_amount, ticker):
    """Create an enhanced investment growth chart."""
    months = list(range(len(values)))
    years_labels = [m/12 for m in months]
    
    fig = go.Figure()
    
    # Investment growth line
    fig.add_trace(go.Scatter(
        x=years_labels,
        y=values,
        mode='lines',
        name=f'{ticker} Investment Growth',
        line=dict(color='#1f77b4', width=3),
        fill='tonexty',
        hovertemplate='<b>Year %{x:.1f}</b><br>Portfolio Value: ₹%{y:,.0f}<extra></extra>'
    ))
    
    # Add initial investment line
    fig.add_hline(y=initial_amount, line_dash="dash", 
                  annotation_text=f"Initial: ₹{initial_amount:,.0f}",
                  line_color="red")
    
    # Add final value annotation
    fig.add_annotation(
        x=years_labels[-1],
        y=values[-1],
        text=f"Final: ₹{values[-1]:,.0f}",
        showarrow=True,
        arrowhead=2,
        bgcolor="lightgreen",
        bordercolor="green"
    )
    
    fig.update_layout(
        title=f"Investment Growth Simulation - {ticker}",
        xaxis_title="Years",
        yaxis_title="Portfolio Value (₹)",
        hovermode='x unified',
        template='plotly_white',
        height=500
    )
    
    return fig

def generate_ai_advice(ticker, risk_category, metrics, selected_risk):
    """Generate AI-powered investment advice."""
    advice = []
    
    # Risk assessment advice
    if risk_category != selected_risk:
        if risk_category == "Aggressive" and selected_risk in ["Conservative", "Moderate"]:
            advice.append(f"⚠️ **Risk Mismatch**: {ticker} is more volatile than your preference. Consider reducing position size or diversifying.")
        elif risk_category == "Conservative" and selected_risk == "Aggressive":
            advice.append(f"ℹ️ **Lower Risk**: {ticker} is less risky than you prefer. You might want to explore growth stocks for higher returns.")
    
    # Performance advice
    if metrics["sharpe_ratio"] > 1.5:
        advice.append(f"✅ **Strong Performance**: {ticker} has excellent risk-adjusted returns (Sharpe: {metrics['sharpe_ratio']:.2f})")
    elif metrics["sharpe_ratio"] < 0.5:
        advice.append(f"⚠️ **Poor Risk-Adjusted Returns**: Consider if the risk is worth the potential reward.")
    
    # Volatility advice
    if metrics["volatility"] > 0.5:
        advice.append(f"🎢 **High Volatility**: Expect significant price swings. Only invest what you can afford to lose.")
    elif metrics["volatility"] < 0.15:
        advice.append(f"📈 **Stable Investment**: Low volatility makes this suitable for conservative portfolios.")
    
    # Drawdown advice
    if abs(metrics["max_drawdown"]) > 0.3:
        advice.append(f"📉 **High Drawdown Risk**: This stock has experienced drops of {abs(metrics['max_drawdown']):.1%}. Be prepared for potential losses.")
    
    return advice

# Sidebar configuration
st.sidebar.header("🎯 Investment Profile")
selected_risk = st.sidebar.selectbox(
    "Choose your risk level:",
    list(RISK_CATEGORIES.keys()),
    help="Select based on your investment experience and risk tolerance"
)

# Enhanced risk info display
risk_info = RISK_CATEGORIES[selected_risk]
st.sidebar.markdown(f"""
**{selected_risk} Investor Profile**
- **Description**: {risk_info['description']}
- **Expected Returns**: {risk_info['expected_return']}
- **Volatility**: {risk_info['volatility']}
- **Examples**: {', '.join(risk_info['examples'][:3])}
""")

# Investment simulator sidebar
st.sidebar.header("💰 Investment Calculator")
investment_amount = st.sidebar.number_input(
    "Initial Investment (₹):",
    min_value=1000,
    max_value=10000000,
    value=50000,
    step=5000
)

monthly_sip = st.sidebar.number_input(
    "Monthly SIP (₹):",
    min_value=0,
    max_value=100000,
    value=10000,
    step=1000,
    help="Systematic Investment Plan - monthly contribution"
)

investment_years = st.sidebar.slider(
    "Investment Period (Years):",
    min_value=1,
    max_value=30,
    value=15
)

# Portfolio comparison
st.sidebar.header("📊 Portfolio Comparison")
compare_tickers = st.sidebar.text_input(
    "Compare with (comma-separated):",
    placeholder="AAPL,GOOGL,TSLA",
    help="Enter multiple tickers to compare"
)

# Main interface
col1, col2 = st.columns([3, 1])

with col1:
    ticker = st.text_input(
        "🔍 Enter Stock Ticker:",
        value=risk_info['examples'][0],
        help="Try stocks from your selected risk category"
    ).upper()

with col2:
    analysis_type = st.selectbox(
        "Analysis Type:",
        ["Detailed", "Quick", "Comparison"],
        help="Choose analysis depth"
    )

# Date selection with presets
date_col1, date_col2, date_col3 = st.columns([1, 1, 1])
with date_col1:
    date_preset = st.selectbox("Quick Select:", ["Custom", "1 Year", "3 Years", "5 Years", "10 Years"])

if date_preset != "Custom":
    years_back = {"1 Year": 1, "3 Years": 3, "5 Years": 5, "10 Years": 10}[date_preset]
    end_date = pd.to_datetime("today")
    start_date = end_date - pd.DateOffset(years=years_back)
else:
    with date_col2:
        start_date = st.date_input("Start Date:", pd.to_datetime("2020-01-01"))
    with date_col3:
        end_date = st.date_input("End Date:", pd.to_datetime("2024-01-01"))

# Main analysis button
if st.button("🚀 Run Complete Analysis", type="primary", use_container_width=True):
    if ticker and start_date and end_date:
        with st.spinner(f"Running comprehensive analysis for {ticker}..."):
            stock_data = get_stock_data(ticker, start_date, end_date)
            
        if stock_data is not None:
            # Calculate metrics
            metrics = calculate_risk_metrics(stock_data, ticker)
            risk_category = categorize_risk(metrics["volatility"])
            
            # Success message
            st.success(f"✅ Analysis complete for {ticker} | Period: {start_date} to {end_date}")
            
            # Key metrics dashboard
            st.subheader("📊 Key Performance Metrics")
            metric_cols = st.columns(5)
            
            with metric_cols[0]:
                st.metric("Risk Level", risk_category, 
                         delta=f"vs {selected_risk}" if risk_category != selected_risk else None)
            with metric_cols[1]:
                st.metric("Total Return", f"{metrics['total_return']:.1f}%")
            with metric_cols[2]:
                st.metric("Volatility", f"{metrics['volatility']:.1%}")
            with metric_cols[3]:
                st.metric("Sharpe Ratio", f"{metrics['sharpe_ratio']:.2f}")
            with metric_cols[4]:
                st.metric("Max Drawdown", f"{metrics['max_drawdown']:.1%}")
            
            # AI-powered advice
            st.subheader("🤖 AI Investment Advice")
            advice_list = generate_ai_advice(ticker, risk_category, metrics, selected_risk)
            for advice in advice_list:
                st.markdown(f"- {advice}")
            
            # Advanced charts
            if analysis_type == "Detailed":
                st.subheader("📈 Advanced Technical Analysis")
                advanced_chart = create_advanced_chart(stock_data, metrics, ticker)
                st.plotly_chart(advanced_chart, use_container_width=True)
            
            # Investment Simulation
            st.markdown("---")
            st.subheader("💰 Investment Simulation Results")
            
            # Run simulation
            projected_values = simulate_investment(
                investment_amount, 
                metrics["avg_return"], 
                investment_years, 
                monthly_sip
            )
            
            final_value = projected_values[-1]
            total_invested = investment_amount + (monthly_sip * investment_years * 12)
            total_returns = final_value - total_invested
            return_percentage = (total_returns / total_invested) * 100 if total_invested > 0 else 0
            
            # Simulation results
            sim_cols = st.columns(4)
            with sim_cols[0]:
                st.metric("💵 Total Invested", f"₹{total_invested:,.0f}")
            with sim_cols[1]:
                st.metric("💎 Final Value", f"₹{final_value:,.0f}")
            with sim_cols[2]:
                st.metric("📈 Total Returns", f"₹{total_returns:,.0f}")
            with sim_cols[3]:
                st.metric("📊 Return %", f"{return_percentage:.1f}%")
            
            # Investment growth chart
            investment_chart = create_investment_chart(
                projected_values, investment_years, investment_amount, ticker
            )
            st.plotly_chart(investment_chart, use_container_width=True)
            
            # Portfolio comparison
            if compare_tickers and analysis_type == "Comparison":
                st.subheader("⚖️ Portfolio Comparison")
                comparison_tickers = [t.strip().upper() for t in compare_tickers.split(",")]
                
            
(Content truncated due to size limit. Use page ranges or line ranges to read remaining content)


