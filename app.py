import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime, timedelta

# --- Configuration --- #
NEWS_API_KEY = "YOUR_NEWS_API_KEY"  # Replace with your actual NewsAPI key

RISK_PROFILES = {
    "Conservative": {
        "description": "Focus on capital preservation with lower risk and steady returns.",
        "expected_return": 0.05,  # 5% annual return
        "stock_type": "large-cap",
        "example_stocks": ["MSFT", "AAPL", "GOOGL", "AMZN", "JPM"],
    },
    "Balanced": {
        "description": "A mix of growth and stability, aiming for moderate returns.",
        "expected_return": 0.08,  # 8% annual return
        "stock_type": "large & mid-cap",
        "example_stocks": ["MSFT", "GOOGL", "ADBE", "PYPL", "INTC"],
    },
    "Aggressive": {
        "description": "Higher risk for potentially higher returns, focusing on growth stocks.",
        "expected_return": 0.12,  # 12% annual return
        "stock_type": "small-cap & high-growth",
        "example_stocks": ["TSLA", "NVDA", "AMD", "SQ", "CRWD"],
    },
}

# --- Helper Functions --- #
def calculate_projected_value(principal, annual_return, years):
    return principal * (1 + annual_return)**years

@st.cache_data
def get_stock_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1y")
        if not hist.empty:
            current_price = hist["Close"].iloc[-1]
            previous_close = hist["Close"].iloc[-2]
            daily_change_abs = current_price - previous_close
            daily_change_pct = (daily_change_abs / previous_close) * 100

            one_year_ago_price = hist["Close"].iloc[0]
            one_year_return_pct = ((current_price - one_year_ago_price) / one_year_ago_price) * 100

            return {
                "current_price": current_price,
                "daily_change_abs": daily_change_abs,
                "daily_change_pct": daily_change_pct,
                "one_year_return_pct": one_year_return_pct,
                "history": hist
            }
        else:
            return None
    except Exception as e:
        st.error(f"Error fetching data for {ticker}: {e}")
        return None

@st.cache_data
def get_financial_news(query, api_key, num_articles=5):
    if api_key == "YOUR_NEWS_API_KEY":
        st.warning("Please replace 'YOUR_NEWS_API_KEY' with your actual NewsAPI key to fetch live news.")
        return []
    
    url = f"https://newsapi.org/v2/everything?q={query}&sortBy=relevancy&apiKey={api_key}&pageSize={num_articles}"
    try:
        response = requests.get(url)
        data = response.json()
        if data["status"] == "ok":
            return data["articles"]
        else:
            st.error(f"Error fetching news: {data.get('message', 'Unknown error')}")
            return []
    except Exception as e:
        st.error(f"Error fetching news: {e}")
        return []

# --- Streamlit App --- #
st.set_page_config(layout="wide", page_title="InvestoPal")

st.title("📈 InvestoPal – Smart Investment Guide")

# Sidebar
st.sidebar.header("Your Investment Profile")

risk_tolerance = st.sidebar.radio(
    "Select your Risk Tolerance:",
    list(RISK_PROFILES.keys())
)

investment_amount = st.sidebar.number_input(
    "Investment Amount (₹)",
    min_value=1000, value=100000, step=1000
)

investment_horizon = st.sidebar.selectbox(
    "Investment Horizon (years)",
    (1, 3, 5, 10, 15, 20)
)

selected_profile = RISK_PROFILES[risk_tolerance]

st.sidebar.subheader("Risk Profile Details:")
st.sidebar.write(f"**Type:** {risk_tolerance}")
st.sidebar.write(f"**Description:** {selected_profile['description']}")
st.sidebar.write(f"**Expected Annual Return:** {selected_profile['expected_return']:.2%}")

# Main Content Area
st.header("Investment Analysis")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Stock Recommendations & Analysis")
    st.write(f"Based on your **{risk_tolerance}** risk tolerance, we recommend looking into **{selected_profile['stock_type']}** stocks.")
    
    selected_stock = st.selectbox(
        "Select a stock for detailed analysis:",
        selected_profile['example_stocks']
    )

    if selected_stock:
        stock_data = get_stock_data(selected_stock)
        if stock_data:
            st.write(f"### {selected_stock}")
            st.write(f"**Current Price:** ₹{stock_data['current_price']:.2f}")
            color = "green" if stock_data['daily_change_abs'] >= 0 else "red"
            st.markdown(f"**Daily Change:** <span style='color:{color}'>₹{stock_data['daily_change_abs']:.2f} ({stock_data['daily_change_pct']:.2f}%)</span>", unsafe_allow_html=True)
            st.write(f"**1-Year Return:** {stock_data['one_year_return_pct']:.2f}%")

            # Plotting chart with enhanced styling
            fig = px.line(
                stock_data['history'], 
                y="Close", 
                title=f"{selected_stock} Closing Price (1 Year)",
                color_discrete_sequence=['#007bff']
            )
            fig.update_layout(
                title_font_size=16,
                title_font_color='#2c3e50',
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(gridcolor='#e1e5e9'),
                yaxis=dict(gridcolor='#e1e5e9')
            )
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            st.plotly_chart(fig, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

            # News Integration
            st.subheader(f"Latest News for {selected_stock}")
            news_articles = get_financial_news(selected_stock, NEWS_API_KEY)
            if news_articles:
                for article in news_articles:
                    st.markdown(f"- [{article['title']}]({article['url']})")
            else:
                st.info("No news found or API key is missing/invalid.")

with col2:
    st.subheader("Investment Insights & Projections")
    
    # Create projection visualization
    years = list(range(1, investment_horizon + 1))
    projected_values = [calculate_projected_value(investment_amount, selected_profile['expected_return'], year) for year in years]
    
    projection_df = pd.DataFrame({
        'Year': years,
        'Projected Value (₹)': projected_values
    })
    
    # Create projection chart
    fig_projection = px.bar(
        projection_df, 
        x='Year', 
        y='Projected Value (₹)',
        title=f"Investment Growth Projection ({risk_tolerance} Profile)",
        color='Projected Value (₹)',
        color_continuous_scale='Blues'
    )
    fig_projection.update_layout(
        title_font_size=16,
        title_font_color='#2c3e50',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(gridcolor='#e1e5e9'),
        yaxis=dict(gridcolor='#e1e5e9')
    )
    
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    st.plotly_chart(fig_projection, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Summary metrics
    final_projected_value = calculate_projected_value(
        investment_amount,
        selected_profile['expected_return'],
        investment_horizon
    )
    total_gain = final_projected_value - investment_amount
    
    col2_1, col2_2 = st.columns(2)
    with col2_1:
        st.metric(
            label="Initial Investment",
            value=f"₹{investment_amount:,.0f}"
        )
    with col2_2:
        st.metric(
            label="Projected Value",
            value=f"₹{final_projected_value:,.0f}",
            delta=f"₹{total_gain:,.0f}"
        )
    
    st.write(f"With an initial investment of ₹{investment_amount:,.2f} and an expected annual return of {selected_profile['expected_return']:.2%},")
    st.write(f"your projected value in {investment_horizon} years could be **₹{final_projected_value:,.2f}**.")

    st.subheader("Learn More")
    with st.expander("Understanding Risk Levels & Investing Tips"):
        st.markdown("""
        ### Risk Levels Explained
        
        **🟢 Conservative (Low Risk)**
        - Focus on stable, well-established companies with a history of consistent dividends
        - Examples: Blue-chip stocks, government bonds, dividend-paying stocks
        - Expected return: 3-7% annually
        - Best for: Risk-averse investors, those nearing retirement
        
        **🟡 Balanced (Moderate Risk)**
        - A diversified portfolio with a mix of growth and value stocks
        - Examples: Mix of large-cap and mid-cap stocks, balanced mutual funds
        - Expected return: 6-10% annually
        - Best for: Investors with moderate risk tolerance, long-term goals
        
        **🔴 Aggressive (High Risk)**
        - Higher allocation to growth stocks, emerging markets, and potentially volatile assets
        - Examples: Small-cap stocks, growth stocks, emerging market funds
        - Expected return: 8-15% annually (with higher volatility)
        - Best for: Young investors, those with high risk tolerance
        
        ### 💡 Essential Investing Tips
        
        **1. Start Early & Invest Regularly**
        - Time is your greatest asset in investing
        - Consider systematic investment plans (SIPs)
        - Even small amounts can grow significantly over time
        
        **2. Diversify Your Portfolio**
        - Don't put all eggs in one basket
        - Spread investments across different sectors and asset classes
        - Consider international diversification
        
        **3. Understand What You're Investing In**
        - Research companies before investing
        - Read annual reports and financial statements
        - Understand the business model and competitive advantages
        
        **4. Stay Informed but Avoid Emotional Decisions**
        - Keep up with market news and trends
        - Don't panic during market downturns
        - Stick to your long-term investment strategy
        
        **5. Rebalance Your Portfolio Periodically**
        - Review your portfolio quarterly or semi-annually
        - Adjust allocations based on your goals and market conditions
        - Take profits from overperforming assets and reinvest
        
        ### 📚 Additional Resources
        - **Books**: "The Intelligent Investor" by Benjamin Graham
        - **Websites**: SEC.gov investor education, Morningstar.com
        - **Podcasts**: "The Investors Podcast", "Chat with Traders"
        """)
    
    # Risk comparison chart
    st.subheader("Risk vs Return Comparison")
    risk_comparison_data = pd.DataFrame({
        'Risk Level': ['Conservative', 'Balanced', 'Aggressive'],
        'Expected Return (%)': [5, 8, 12],
        'Risk Score': [2, 5, 8]
    })
    
    fig_risk = px.scatter(
        risk_comparison_data,
        x='Risk Score',
        y='Expected Return (%)',
        size='Expected Return (%)',
        color='Risk Level',
        title="Risk vs Expected Return Profile",
        color_discrete_map={
            'Conservative': '#28a745',
            'Balanced': '#ffc107', 
            'Aggressive': '#dc3545'
        }
    )
    fig_risk.update_layout(
        title_font_size=16,
        title_font_color='#2c3e50',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(gridcolor='#e1e5e9', title='Risk Level (1-10)'),
        yaxis=dict(gridcolor='#e1e5e9', title='Expected Annual Return (%)')
    )
    
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    st.plotly_chart(fig_risk, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Export simulation results as CSV
    df_projection = pd.DataFrame({
        'Investment Amount': [investment_amount],
        'Expected Annual Return': [selected_profile['expected_return']],
        'Investment Horizon (Years)': [investment_horizon],
        'Projected Value': [final_projected_value]
    })
    csv = df_projection.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Export Simulation Results as CSV",
        data=csv,
        file_name='investopal_simulation_results.csv',
        mime='text/csv',
    )

# Custom CSS for professional styling
st.markdown("""
<style>
/* Main app styling */
.main {
    padding-top: 2rem;
}

/* Risk profile cards */
.risk-card {
    border: 2px solid #e1e5e9;
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 15px;
    background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    transition: all 0.3s ease;
}

.risk-card:hover {
    border-color: #007bff;
    box-shadow: 0 8px 15px rgba(0, 123, 255, 0.2);
    transform: translateY(-2px);
}

/* Conservative risk styling */
.conservative-card {
    border-color: #28a745;
    background: linear-gradient(135deg, #d4edda 0%, #ffffff 100%);
}

/* Balanced risk styling */
.balanced-card {
    border-color: #ffc107;
    background: linear-gradient(135deg, #fff3cd 0%, #ffffff 100%);
}

/* Aggressive risk styling */
.aggressive-card {
    border-color: #dc3545;
    background: linear-gradient(135deg, #f8d7da 0%, #ffffff 100%);
}

/* Stock analysis cards */
.stock-card {
    background: #ffffff;
    border-radius: 10px;
    padding: 20px;
    margin: 10px 0;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
    border-left: 4px solid #007bff;
}

/* Metrics styling */
.metric-positive {
    color: #28a745;
    font-weight: bold;
}

.metric-negative {
    color: #dc3545;
    font-weight: bold;
}

/* Header styling */
.main-header {
    text-align: center;
    color: #2c3e50;
    margin-bottom: 2rem;
    font-size: 2.5rem;
    font-weight: 700;
}

/* Sidebar styling */
.sidebar .sidebar-content {
    background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
    color: white;
}

/* Button styling */
.stDownloadButton > button {
    background: linear-gradient(45deg, #667eea 0%, #764ba2 100%);
    color: white;
    border: none;
    border-radius: 8px;
    padding: 0.5rem 1rem;
    font-weight: 600;
    transition: all 0.3s ease;
}

.stDownloadButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

/* Expander styling */
.streamlit-expanderHeader {
    background: #f8f9fa;
    border-radius: 8px;
    border: 1px solid #dee2e6;
}

/* Chart container */
.chart-container {
    background: white;
    border-radius: 10px;
    padding: 15px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    margin: 15px 0;
}
</style>
""", unsafe_allow_html=True)


