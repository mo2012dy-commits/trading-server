import os, json, time, threading, datetime, random, logging
from flask import Flask, request, jsonify
from binance.client import Client
from binance.enums import *
from decimal import Decimal, ROUND_DOWN

app = Flask(__name__)
lock = threading.Lock()

# إعداد السجل
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

# جلب المفاتيح من بيئة السيرفر
client = Client(
    os.getenv("BINANCE_API_KEY"),
    os.getenv("BINANCE_API_SECRET"),
    testnet=True  # اجعلها False للتداول الحقيقي
)

STRATEGY_BANK = "strategy_bank.json"
SYMBOL_CACHE = {}

# حالة الصندوق المؤسسي
FUND_STATE = {
    "max_risk_per_trade": 0.02,
    "max_fund_drawdown": 0.10,
    "peak_equity": 0.0,
    "start_day_equity": 0.0,
    "current_day": ""
}

def get_symbol_precision(symbol):
    global SYMBOL_CACHE
    if symbol in SYMBOL_CACHE: return SYMBOL_CACHE[symbol]
    try:
        info = client.futures_exchange_info()
        for s in info['symbols']:
            if s['symbol'] == symbol:
                step_size = next(f['stepSize'] for f in s['filters'] if f['filterType'] == 'LOT_SIZE')
                SYMBOL_CACHE[symbol] = step_size
                return step_size
    except Exception as e:
        logging.error(f"Precision Error: {e}")
    return None

def sync_fund(equity):
    today = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    if FUND_STATE["current_day"] != today:
        FUND_STATE["current_day"] = today
        FUND_STATE["start_day_equity"] = equity
        FUND_STATE["peak_equity"] = equity
    if equity > FUND_STATE["peak_equity"]:
        FUND_STATE["peak_equity"] = equity

@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "online", "project": "مصنع $ V16"})

@app.route("/trade", methods=["POST"])
def trade():
    with lock:
        try:
            data = request.get_json()
            symbol, side = data["symbol"].upper(), data["side"].upper()
            sl, tp = float(data["sl"]), float(data["tp"])

            acc = client.futures_account()
            equity = float(acc["totalMarginBalance"])
            sync_fund(equity)

            # Kill Switch
            drawdown = (FUND_STATE["peak_equity"] - equity) / FUND_STATE["peak_equity"] if FUND_STATE["peak_equity"] > 0 else 0
            if drawdown >= FUND_STATE["max_fund_drawdown"]:
                return jsonify({"status": "HALTED", "msg": "Drawdown limit reached"}), 403

            # حساب الكمية والدقة
            step_size = get_symbol_precision(symbol)
            curr_price = float(client.futures_symbol_ticker(symbol=symbol)["price"])
            sl_distance = abs(curr_price - sl)
            
            raw_qty = (equity * FUND_STATE["max_risk_per_trade"]) / max(sl_distance, 0.0001)
            qty = float(Decimal(str(raw_qty)).quantize(Decimal(str(step_size)), rounding=ROUND_DOWN))

            if qty <= 0: return jsonify({"status": "ERROR", "msg": "Qty too small"}), 400

            # التنفيذ
            client.futures_change_leverage(symbol=symbol, leverage=75)
            client.futures_create_order(symbol=symbol, side=SIDE_BUY if side == "LONG" else SIDE_SELL, type=ORDER_TYPE_MARKET, quantity=qty)
            
            # أوامر الحماية
            params = {'symbol': symbol, 'closePosition': True, 'workingType': 'MARK_PRICE'}
            client.futures_create_order(side=SIDE_SELL if side == "LONG" else SIDE_BUY, type=ORDER_TYPE_STOP_MARKET, stopPrice=sl, **params)
            client.futures_create_order(side=SIDE_SELL if side == "LONG" else SIDE_BUY, type=ORDER_TYPE_TAKE_PROFIT_MARKET, stopPrice=tp, **params)

            return jsonify({"status": "SUCCESS", "symbol": symbol, "qty": qty})

        except Exception as e:
            logging.error(f"Error: {str(e)}")
            return jsonify({"status": "ERROR", "msg": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
