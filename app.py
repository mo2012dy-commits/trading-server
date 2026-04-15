import os
from flask import Flask, jsonify, request
from flask_cors import CORS
import ccxt
from decimal import Decimal, getcontext, ROUND_HALF_UP
from datetime import datetime
from threading import Lock
from loguru import logger

# 1. إعدادات الدقة المالية (معايير بنكية)
getcontext().prec = 28
app = Flask(__name__)
CORS(app)
trade_lock = Lock()

# 2. جلب المفاتيح من Railway Variables
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_SECRET_KEY = os.getenv("BINANCE_SECRET_KEY")

# إعداد الربط مع Binance Futures حصراً لضمان دقة الأسعار
exchange = ccxt.binance({
    'apiKey': BINANCE_API_KEY,
    'secret': BINANCE_SECRET_KEY,
    'enableRateLimit': True,
    'options': {'defaultType': 'future'} # تحديد وضع العقود الآجلة
})

class FortressPortfolio:
    def __init__(self, initial_balance):
        self.initial_deposit = Decimal(str(initial_balance))
        self.cash_balance = Decimal(str(initial_balance))
        self.peak_equity = Decimal(str(initial_balance))
        self.ledger = []
        self.open_trades = {}
        self.MAX_DRAWDOWN_PCT = Decimal("20.0")

    def to_decimal(self, value):
        return Decimal(str(value)).quantize(Decimal('0.00000001'), rounding=ROUND_HALF_UP)

    def get_snapshot(self):
        # جلب أسعار مارك (Mark Prices) للفيوتشر لضمان دقة حساب الأرباح والتصفية
        current_prices = {}
        symbols = list(set([t['symbol'] for t in self.open_trades.values()]))
        
        try:
            if symbols:
                # fetch_tickers في وضع الفيوتشر تجلب أسعار العقود الآجلة الحالية
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

# إنشاء المحفظة (ابدأ بالرصيد المبدئي الذي تفضله)
portfolio = FortressPortfolio(1000)

# --- مسارات الـ API (Endpoints) ---

@app.route('/')
def health_check():
    return jsonify({"status": "online", "name": "مصنع $"}), 200

@app.route('/api/portfolio', methods=['GET'])
def get_portfolio():
    with trade_lock:
        return jsonify(portfolio.get_snapshot())

# مسار لجلب شارت الفيوتشر الحقيقي (Candlesticks)
@app.route('/api/chart/<symbol>', methods=['GET'])
def get_futures_chart(symbol):
    try:
        timeframe = request.args.get('timeframe', '1h')
        # جلب بيانات الشموع من محرك الفيوتشر حصراً
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=100)
        return jsonify(ohlcv)
    except Exception as e:
        logger.error(f"Chart Error for {symbol}: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/api/trade/open', methods=['POST'])
def open_trade():
    data = request.json
    with trade_lock:
        trade_id = f"T_{datetime.now().timestamp()}"
        portfolio.open_trades[trade_id] = {
            "symbol": data['symbol'].upper(), # التأكد من صيغة الرمز مثل BTC/USDT أو BTCUSDT
            "side": data['side'].upper(),
            "qty": Decimal(str(data['qty'])),
            "entry_price": Decimal(str(data['entry_price'])),
            "leverage": Decimal(str(data['leverage']))
        }
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
            
            # تحديث الرصيد وتسجيل العملية
            portfolio.cash_balance += (margin_reclaimed + raw_pnl)
            del portfolio.open_trades[trade_id]
            
            return jsonify({"status": "success", "new_balance": str(portfolio.cash_balance)})
        return jsonify({"status": "error", "message": "Trade not found"}), 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
