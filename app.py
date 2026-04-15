import os, ccxt, uuid, json, pandas as pd, pandas_ta as ta
from flask import Flask, jsonify, request
from flask_cors import CORS
from threading import Lock
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)
CORS(app)
trade_lock = Lock()

# --- إعدادات التخزين المنفصلة ---
SIM_FILE = "sim_data.json"
LIVE_FILE = "live_data.json"

def load_storage(file_path, initial_balance=1000.0):
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r') as f: return json.load(f)
        except: pass
    return {"balance": initial_balance, "open_trades": [], "history": [], "ai_enabled": False}

def save_storage(data, file_path):
    with open(file_path, 'w') as f: json.dump(data, f, indent=4)

# تحميل البيانات
sim_data = load_storage(SIM_FILE, 1000.0)
live_data = load_storage(LIVE_FILE, 0.0)

# الربط مع بينانس باستخدام مفاتيح Railway
exchange = ccxt.binance({
    'apiKey': os.environ.get('BINANCE_API_KEY'),
    'secret': os.environ.get('BINANCE_SECRET_KEY'),
    'enableRateLimit': True,
    'options': {'defaultType': 'future'}
})

# --- ذكاء اصطناعي مدمج (TradeAI) ---
class TradeAI:
    def __init__(self):
        self.symbol = "BTC/USDT"
        
    def analyze(self):
        try:
            bars = exchange.fetch_ohlcv(self.symbol.replace('/',''), timeframe='15m', limit=50)
            df = pd.DataFrame(bars, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
            rsi = ta.rsi(df['c'], length=14).iloc[-1]
            ema_short = ta.ema(df['c'], length=9).iloc[-1]
            ema_long = ta.ema(df['c'], length=21).iloc[-1]
            
            if rsi < 35 and ema_short > ema_long: return "BUY"
            if rsi > 65 and ema_short < ema_long: return "SELL"
            return None
        except: return None

ai_engine = TradeAI()

# --- محرك التداول المطور ---
def update_engine():
    with trade_lock:
        run_engine_logic(sim_data, SIM_FILE)
        run_engine_logic(live_data, LIVE_FILE)

def run_engine_logic(data_source, file_path):
    for trade in data_source["open_trades"][:]:
        try:
            curr_p = float(exchange.fetch_ticker(trade['symbol'].replace('/', ''))['last'])
            direction = 1 if trade['side'] == 'BUY' else -1
            trade['pnl'] = round((curr_p - trade['entry_price']) * trade['quantity'] * trade['leverage'] * direction, 2)
            
            # فحص الإغلاق التلقائي (SL/TP)
            if (trade.get('sl') and ((direction==1 and curr_p<=trade['sl']) or (direction==-1 and curr_p>=trade['sl']))) or \
               (trade.get('tp') and ((direction==1 and curr_p>=trade['tp']) or (direction==-1 and curr_p<=trade['tp']))):
                close_trade_logic(data_source, trade, curr_p, file_path, "AUTO_EXIT")
        except: continue

def close_trade_logic(data_source, trade, exit_price, file_path, reason):
    data_source["balance"] += trade['pnl']
    trade.update({"status": "CLOSED", "exit_price": exit_price, "reason": reason, "close_time": datetime.now().isoformat()})
    data_source["history"].append(trade)
    data_source["open_trades"].remove(trade)
    save_storage(data_source, file_path)

# --- المسارات (Endpoints) المحدثة بدقة ---

@app.route('/status', methods=['GET'])
def get_status():
    mode = request.args.get('mode', 'SIMULATION')
    btc_price = float(exchange.fetch_ticker('BTCUSDT')['last'])
    
    if mode == 'LIVE':
        try:
            # جلب الرصيد الحقيقي من بينانس
            balance_info = exchange.fetch_balance()
            live_data["balance"] = balance_info['total'].get('USDT', 0.0)
            data = live_data
        except: data = live_data
    else:
        data = sim_data
    
    return jsonify({
        "mode": mode,
        "price": btc_price,
        "financials": {"balance": round(data["balance"], 2)},
        "open_trades": data["open_trades"],
        "history": data.get("history", []),
        "ai_status": data.get("ai_enabled", False)
    })

@app.route('/close_trade', methods=['POST'])
def handle_close_trade():
    req = request.json
    mode = req.get('mode', 'SIMULATION')
    trade_id = req.get('id') # نستخدم المعرف لضمان الدقة
    data_source = sim_data if mode == 'SIMULATION' else live_data
    file_path = SIM_FILE if mode == 'SIMULATION' else LIVE_FILE

    with trade_lock:
        trade = next((t for t in data_source["open_trades"] if t['id'] == trade_id), None)
        if trade:
            try:
                curr_p = float(exchange.fetch_ticker(trade['symbol'].replace('/', ''))['last'])
                close_trade_logic(data_source, trade, curr_p, file_path, "MANUAL_CLOSE")
                return jsonify({"status": "success", "msg": "تم إغلاق الصفقة بنجاح"})
            except Exception as e:
                return jsonify({"status": "error", "msg": str(e)})
        return jsonify({"status": "error", "msg": "الصفقة غير موجودة"})

@app.route('/trade', methods=['POST'])
def handle_trade():
    req = request.json
    mode = req.get('mode', 'SIMULATION')
    data_source = sim_data if mode == 'SIMULATION' else live_data
    file_path = SIM_FILE if mode == 'SIMULATION' else LIVE_FILE
    
    with trade_lock:
        try:
            price = float(exchange.fetch_ticker(req['symbol'].replace('/',''))['last'])
            new_trade = {
                "id": str(uuid.uuid4())[:6],
                "symbol": req['symbol'],
                "side": req['side'],
                "entry_price": price,
                "quantity": float(req['quantity']),
                "leverage": int(req['leverage']),
                "sl": float(req['sl']) if req.get('sl') else None,
                "tp": float(req['tp']) if req.get('tp') else None,
                "pnl": 0.0,
                "timestamp": datetime.now().isoformat()
            }
            data_source["open_trades"].append(new_trade)
            save_storage(data_source, file_path)
            return jsonify({"status": "success", "trade": new_trade})
        except Exception as e:
            return jsonify({"status": "error", "msg": str(e)})

@app.route('/toggle_ai', methods=['POST'])
def toggle_ai():
    mode = request.json.get('mode', 'SIMULATION')
    data = sim_data if mode == 'SIMULATION' else live_data
    data["ai_enabled"] = not data.get("ai_enabled", False)
    save_storage(data, SIM_FILE if mode == 'SIMULATION' else LIVE_FILE)
    return jsonify({"ai_enabled": data["ai_enabled"]})

scheduler = BackgroundScheduler()
scheduler.add_job(update_engine, 'interval', seconds=5)
scheduler.start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
