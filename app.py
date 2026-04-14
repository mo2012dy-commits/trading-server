import os
import ccxt
import pandas as pd
import pandas_ta as ta
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# إعداد الربط مع بينانس
exchange = ccxt.binance()

def get_market_analysis(symbol='BTC/USDT'):
    try:
        # جلب بيانات الشموع (5 دقائق)
        bars = exchange.fetch_ohlcv(symbol, timeframe='5m', limit=100)
        df = pd.DataFrame(bars, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
        
        # حساب المؤشرات الفنية
        df['RSI'] = ta.rsi(df['close'], length=14)
        df['EMA_20'] = ta.ema(df['close'], length=20)
        
        current_price = df['close'].iloc[-1]
        current_rsi = df['RSI'].iloc[-1]
        
        # منطق التنبيهات الذكي
        alerts = []
        if current_rsi > 70:
            alerts.append({"msg": "RSI مرتفع جداً - منطقة تشبع بيع 🚨", "type": "SELL"})
        elif current_rsi < 30:
            alerts.append({"msg": "RSI منخفض جداً - فرصة شراء ✅", "type": "BUY"})
            
        return {
            "symbol": symbol,
            "price": float(current_price),
            "rsi": round(float(current_rsi), 2),
            "balance": 901.34, # سيتم ربطه لاحقاً بالرصيد الحي
            "pnl": 54.5,
            "trades": 3,
            "alerts": alerts,
            "trend": "صاعد" if current_price > df['EMA_20'].iloc[-1] else "هابط"
        }
    except Exception as e:
        print(f"خطأ في التحليل: {e}")
        return None

@app.route('/status', methods=['GET'])
def status():
    result = get_market_analysis()
    if result:
        return jsonify(result)
    return jsonify({"error": "فشل في جلب البيانات"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
