import os
import ccxt
import pandas as pd
import pandas_ta as ta
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# إعداد منصة بينانس
exchange = ccxt.binance()

def fetch_data_and_analyze():
    try:
        # 1. جلب الشموع الأخيرة (لحساب RSI دقيق)
        bars = exchange.fetch_ohlcv('BTC/USDT', timeframe='5m', limit=50)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # 2. حساب الـ RSI الحقيقي باستخدام pandas_ta
        df['rsi'] = ta.rsi(df['close'], length=14)
        current_rsi = df['rsi'].iloc[-1]
        current_price = df['close'].iloc[-1]
        
        # 3. نظام التنبيهات البسيط
        alerts = []
        if current_rsi > 70:
            alerts.append({"msg": "منطقة بيع - RSI مرتفع 🚨", "type": "SELL"})
        elif current_rsi < 30:
            alerts.append({"msg": "منطقة شراء - RSI منخفض ✅", "type": "BUY"})

        return {
            "symbol": "BTC/USDT",
            "price": str(current_price),
            "rsi": str(round(current_rsi, 2)),
            "balance": "901.34",  # سنربطها بالمحفظة لاحقاً
            "pnl": "54.5",
            "trades": "3",
            "alerts": alerts
        }
    except Exception as e:
        print(f"Error: {e}")
        return None

@app.route('/status', methods=['GET'])
def get_status():
    data = fetch_data_and_analyze()
    if data:
        return jsonify(data)
    return jsonify({"error": "Failed to fetch data"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
