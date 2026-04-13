import os
from flask import Flask, jsonify
import ccxt

app = Flask(__name__)

# إعداد الربط مع بينانس باستخدام مفاتيحك الحالية في Railway
exchange = ccxt.binance({
    'apiKey': os.getenv('BINANCE_API_KEY'),
    'secret': os.getenv('BINANCE_SECRET_KEY'),
    'options': {'defaultType': 'future'},
    'enableRateLimit': True
})

@app.route('/')
def home():
    try:
        # جلب بيانات المحفظة
        balance = exchange.fetch_balance()
        # التأكد من وجود البيانات قبل الحساب لمنع الـ Crash
        if 'info' in balance and 'totalMarginBalance' in balance['info']:
            total_equity = balance['info']['totalMarginBalance']
        else:
            total_equity = "0.00"
            
        return jsonify({
            'status': 'online',
            'equity': total_equity,
            'active_trades': []
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

if __name__ == '__main__':
    # بورت 5000 أو البورت الذي يحدده Railway
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
