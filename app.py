import os
import ccxt
import pandas as pd
import pandas_ta as ta
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# 1. إعداد الربط مع بينانس (المحفظة الحقيقية)
exchange = ccxt.binance({
    'apiKey': os.environ.get('BINANCE_API_KEY'),
    'secret': os.environ.get('BINANCE_SECRET_KEY'),
    'enableRateLimit': True,
    'options': {'defaultType': 'future'}
})

# 2. ذاكرة التداول التجريبي وتتبع السعر
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
        
        # جلب الرصيد الحقيقي
        balance_info = exchange.fetch_balance()
        real_balance = round(float(balance_info['total'].get('USDT', 0)), 2)
        
        alerts = []
        # منطق تنبيه الـ 500$ (عرض داخلي فقط)
        if paper_trading["last_notified_price"] == 0:
            paper_trading["last_notified_price"] = current_price
            
        price_diff = current_price - paper_trading["last_notified_price"]
        if abs(price_diff) >= 500:
            direction = "ارتفاع" if price_diff > 0 else "انخفاض"
            alerts.append({
                "msg": f"تغير السعر بمقدار {abs(int(price_diff))}$! السعر الحالي: {current_price}",
                "type": "PRICE"
            })
            paper_trading["last_notified_price"] = current_price

        if current_rsi > 70:
            alerts.append({"msg": "RSI مرتفع (بيع) 🚨", "type": "SELL"})
        elif current_rsi < 30:
            alerts.append({"msg": "RSI منخفض (شراء) ✅", "type": "BUY"})
            
        return {
            "symbol": symbol,
            "price": current_price,
            "rsi": current_rsi,
            "real_balance": real_balance,
            "paper_balance": round(paper_trading["balance"], 2),
            "pnl": 0.0,
            "trades_count": len(paper_trading["history"]),
            "alerts": alerts,
            "trend": "صاعد" if current_price > df['EMA_20'].iloc[-1] else "هابط"
        }
    except Exception as e:
        return None

@app.route('/trade', methods=['POST'])
def execute_trade():
    trade_data = request.json
    paper_trading["history"].append(trade_data)
    return jsonify({"status": "success"})

@app.route('/status', methods=['GET'])
def status():
    result = get_market_analysis()
    if result:
        return jsonify(result)
    return jsonify({"error": "Data error"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
