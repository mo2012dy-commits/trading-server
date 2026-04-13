import os
from flask import Flask, jsonify, request
from flask_cors import CORS
import ccxt
import pandas as pd
import pandas_ta as ta
from datetime import datetime

app = Flask(__name__)
CORS(app)

# الربط مع بينانس
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
        last_price = df.iloc[-1]['close']
        return {"price": last_price, "rsi": round(df.iloc[-1]['rsi'], 2)}
    except: return None

@app.route('/')
def dashboard():
    try:
        real_balance = exchange.fetch_balance()
        status = fetch_indicators()
        
        current_alerts = []
        if status['rsi'] < 30:
            current_alerts.append({"type": "BUY_SIGNAL", "msg": "فرصة شراء: RSI متشبع بيعياً!"})
        elif status['rsi'] > 70:
            current_alerts.append({"type": "SELL_SIGNAL", "msg": "فرصة بيع: RSI متشبع شرائياً!"})

        current_paper_pnl = 0
        for trade in paper_trades:
            if trade['status'] == 'OPEN':
                diff = status['price'] - trade['entry_price']
                current_paper_pnl += diff if trade['side'] == 'buy' else -diff

        return jsonify({
            'status': 'online',
            'real_equity': real_balance['info']['totalMarginBalance'],
            'market_price': status['price'],
            'market_rsi': status['rsi'],
            'alerts': current_alerts,
            'paper_trades_count': len([t for t in paper_trades if t['status'] == 'OPEN']),
            'total_paper_pnl': round(current_paper_pnl, 2)
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
            'symbol': data.get('symbol', 'BTC/USDT'),
            'side': data.get('side'),
            'entry_price': status['price'],
            'amount': data.get('amount', 0.001),
            'status': 'OPEN',
            'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        paper_trades.append(new_trade)
        return jsonify({'status': 'success', 'trade': new_trade})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/kill', methods=['POST'])
def kill_switch():
    closed_count = 0
    for trade in paper_trades:
        if trade['status'] == 'OPEN':
            trade['status'] = 'CLOSED'
            closed_count += 1
    return jsonify({'status': 'success', 'closed_paper_trades': closed_count})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
