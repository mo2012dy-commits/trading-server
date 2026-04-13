import os
from flask import Flask, jsonify, request
from flask_cors import CORS
import ccxt
import pandas as pd
import pandas_ta as ta
from datetime import datetime

app = Flask(__name__)
CORS(app)

exchange = ccxt.binance({
    'apiKey': os.getenv('BINANCE_API_KEY'),
    'secret': os.getenv('BINANCE_SECRET_KEY'),
    'options': {'defaultType': 'future'},
    'enableRateLimit': True
})

paper_trades = []

def fetch_indicators(symbol="BTC/USDT"):
    try:
        bars = exchange.fetch_ohlcv(symbol, timeframe="15m", limit=100)
        df = pd.DataFrame(bars, columns=['ts', 'open', 'high', 'low', 'close', 'vol'])
        df['rsi'] = ta.rsi(df['close'], length=14)
        last_row = df.iloc[-1]
        return {"price": last_row['close'], "rsi": round(last_row['rsi'], 2)}
    except: return None

@app.route('/')
def dashboard():
    try:
        real_balance = exchange.fetch_balance()
        status = fetch_indicators()
        active_alerts = []
        if status['rsi'] <= 30: active_alerts.append({"type": "BUY", "msg": "شراء! RSI منخفض"})
        elif status['rsi'] >= 70: active_alerts.append({"type": "SELL", "msg": "بيع! RSI مرتفع"})

        current_pnl = 0
        for trade in paper_trades:
            if trade['status'] == 'OPEN':
                diff = status['price'] - trade['entry_price']
                current_pnl += diff if trade['side'] == 'buy' else -diff

        return jsonify({
            'status': 'online',
            'real_equity': real_balance['info']['totalMarginBalance'],
            'market_price': status['price'],
            'market_rsi': status['rsi'],
            'alerts': active_alerts,
            'paper_trades_count': len([t for t in paper_trades if t['status'] == 'OPEN']),
            'total_paper_pnl': round(current_pnl, 2)
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/trade', methods=['POST'])
def place_paper_order():
    try:
        data = request.json
        status = fetch_indicators()
        new_trade = {
            'id': len(paper_trades) + 1,
            'symbol': 'BTC/USDT',
            'side': data.get('side'),
            'entry_price': status['price'],
            'status': 'OPEN',
            'time': datetime.now().strftime("%H:%M:%S")
        }
        paper_trades.append(new_trade)
        return jsonify({'status': 'success', 'trade': new_trade})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
