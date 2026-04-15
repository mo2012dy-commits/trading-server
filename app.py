import os
import time
import threading
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import ccxt
from decimal import Decimal, getcontext, ROUND_HALF_UP
from datetime import datetime
from threading import Lock
from loguru import logger

# 1. إعدادات الدقة المالية (معايير بنكية)
getcontext().prec = 28
app = Flask(__name__)
CORS(app)
# إعداد SocketIO مع دعم eventlet للأداء العالي
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')
trade_lock = Lock()

# 2. جلب المفاتيح من Railway Variables
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_SECRET_KEY = os.getenv("BINANCE_SECRET_KEY")

# إعداد الربط مع Binance Futures
exchange = ccxt.binance({
    'apiKey': BINANCE_API_KEY,
    'secret': BINANCE_SECRET_KEY,
    'enableRateLimit': True,
    'options': {'defaultType': 'future'}
})

class FortressPortfolio:
    def __init__(self, initial_balance):
        self.initial_deposit = Decimal(str(initial_balance))
        self.cash_balance = Decimal(str(initial_balance))
        self.peak_equity = Decimal(str(initial_balance))
        self.open_trades = {}
        self.MAX_DRAWDOWN_PCT = Decimal("20.0")

    def to_decimal(self, value):
        return Decimal(str(value)).quantize(Decimal('0.00000001'), rounding=ROUND_HALF_UP)

    def get_snapshot(self):
        current_prices = {}
        symbols = list(set([t['symbol'] for t in self.open_trades.values()]))
        
        try:
            if symbols:
                tickers = exchange.fetch_tickers(symbols)
                for s in symbols:
                    current_prices[s] = tickers[s]['last']
        except Exception as e:
            logger.error(f"Error fetching futures prices: {e}")

        unrealized_pnl = Decimal("0.0")
        locked_margin = Decimal("0.0")
        
        for tid, trade in self.open_trades.items():
            price = self.to_decimal(current_prices.get(trade['symbol'], trade['entry_price']))
            margin = (trade['qty'] * trade['entry_price']) / trade['leverage']
            locked_margin += margin
            
            direction = Decimal("1") if trade['side'].upper() == "BUY" else Decimal("-1")
            pnl = (price - trade['entry_price']) * trade['qty'] * direction
            unrealized_pnl += pnl

        equity = self.cash_balance + unrealized_pnl
        if equity > self.peak_equity:
            self.peak_equity = equity
        
        drawdown = ((self.peak_equity - equity) / self.peak_equity) * 100
        free_margin = equity - locked_margin

        return {
            "equity": str(equity.quantize(Decimal('0.01'))),
            "cash": str(self.cash_balance.quantize(Decimal('0.01'))),
            "free_margin": str(free_margin.quantize(Decimal('0.01'))),
            "drawdown_pct": str(drawdown.quantize(Decimal('0.01'))),
            "open_trades_count": len(self.open_trades),
            "status": "KILL_SWITCH" if drawdown > self.MAX_DRAWDOWN_PCT else "HEALTHY",
            "server_time": datetime.now().isoformat()
        }

# إنشاء المحفظة برصيد مبدئي 1000
portfolio = FortressPortfolio(1000)

# --- وظيفة البث اللحظي (Background Broadcast) ---
def background_broadcaster():
    """ترسل تحديثات المحفظة للجوال كل ثانية تلقائياً"""
    while True:
        try:
            with trade_lock:
                snapshot = portfolio.get_snapshot()
                socketio.emit('portfolio_update', snapshot)
        except Exception as e:
            logger.error(f"Broadcast Error: {e}")
        time.sleep(1)

# تشغيل البث في خيط منفصل
threading.Thread(target=background_broadcaster, daemon=True).start()

# --- مسارات الـ API التقليدية ---

@app.route('/')
def health_check():
    return jsonify({"status": "online", "name": "مصنع $"}), 200

@app.route('/api/portfolio', methods=['GET'])
def get_portfolio():
    with trade_lock:
        return jsonify(portfolio.get_snapshot())

@app.route('/api/trade/open', methods=['POST'])
def open_trade():
    data = request.json
    with trade_lock:
        trade_id = f"T_{datetime.now().timestamp()}"
        portfolio.open_trades[trade_id] = {
            "symbol": data['symbol'].upper(),
            "side": data['side'].upper(),
            "qty": Decimal(str(data['qty'])),
            "entry_price": Decimal(str(data['entry_price'])),
            "leverage": Decimal(str(data['leverage']))
        }
        # إرسال تحديث فوري بعد فتح الصفقة
        socketio.emit('portfolio_update', portfolio.get_snapshot())
        return jsonify({"status": "success", "trade_id": trade_id})

@app.route('/api/trade/close', methods=['POST'])
def close_trade():
    data = request.json
    trade_id = data.get('trade_id')
    exit_price = data.get('exit_price')
    
    with trade_lock:
        if trade_id in portfolio.open_trades:
            trade = portfolio.open_trades[trade_id]
            direction = Decimal("1") if trade['side'].upper() == "BUY" else Decimal("-1")
            raw_pnl = (Decimal(str(exit_price)) - trade['entry_price']) * trade['qty'] * direction
            margin_reclaimed = (trade['qty'] * trade['entry_price']) / trade['leverage']
            
            portfolio.cash_balance += (margin_reclaimed + raw_pnl)
            del portfolio.open_trades[trade_id]
            
            # إرسال تحديث فوري بعد إغلاق الصفقة
            socketio.emit('portfolio_update', portfolio.get_snapshot())
            return jsonify({"status": "success", "new_balance": str(portfolio.cash_balance)})
        return jsonify({"status": "error", "message": "Trade not found"}), 404

# --- معالجة أحداث SocketIO ---
@socketio.on('connect')
def handle_connect():
    logger.info("جهاز جديد اتصل بالمصنع")
    emit('portfolio_update', portfolio.get_snapshot())

if __name__ == "__main__":
    # استخدام socketio.run بدلاً من app.run لدعم البث المباشر
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port)
