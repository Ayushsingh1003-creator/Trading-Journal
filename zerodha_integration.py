from kiteconnect import KiteConnect
import pandas as pd
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

class ZerodhaIntegration:
    def __init__(self):
        self.api_key = os.getenv("ZERODHA_API_KEY")
        self.api_secret = os.getenv("ZERODHA_API_SECRET")
        self.kite = None
        self.access_token = None

    def get_login_url(self):
        """Generate login URL for Zerodha"""
        kite = KiteConnect(api_key=self.api_key)
        return kite.login_url()

    def generate_session(self, request_token):
        """Generate session using request token"""
        try:
            kite = KiteConnect(api_key=self.api_key)
            data = kite.generate_session(request_token, api_secret=self.api_secret)
            self.access_token = data["access_token"]
            self.kite = KiteConnect(api_key=self.api_key)
            self.kite.set_access_token(self.access_token)
            return True
        except Exception as e:
            print(f"Error generating session: {str(e)}")
            return False

    def fetch_trades(self, days=30):
        """Fetch trades from Zerodha"""
        try:
            if not self.kite:
                return None

            # Get trades for the last 30 days
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Fetch orders
            orders = self.kite.orders()
            
            # Convert to DataFrame
            df = pd.DataFrame(orders)
            
            # Filter completed trades
            completed_trades = df[df['status'] == 'COMPLETE']
            
            # Process trades
            processed_trades = []
            for _, trade in completed_trades.iterrows():
                processed_trade = {
                    "asset": trade['tradingsymbol'],
                    "entry_price": float(trade['average_price']),
                    "exit_price": float(trade['average_price']),  # Same as entry for now
                    "position_size": float(trade['quantity']),
                    "entry_date": trade['order_timestamp'].isoformat(),
                    "exit_date": trade['order_timestamp'].isoformat(),
                    "direction": "LONG" if trade['transaction_type'] == 'BUY' else "SHORT",
                    "strategy": "Zerodha Import",
                    "notes": f"Order ID: {trade['order_id']}"
                }
                processed_trades.append(processed_trade)
            
            return processed_trades
        except Exception as e:
            print(f"Error fetching trades: {str(e)}")
            return None

    def get_profile(self):
        """Get user profile from Zerodha"""
        try:
            if not self.kite:
                return None
            return self.kite.profile()
        except Exception as e:
            print(f"Error fetching profile: {str(e)}")
            return None 