import os
from flask import Flask, jsonify
import ccxt

app = Flask(__name__)

# الربط مع بينانس باستخدام الأسماء المطابقة لـ Railway Variables عندك
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
        total_equity = balance['info']['totalMarginBalance']
        
        # جلب الصفقات المفتوحة
        positions = exchange.fetch_positions()
        active_trades = []
        for pos in positions:
            if float(pos['contracts']) > 0:
                active_trades.append({
                    'pair': pos['symbol'],
                    'side': pos['side'],
                    'pnl': str(round(float(pos['unrealizedPnl']), 2)),
                    'percentage': str(round(float(pos['percentage']), 2))
                })

        return jsonify({
            'status': 'online',
            'equity': total_equity,
            'active_trades': active_trades
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

if __name__ == '__main__':
    # استخدام بورت Railway التلقائي
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
