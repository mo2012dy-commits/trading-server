import os
import ccxt
import pandas as pd
import pandas_ta as ta
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# 1. الربط باستخدام المفاتيح المحفوظة في Railway (التي تم التأكد من وجودها)
exchange = ccxt.binance({
    'apiKey': os.environ.get('BINANCE_API_KEY'),
    'secret': os.environ.get('BINANCE_SECRET_KEY'),
    'enableRateLimit': True,
    'options': {
        'defaultType': 'future',  # لضمان قراءة محفظة العقود الآجلة
    }
})

def get_market_analysis(symbol='BTC/USDT'):
    try:
        # 2. جلب بيانات الشموع للتحليل الفني
        bars = exchange.fetch_ohlcv(symbol, timeframe='5m', limit=100)
        df = pd.DataFrame(bars, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
        
        # حساب المؤشرات (RSI و EMA)
        df['RSI'] = ta.rsi(df['close'], length=14)
        df['EMA_20'] = ta.ema(df['close'], length=20)
        
        current_price = df['close'].iloc[-1]
        current_rsi = df['RSI'].iloc[-1]
        
        # 3. جلب الرصيد الحقيقي من محفظة USDT
        balance_info = exchange.fetch_balance()
        current_balance = balance_info['total'].get('USDT', 0)
        
        # 4. نظام التنبيهات
        alerts = []
        if current_rsi > 70:
            alerts.append({"msg": "RSI مرتفع جداً - منطقة تشبع بيع 🚨", "type": "SELL"})
        elif current_rsi < 30:
            alerts.append({"msg": "RSI منخفض جداً - فرصة شراء ✅", "type": "BUY"})
            
        return {
            "symbol": symbol,
            "price": float(current_price),
            "rsi": round(float(current_rsi), 2),
            "balance": round(float(current_balance), 2),
            "pnl": 54.5, # سيتم ربطه بـ PNL الصفقات المفتوحة لاحقاً
            "trades": 3,
            "alerts": alerts,
            "trend": "صاعد" if current_price > df['EMA_20'].iloc[-1] else "هابط"
        }
    except Exception as e:
        print(f"خطأ في جلب البيانات: {e}")
        return None

@app.route('/status', methods=['GET'])
def status():
    result = get_market_analysis()
    if result:
        return jsonify(result)
    return jsonify({"error": "فشل في جلب البيانات من بينانس"}), 500

if __name__ == '__main__':
    # التأكد من عمل السيرفر على المنفذ الصحيح في Railway
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
