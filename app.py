import os, ccxt, uuid, json, pandas as pd, pandas_ta as ta
from flask import Flask, jsonify, request
from flask_cors import CORS
from threading import Lock
from datetime import datetime

app = Flask(__name__)
CORS(app)
trade_lock = Lock()

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

sim_data = load_storage(SIM_FILE, 1000.0)
live_data = load_storage(LIVE_FILE, 0.0)

exchange = ccxt.binance({
    'apiKey': os.environ.get('BINANCE_API_KEY'),
    'secret': os.environ.get('BINANCE_SECRET_KEY'),
    'enableRateLimit': True,
    'options': {'defaultType': 'future'}
})

@app.route('/status', methods=['GET'])
def get_status():
    mode = request.args.get('mode', 'SIMULATION')
    data = sim_data if mode == 'SIMULATION' else live_data
    try:
        btc_price = float(exchange.fetch_ticker('BTCUSDT')['last'])
    except: btc_price = 0.0
    
    # الهيكلية المعتمدة لمنع Render Error
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
    trade_id = req.get('id')
    data_source = sim_data if mode == 'SIMULATION' else live_data
    file_path = SIM_FILE if mode == 'SIMULATION' else LIVE_FILE

    with trade_lock:
        trade = next((t for t in data_source["open_trades"] if t['id'] == trade_id), None)
        if trade:
            try:
                curr_p = float(exchange.fetch_ticker(trade['symbol'].replace('/', ''))['last'])
                # منطق الإغلاق ونقل البيانات للسجل
                data_source["balance"] += trade.get('pnl', 0)
                trade.update({"status": "CLOSED", "exit_price": curr_p, "close_time": datetime.now().isoformat()})
                data_source["history"].append(trade)
                data_source["open_trades"].remove(trade)
                save_storage(data_source, file_path)
                return jsonify({"status": "success"})
            except: return jsonify({"status": "error"})
        return jsonify({"status": "error"})

@app.route('/trade', methods=['POST'])
def handle_trade():
    req = request.json
    mode = req.get('mode', 'SIMULATION')
    data_source = sim_data if mode == 'SIMULATION' else live_data
    with trade_lock:
        try:
            price = float(exchange.fetch_ticker(req['symbol'].replace('/',''))['last'])
            new_trade = {
                "id": str(uuid.uuid4())[:6], "symbol": req['symbol'], "side": req['side'],
                "entry_price": price, "quantity": float(req['quantity']), "leverage": int(req['leverage']),
                "pnl": 0.0, "timestamp": datetime.now().isoformat()
            }
            data_source["open_trades"].append(new_trade)
            save_storage(data_source, SIM_FILE if mode == 'SIMULATION' else LIVE_FILE)
            return jsonify({"status": "success", "trade": new_trade})
        except: return jsonify({"status": "error"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
