import os
import ccxt
import pandas as pd
import pandas_ta as ta
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# 1. إعداد الربط مع بينانس (الحقيقية)
exchange = ccxt.binance({
    'apiKey': os.environ.get('BINANCE_API_KEY'),
    'secret': os.environ.get('BINANCE_SECRET_KEY'),
    'enableRateLimit': True,
    'options': {'defaultType': 'future'}
})

# 2. ذاكرة التداول التجريبي
paper_trading = {
    "balance": 10000.0,
    "history": [],
    "last_notified_price": 0.0
}

def get_market_analysis(symbol='BTC/USDT'):
    try:
        bars = exchange.fetch_ohlcv(symbol, timeframe='5m', limit=100)
        df = pd.DataFrame(bars, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
        
        df['RSI'] = ta.rsi(df['close'], length=14)
        df['EMA_20'] = ta.ema(df['close'], length=20)
        
        current_price = float(df['close'].iloc[-1])
        current_rsi = round(float(df['RSI'].iloc[-1]), 2)
        
        balance_info = exchange.fetch_balance()
        real_balance = round(float(balance_info['total'].get('USDT', 0)), 2)
        
        alerts = []
        # تنبيه الـ 500$ داخلي
        if paper_trading["last_notified_price"] == 0:
            paper_trading["last_notified_price"] = current_price
            
        if abs(current_price - paper_trading["last_notified_price"]) >= 500:
            alerts.append({"msg": f"تغير السعر بـ 500$! الحالي: {current_price}", "type": "INFO"})
            paper_trading["last_notified_price"] = current_price

        return {
            "symbol": symbol, "price": current_price, "rsi": current_rsi,
            "real_balance": real_balance, "paper_balance": round(paper_trading["balance"], 2),
            "pnl": 0.0, "trades_count": len(paper_trading["history"]),
            "alerts": alerts, "trend": "صاعد" if current_price > df['EMA_20'].iloc[-1] else "هابط"
        }
    except Exception as e:
        return None

@app.route('/status', methods=['GET'])
def status():
    res = get_market_analysis()
    return jsonify(res) if res else (jsonify({"error": "err"}), 500)

@app.route('/trade', methods=['POST'])
def trade():
    paper_trading["history"].append(request.json)
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
