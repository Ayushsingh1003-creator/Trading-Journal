import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
from datetime import datetime
import json
import os
from dotenv import load_dotenv
from zerodha_integration import ZerodhaIntegration
import numpy as np
from typing import List, Dict, Any

# Custom CSS for better styling
st.set_page_config(
    page_title="Tradeverse",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main {
        background-color: #ffffff;
    }
    .stButton>button {
        background-color: #1e88e5;
        color: white;
        border-radius: 5px;
        padding: 10px 20px;
        border: none;
        font-weight: bold;
        transition: background-color 0.3s;
    }
    .stButton>button:hover {
        background-color: #1565c0;
    }
    .metric-card {
        background-color: white;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        border: 1px solid #e0e0e0;
    }
    .header {
        color: #1e88e5;
        font-size: 2.5em;
        font-weight: bold;
        margin-bottom: 20px;
        text-align: center;
    }
    .subheader {
        color: #1e88e5;
        font-size: 1.8em;
        font-weight: bold;
        margin-top: 30px;
        margin-bottom: 20px;
        border-bottom: 2px solid #1e88e5;
        padding-bottom: 10px;
    }
    .info-box {
        background-color: #e3f2fd;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        border-left: 4px solid #1e88e5;
    }
    .warning-box {
        background-color: #fff3e0;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        border-left: 4px solid #ff9800;
    }
    .stTextInput>div>div>input {
        border-radius: 5px;
        border: 1px solid #e0e0e0;
    }
    .stNumberInput>div>div>input {
        border-radius: 5px;
        border: 1px solid #e0e0e0;
    }
    .stSelectbox>div>div>select {
        border-radius: 5px;
        border: 1px solid #e0e0e0;
    }
    .stTextArea>div>div>textarea {
        border-radius: 5px;
        border: 1px solid #e0e0e0;
    }
    .stDateInput>div>div>input {
        border-radius: 5px;
        border: 1px solid #e0e0e0;
    }
    .stTimeInput>div>div>input {
        border-radius: 5px;
        border: 1px solid #e0e0e0;
    }
    .stFileUploader>div>div>div>div {
        border-radius: 5px;
        border: 1px solid #e0e0e0;
    }
    .stMultiSelect>div>div>div>div {
        border-radius: 5px;
        border: 1px solid #e0e0e0;
    }
    .stRadio>div>div>label {
        color: #1e88e5;
    }
    .stSuccess {
        background-color: #e3f2fd;
        color: #1e88e5;
    }
    .stError {
        background-color: #ffebee;
        color: #c62828;
    }
    .nav-button {
        background-color: #1e88e5;
        color: white;
        border-radius: 5px;
        padding: 10px 20px;
        border: none;
        font-weight: bold;
        margin: 5px;
        transition: background-color 0.3s;
    }
    .nav-button:hover {
        background-color: #1565c0;
    }
    .nav-container {
        display: flex;
        justify-content: center;
        padding: 10px;
        background-color: white;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        margin-bottom: 20px;
    }
    .section {
        display: none;
    }
    .section.active {
        display: block;
    }
    </style>
""", unsafe_allow_html=True)

load_dotenv()

# Initialize Zerodha integration
zerodha = ZerodhaIntegration()

# API configuration
API_URL = os.getenv("API_URL", "http://localhost:8000")

# Session state initialization
if 'token' not in st.session_state:
    st.session_state.token = None
if 'user' not in st.session_state:
    st.session_state.user = None
if 'zerodha_connected' not in st.session_state:
    st.session_state.zerodha_connected = False
if 'zerodha_profile' not in st.session_state:
    st.session_state.zerodha_profile = None
if 'available_tags' not in st.session_state:
    st.session_state.available_tags = set()

# Helper functions
def calculate_trade_metrics(df):
    if df.empty:
        return {
            'win_rate': 0,
            'avg_rr': 0,
            'net_pnl': 0,
            'max_drawdown': 0
        }
    
    # Calculate PnL
    df['pnl'] = (df['exit_price'] - df['entry_price']) * df['position_size']
    df['pnl'] = df.apply(lambda x: x['pnl'] if x['direction'] == 'LONG' else -x['pnl'], axis=1)
    
    # Calculate win/loss
    df['win'] = df['pnl'] > 0
    
    # Calculate win rate
    win_rate = (df['win'].sum() / len(df)) * 100 if len(df) > 0 else 0
    
    # Calculate average R:R
    df['rr'] = abs(df['pnl'] / (df['position_size'] * df['entry_price']))
    avg_rr = df['rr'].mean() if not df['rr'].empty else 0
    
    # Calculate net PnL
    net_pnl = df['pnl'].sum()
    
    # Calculate max drawdown
    if not df.empty:
        cumulative_pnl = df['pnl'].cumsum()
        rolling_max = cumulative_pnl.cummax()
        drawdown = cumulative_pnl - rolling_max
        max_drawdown = drawdown.min()
    else:
        max_drawdown = 0
    
    return {
        'win_rate': win_rate,
        'avg_rr': avg_rr,
        'net_pnl': net_pnl,
        'max_drawdown': max_drawdown
    }

def calculate_advanced_metrics(df: pd.DataFrame) -> Dict[str, Any]:
    if df.empty:
        return {
            'expectancy': 0,
            'sharpe_ratio': 0,
            'profit_factor': 0,
            'avg_holding_time': 0,
            'std_dev_returns': 0
        }
    
    # Calculate expectancy
    win_trades = df[df['pnl'] > 0]
    loss_trades = df[df['pnl'] < 0]
    
    win_rate = len(win_trades) / len(df) if len(df) > 0 else 0
    avg_win = win_trades['pnl'].mean() if not win_trades.empty else 0
    avg_loss = abs(loss_trades['pnl'].mean()) if not loss_trades.empty else 0
    
    expectancy = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)
    
    # Calculate Sharpe Ratio (assuming 0 risk-free rate)
    returns = df['pnl'] / (df['position_size'] * df['entry_price'])
    sharpe_ratio = returns.mean() / returns.std() if len(returns) > 1 else 0
    
    # Calculate Profit Factor
    gross_profit = win_trades['pnl'].sum() if not win_trades.empty else 0
    gross_loss = abs(loss_trades['pnl'].sum()) if not loss_trades.empty else 0
    profit_factor = gross_profit / gross_loss if gross_loss != 0 else float('inf')
    
    # Calculate Average Holding Time
    df['entry_datetime'] = pd.to_datetime(df['entry_date'])
    df['exit_datetime'] = pd.to_datetime(df['exit_date'])
    df['holding_time'] = (df['exit_datetime'] - df['entry_datetime']).dt.total_seconds() / 3600  # in hours
    avg_holding_time = df['holding_time'].mean()
    
    # Calculate Standard Deviation of Returns
    std_dev_returns = returns.std() if len(returns) > 1 else 0
    
    return {
        'expectancy': expectancy,
        'sharpe_ratio': sharpe_ratio,
        'profit_factor': profit_factor,
        'avg_holding_time': avg_holding_time,
        'std_dev_returns': std_dev_returns
    }

def update_available_tags(tags: List[str]):
    st.session_state.available_tags.update(tags)

# Authentication functions
def login(email, password):
    try:
        response = requests.post(
            f"{API_URL}/token",
            data={"username": email, "password": password}
        )
        if response.status_code == 200:
            st.session_state.token = response.json()["access_token"]
            st.session_state.user = email
            return True
    except:
        pass
    return False

def register(email, password):
    try:
        response = requests.post(
            f"{API_URL}/register",
            json={"email": email, "password": password}
        )
        return response.status_code == 200
    except:
        return False

# Main app
def main():
    st.markdown('<div class="header">Tradeverse Trading Journal</div>', unsafe_allow_html=True)
    
    # Initialize session state for active section
    if 'active_section' not in st.session_state:
        st.session_state.active_section = 'trade_input'
    
    # Authentication
    if not st.session_state.token:
        auth_type = st.radio("Choose action", ["Login", "Register"], horizontal=True)
        
        if auth_type == "Login":
            with st.container():
                st.markdown('<div class="subheader">Login</div>', unsafe_allow_html=True)
                col1, col2 = st.columns(2)
                with col1:
                    email = st.text_input("Email", key="login_email")
                with col2:
                    password = st.text_input("Password", type="password", key="login_password")
                if st.button("Login", key="login_button"):
                    if login(email, password):
                        st.success("Logged in successfully!")
                        st.rerun()
                    else:
                        st.error("Invalid credentials")
        else:
            with st.container():
                st.markdown('<div class="subheader">Register</div>', unsafe_allow_html=True)
                col1, col2 = st.columns(2)
                with col1:
                    email = st.text_input("Email", key="register_email")
                with col2:
                    password = st.text_input("Password", type="password", key="register_password")
                if st.button("Register", key="register_button"):
                    if register(email, password):
                        st.success("Registration successful! Please login.")
                    else:
                        st.error("Registration failed")
    else:
        # Navigation Bar
        st.markdown('<div class="nav-container">', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("Trade Input", key="nav_trade_input"):
                st.session_state.active_section = 'trade_input'
        with col2:
            if st.button("Performance Dashboard", key="nav_performance"):
                st.session_state.active_section = 'performance'
        with col3:
            if st.button("Zerodha Integration", key="nav_zerodha"):
                st.session_state.active_section = 'zerodha'
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Logout button
        if st.button("Logout", key="logout_button"):
            st.session_state.token = None
            st.session_state.user = None
            st.rerun()
        
        # Trade Input Section
        if st.session_state.active_section == 'trade_input':
            st.markdown('<div class="subheader">Trade Input</div>', unsafe_allow_html=True)
            
            # Trade input form
            with st.container():
                with st.form("trade_form", clear_on_submit=True):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                        asset = st.text_input("Asset (e.g., BTCUSD, NIFTY)", key="asset")
                        entry_price = st.number_input("Entry Price", min_value=0.0, key="entry_price")
                        position_size = st.number_input("Position Size", min_value=0.0, key="position_size")
                        entry_date = st.date_input("Entry Date", key="entry_date")
                        entry_time = st.time_input("Entry Time", key="entry_time")
                        direction = st.selectbox("Direction", ["LONG", "SHORT"], key="direction")
                        st.markdown('</div>', unsafe_allow_html=True)
                    
                    with col2:
                        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                        exit_price = st.number_input("Exit Price", min_value=0.0, key="exit_price")
                        exit_date = st.date_input("Exit Date", key="exit_date")
                        exit_time = st.time_input("Exit Time", key="exit_time")
                        strategy = st.text_input("Strategy", key="strategy")
                        
                        # Add TP and SL fields
                        col_tp, col_sl = st.columns(2)
                        with col_tp:
                            take_profit = st.number_input("Take Profit", min_value=0.0, key="take_profit")
                        with col_sl:
                            stop_loss = st.number_input("Stop Loss", min_value=0.0, key="stop_loss")
                        
                        tags = st.multiselect(
                            "Tags",
                            options=list(st.session_state.available_tags),
                            key="tags",
                            help="Select existing tags or type to create new ones"
                        )
                        new_tags = st.text_input("New Tags (comma-separated)", key="new_tags", help="Add new tags separated by commas")
                        screenshot = st.file_uploader("Screenshot (optional)", type=['png', 'jpg', 'jpeg'], key="screenshot")
                        notes = st.text_area("Notes", key="notes")
                        st.markdown('</div>', unsafe_allow_html=True)
                    
                    submitted = st.form_submit_button("Submit Trade")
                    
                    if submitted:
                        if not asset or not entry_price or not exit_price or not position_size:
                            st.error("Please fill in all required fields (Asset, Entry Price, Exit Price, Position Size)")
                        else:
                            # Combine date and time into ISO format strings
                            entry_datetime = datetime.combine(entry_date, entry_time).isoformat()
                            exit_datetime = datetime.combine(exit_date, exit_time).isoformat()
                            
                            # Handle tags
                            all_tags = set(tags)
                            if new_tags:
                                new_tags_list = [tag.strip() for tag in new_tags.split(',')]
                                all_tags.update(new_tags_list)
                                update_available_tags(new_tags_list)
                            
                            # Handle screenshot
                            screenshot_path = None
                            if screenshot is not None:
                                # Save the screenshot to a temporary location
                                screenshot_path = f"uploads/{screenshot.name}"
                                os.makedirs("uploads", exist_ok=True)
                                with open(screenshot_path, "wb") as f:
                                    f.write(screenshot.getbuffer())
                            
                            trade_data = {
                                "asset": asset,
                                "entry_price": float(entry_price),
                                "exit_price": float(exit_price),
                                "position_size": float(position_size),
                                "entry_date": entry_datetime,
                                "exit_date": exit_datetime,
                                "direction": direction,
                                "strategy": strategy if strategy else None,
                                "take_profit": float(take_profit) if take_profit else None,
                                "stop_loss": float(stop_loss) if stop_loss else None,
                                "tags": list(all_tags),
                                "screenshot_path": screenshot_path,
                                "notes": notes if notes else None
                            }
                            
                            try:
                                response = requests.post(
                                    f"{API_URL}/trades",
                                    json=trade_data,
                                    headers={"Authorization": f"Bearer {st.session_state.token}"}
                                )
                                if response.status_code == 200:
                                    st.success("Trade added successfully!")
                                    st.rerun()  # Refresh the page to show the new trade
                                else:
                                    st.error(f"Failed to add trade: {response.text}")
                            except Exception as e:
                                st.error(f"Error connecting to server: {str(e)}")
        
        # Performance Dashboard Section
        elif st.session_state.active_section == 'performance':
            st.markdown('<div class="subheader">Performance Dashboard</div>', unsafe_allow_html=True)
            try:
                response = requests.get(
                    f"{API_URL}/trades",
                    headers={"Authorization": f"Bearer {st.session_state.token}"}
                )
                
                if response.status_code == 200:
                    trades = response.json()
                    if not trades:
                        st.markdown('<div class="info-box">No trades recorded yet. Add your first trade to see performance metrics.</div>', unsafe_allow_html=True)
                        return
                        
                    df = pd.DataFrame(trades)
                    
                    if not df.empty:
                        metrics = calculate_trade_metrics(df)
                        
                        # Metrics display with cards
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                            st.metric("Win Rate", f"{metrics['win_rate']:.1f}%")
                            st.markdown('</div>', unsafe_allow_html=True)
                        with col2:
                            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                            st.metric("Avg R:R", f"{metrics['avg_rr']:.2f}")
                            st.markdown('</div>', unsafe_allow_html=True)
                        with col3:
                            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                            st.metric("Net PnL", f"₹{metrics['net_pnl']:,.2f}")
                            st.markdown('</div>', unsafe_allow_html=True)
                        with col4:
                            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                            st.metric("Max Drawdown", f"₹{metrics['max_drawdown']:,.2f}")
                            st.markdown('</div>', unsafe_allow_html=True)
                        
                        # Charts with better styling
                        st.markdown('<div class="subheader">Performance Charts</div>', unsafe_allow_html=True)
                        
                        # Equity Curve
                        df['cumulative_pnl'] = df['pnl'].cumsum()
                        fig_equity = px.line(df, x='exit_date', y='cumulative_pnl', title='Equity Curve (₹)')
                        fig_equity = update_chart_style(fig_equity)
                        st.plotly_chart(fig_equity, use_container_width=True)
                        
                        # Win/Loss Distribution
                        col1, col2 = st.columns(2)
                        with col1:
                            fig_pie = px.pie(df, names='win', title='Win/Loss Distribution')
                            fig_pie = update_chart_style(fig_pie)
                            st.plotly_chart(fig_pie, use_container_width=True)
                        
                        # Strategy Performance
                        with col2:
                            if not df['strategy'].empty and df['strategy'].notna().any():
                                strategy_perf = df.groupby('strategy')['pnl'].sum().reset_index()
                                fig_strategy = px.bar(strategy_perf, x='strategy', y='pnl', title='Performance by Strategy (₹)')
                                fig_strategy = update_chart_style(fig_strategy)
                                st.plotly_chart(fig_strategy, use_container_width=True)
                        
                        # Add improvement recommendations directly in the performance dashboard
                        st.markdown('<div class="subheader">Improvement Recommendations</div>', unsafe_allow_html=True)
                        
                        # Strategy analysis
                        if not df['strategy'].empty and df['strategy'].notna().any():
                            strategy_win_rates = df.groupby('strategy')['win'].mean() * 100
                            for strategy, win_rate in strategy_win_rates.items():
                                if win_rate < 50:
                                    st.markdown(f'<div class="warning-box">Your trades using {strategy} have a {win_rate:.1f}% win rate. Consider refining this setup.</div>', unsafe_allow_html=True)
                        
                        # R:R analysis
                        if metrics['avg_rr'] < 1.5:
                            st.markdown(f'<div class="warning-box">Improve reward-to-risk. Average R:R is {metrics["avg_rr"]:.2f} — aim for trades above 1.5.</div>', unsafe_allow_html=True)
                        
                        # Day of week analysis
                        df['day_of_week'] = pd.to_datetime(df['exit_date']).dt.day_name()
                        day_win_rates = df.groupby('day_of_week')['win'].mean() * 100
                        for day, win_rate in day_win_rates.items():
                            if win_rate < 40:
                                st.markdown(f'<div class="warning-box">Avoid trading on {day}s — your win rate is {win_rate:.1f}%.</div>', unsafe_allow_html=True)
                        
                        # Zerodha Integration
                        st.markdown("---")
                        st.header("Zerodha Integration")
                        
                        if not st.session_state.zerodha_connected:
                            if st.button("Connect with Zerodha"):
                                login_url = zerodha.get_login_url()
                                st.markdown(f"[Click here to connect with Zerodha]({login_url})")
                                
                                request_token = st.text_input("Enter the request token from Zerodha")
                                if request_token:
                                    if zerodha.generate_session(request_token):
                                        st.session_state.zerodha_connected = True
                                        st.session_state.zerodha_profile = zerodha.get_profile()
                                        st.success("Successfully connected to Zerodha!")
                                    else:
                                        st.error("Failed to connect to Zerodha. Please try again.")
                        else:
                            st.success("Connected to Zerodha!")
                            if st.session_state.zerodha_profile:
                                st.write(f"Welcome, {st.session_state.zerodha_profile['user_name']}")
                            
                            if st.button("Import Trades from Zerodha"):
                                trades = zerodha.fetch_trades()
                                if trades:
                                    # Import trades to our database
                                    for trade in trades:
                                        try:
                                            response = requests.post(
                                                f"{API_URL}/trades",
                                                json=trade,
                                                headers={"Authorization": f"Bearer {st.session_state.token}"}
                                            )
                                            if response.status_code != 200:
                                                st.error(f"Failed to import trade: {response.text}")
                                        except Exception as e:
                                            st.error(f"Error importing trade: {str(e)}")
                                    
                                    st.success("Trades imported successfully!")
                                    st.rerun()
                                else:
                                    st.error("No trades found or error fetching trades from Zerodha")
                            
                            if st.button("Disconnect Zerodha"):
                                st.session_state.zerodha_connected = False
                                st.session_state.zerodha_profile = None
                                st.success("Disconnected from Zerodha!")
                                st.rerun()
                        
                        # Trade Log
                        st.header("Trade Log")
                        
                        # Add edit and delete functionality
                        col1, col2 = st.columns([4, 1])
                        with col1:
                            st.dataframe(df)
                        
                        with col2:
                            st.write("Actions")
                            trade_id = st.number_input("Trade ID", min_value=1, step=1, key="trade_id")
                            
                            if st.button("Edit Trade"):
                                # Get the trade details
                                trade = df[df['id'] == trade_id].iloc[0] if not df[df['id'] == trade_id].empty else None
                                
                                if trade is not None:
                                    # Create edit form
                                    with st.form("edit_trade_form"):
                                        st.write("Edit Trade Details")
                                        
                                        col1, col2 = st.columns(2)
                                        with col1:
                                            asset = st.text_input("Asset", value=trade['asset'], key="edit_asset")
                                            entry_price = st.number_input("Entry Price", value=trade['entry_price'], key="edit_entry_price")
                                            position_size = st.number_input("Position Size", value=trade['position_size'], key="edit_position_size")
                                            entry_date = st.date_input("Entry Date", value=pd.to_datetime(trade['entry_date']).date(), key="edit_entry_date")
                                            entry_time = st.time_input("Entry Time", value=pd.to_datetime(trade['entry_date']).time(), key="edit_entry_time")
                                            direction = st.selectbox("Direction", ["LONG", "SHORT"], index=0 if trade['direction'] == "LONG" else 1, key="edit_direction")
                                        
                                        with col2:
                                            exit_price = st.number_input("Exit Price", value=trade['exit_price'], key="edit_exit_price")
                                            exit_date = st.date_input("Exit Date", value=pd.to_datetime(trade['exit_date']).date(), key="edit_exit_date")
                                            exit_time = st.time_input("Exit Time", value=pd.to_datetime(trade['exit_date']).time(), key="edit_exit_time")
                                            strategy = st.text_input("Strategy", value=trade['strategy'] if pd.notna(trade['strategy']) else "", key="edit_strategy")
                                            notes = st.text_area("Notes", value=trade['notes'] if pd.notna(trade['notes']) else "", key="edit_notes")
                                        
                                        if st.form_submit_button("Update Trade"):
                                            try:
                                                # Combine date and time into ISO format strings
                                                entry_datetime = datetime.combine(entry_date, entry_time).isoformat()
                                                exit_datetime = datetime.combine(exit_date, exit_time).isoformat()
                                                
                                                trade_data = {
                                                    "asset": asset,
                                                    "entry_price": float(entry_price),
                                                    "exit_price": float(exit_price),
                                                    "position_size": float(position_size),
                                                    "entry_date": entry_datetime,
                                                    "exit_date": exit_datetime,
                                                    "direction": direction,
                                                    "strategy": strategy if strategy else None,
                                                    "notes": notes if notes else None
                                                }
                                                
                                                response = requests.put(
                                                    f"{API_URL}/trades/{trade_id}",
                                                    json=trade_data,
                                                    headers={"Authorization": f"Bearer {st.session_state.token}"}
                                                )
                                                
                                                if response.status_code == 200:
                                                    st.success("Trade updated successfully!")
                                                    st.rerun()
                                                else:
                                                    st.error(f"Failed to update trade: {response.text}")
                                            except Exception as e:
                                                st.error(f"Error updating trade: {str(e)}")
                                else:
                                    st.error("Trade not found")
                            
                            if st.button("Delete Trade"):
                                try:
                                    response = requests.delete(
                                        f"{API_URL}/trades/{trade_id}",
                                        headers={"Authorization": f"Bearer {st.session_state.token}"}
                                    )
                                    
                                    if response.status_code == 200:
                                        st.success("Trade deleted successfully!")
                                        st.rerun()
                                    else:
                                        st.error(f"Failed to delete trade: {response.text}")
                                except Exception as e:
                                    st.error(f"Error deleting trade: {str(e)}")
                        
                        # Tag Analytics
                        st.header("Tag Analytics")
                        
                        if 'tags' in df.columns and not df['tags'].empty:
                            # Flatten tags and create a new DataFrame for tag analysis
                            tag_data = []
                            for idx, row in df.iterrows():
                                for tag in row['tags']:
                                    tag_data.append({
                                        'tag': tag,
                                        'pnl': row['pnl'],
                                        'win': row['pnl'] > 0,
                                        'date': row['exit_date']
                                    })
                            tag_df = pd.DataFrame(tag_data)
                            
                            if not tag_df.empty:
                                # Tag Win Rate Bar Chart
                                tag_win_rates = tag_df.groupby('tag')['win'].mean() * 100
                                fig_tag_win = px.bar(
                                    tag_win_rates.reset_index(),
                                    x='tag',
                                    y='win',
                                    title='Win Rate by Tag (%)',
                                    labels={'win': 'Win Rate (%)', 'tag': 'Tag'}
                                )
                                st.plotly_chart(fig_tag_win)
                                
                                # Tag Distribution Pie Chart
                                tag_counts = tag_df['tag'].value_counts()
                                fig_tag_dist = px.pie(
                                    tag_counts.reset_index(),
                                    values='count',
                                    names='tag',
                                    title='Tag Distribution'
                                )
                                st.plotly_chart(fig_tag_dist)
                                
                                # Average PnL per Tag Table
                                tag_pnl = tag_df.groupby('tag')['pnl'].agg(['mean', 'count']).round(2)
                                tag_pnl.columns = ['Average PnL', 'Number of Trades']
                                st.write("Average PnL per Tag:")
                                st.dataframe(tag_pnl)
                                
                                # Tag Filter
                                selected_tags = st.multiselect(
                                    "Filter by Tags",
                                    options=list(tag_df['tag'].unique()),
                                    default=[]
                                )
                                
                                if selected_tags:
                                    filtered_df = df[df['tags'].apply(lambda x: any(tag in x for tag in selected_tags))]
                                    if not filtered_df.empty:
                                        st.write(f"Showing {len(filtered_df)} trades with selected tags")
                                        st.dataframe(filtered_df)
                        
                        # Advanced Analytics Tab
                        st.header("Advanced Analytics")
                        
                        # Calculate advanced metrics
                        advanced_metrics = calculate_advanced_metrics(df)
                        
                        # Display advanced metrics
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Expectancy", f"₹{advanced_metrics['expectancy']:,.2f}")
                            st.metric("Sharpe Ratio", f"{advanced_metrics['sharpe_ratio']:.2f}")
                        with col2:
                            st.metric("Profit Factor", f"{advanced_metrics['profit_factor']:.2f}")
                            st.metric("Avg Holding Time", f"{advanced_metrics['avg_holding_time']:.1f} hours")
                        with col3:
                            st.metric("Std Dev Returns", f"{advanced_metrics['std_dev_returns']:.2%}")
                        
                        # Advanced Visualizations
                        st.subheader("Performance Analysis")
                        
                        # Expectancy over Time
                        df['date'] = pd.to_datetime(df['exit_date'])
                        df['month'] = df['date'].dt.to_period('M')
                        
                        # Calculate monthly metrics
                        monthly_metrics = []
                        for month, group in df.groupby('month'):
                            metrics = calculate_advanced_metrics(group)
                            metrics['month'] = str(month)  # Convert Period to string
                            monthly_metrics.append(metrics)
                        
                        metrics_df = pd.DataFrame(monthly_metrics)
                        
                        # Sort by month for proper plotting
                        metrics_df['month_date'] = pd.to_datetime(metrics_df['month'].astype(str) + '-01')
                        metrics_df = metrics_df.sort_values('month_date')
                        
                        fig_expectancy = px.line(
                            metrics_df,
                            x='month',
                            y='expectancy',
                            title='Expectancy Over Time'
                        )
                        st.plotly_chart(fig_expectancy)
                        
                        # Sharpe Ratio and Profit Factor
                        fig_metrics = go.Figure()
                        fig_metrics.add_trace(go.Scatter(
                            x=metrics_df['month'],
                            y=metrics_df['sharpe_ratio'],
                            name='Sharpe Ratio',
                            yaxis='y1'
                        ))
                        fig_metrics.add_trace(go.Scatter(
                            x=metrics_df['month'],
                            y=metrics_df['profit_factor'],
                            name='Profit Factor',
                            yaxis='y2'
                        ))
                        fig_metrics.update_layout(
                            title='Sharpe Ratio and Profit Factor Over Time',
                            yaxis=dict(title='Sharpe Ratio'),
                            yaxis2=dict(title='Profit Factor', overlaying='y', side='right')
                        )
                        st.plotly_chart(fig_metrics)
                        
                        # R:R vs PnL Scatter Plot
                        fig_scatter = px.scatter(
                            df,
                            x='rr',
                            y='pnl',
                            color='win',
                            title='R:R Ratio vs PnL',
                            labels={'rr': 'Risk:Reward Ratio', 'pnl': 'PnL'}
                        )
                        st.plotly_chart(fig_scatter)
                        
                        # Automated Insights
                        st.subheader("Automated Insights")
                        
                        # Tag-based insights
                        if 'tags' in df.columns and not df['tags'].empty:
                            tag_expectancy = {}
                            for tag in tag_df['tag'].unique():
                                tag_trades = df[df['tags'].apply(lambda x: tag in x)]
                                if not tag_trades.empty:
                                    tag_metrics = calculate_advanced_metrics(tag_trades)
                                    tag_expectancy[tag] = tag_metrics['expectancy']
                            
                            if tag_expectancy:
                                best_tag = max(tag_expectancy.items(), key=lambda x: x[1])
                                st.info(f"Your highest expectancy ({best_tag[1]:.2f}) comes from trades tagged as '{best_tag[0]}'")
                        
                        # Time-based insights
                        df['hour'] = pd.to_datetime(df['exit_date']).dt.hour
                        hourly_win_rates = df.groupby('hour')['win'].mean()
                        if not hourly_win_rates.empty:
                            worst_hour = hourly_win_rates.idxmin()
                            best_hour = hourly_win_rates.idxmax()
                            st.info(f"Your most consistent performance occurs during {best_hour}:00 hours (win rate: {hourly_win_rates[best_hour]:.1%})")
                            st.warning(f"Consider avoiding trades during {worst_hour}:00 hours (win rate: {hourly_win_rates[worst_hour]:.1%})")
                    else:
                        st.info("No trades recorded yet. Add your first trade to see performance metrics.")
                else:
                    st.error(f"Failed to fetch trades. Status code: {response.status_code}")
                    if response.status_code == 401:
                        st.error("Your session has expired. Please log in again.")
                        st.session_state.token = None
                        st.session_state.user = None
                        st.rerun()
                    else:
                        st.error(f"Error details: {response.text}")
            except requests.exceptions.ConnectionError:
                st.error("Could not connect to the server. Please make sure the backend is running.")
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
        
        # Zerodha Integration Section
        elif st.session_state.active_section == 'zerodha':
            st.markdown('<div class="subheader">Zerodha Integration</div>', unsafe_allow_html=True)
            if not st.session_state.zerodha_connected:
                if st.button("Connect with Zerodha"):
                    login_url = zerodha.get_login_url()
                    st.markdown(f"[Click here to connect with Zerodha]({login_url})")
                    
                    request_token = st.text_input("Enter the request token from Zerodha")
                    if request_token:
                        if zerodha.generate_session(request_token):
                            st.session_state.zerodha_connected = True
                            st.session_state.zerodha_profile = zerodha.get_profile()
                            st.success("Successfully connected to Zerodha!")
                        else:
                            st.error("Failed to connect to Zerodha. Please try again.")
            else:
                st.success("Connected to Zerodha!")
                if st.session_state.zerodha_profile:
                    st.write(f"Welcome, {st.session_state.zerodha_profile['user_name']}")
                
                if st.button("Import Trades from Zerodha"):
                    trades = zerodha.fetch_trades()
                    if trades:
                        # Import trades to our database
                        for trade in trades:
                            try:
                                response = requests.post(
                                    f"{API_URL}/trades",
                                    json=trade,
                                    headers={"Authorization": f"Bearer {st.session_state.token}"}
                                )
                                if response.status_code != 200:
                                    st.error(f"Failed to import trade: {response.text}")
                            except Exception as e:
                                st.error(f"Error importing trade: {str(e)}")
                        
                        st.success("Trades imported successfully!")
                        st.rerun()
                    else:
                        st.error("No trades found or error fetching trades from Zerodha")
                
                if st.button("Disconnect Zerodha"):
                    st.session_state.zerodha_connected = False
                    st.session_state.zerodha_profile = None
                    st.success("Disconnected from Zerodha!")
                    st.rerun()

# Update chart colors
def update_chart_style(fig):
    fig.update_layout(
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(color='#1e88e5'),
        title=dict(font=dict(color='#1e88e5')),
        xaxis=dict(
            gridcolor='#e0e0e0',
            linecolor='#1e88e5',
            tickfont=dict(color='#1e88e5')
        ),
        yaxis=dict(
            gridcolor='#e0e0e0',
            linecolor='#1e88e5',
            tickfont=dict(color='#1e88e5')
        )
    )
    return fig

if __name__ == "__main__":
    main() 