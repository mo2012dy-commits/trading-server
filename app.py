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
sim_data = load_storage(SIM_FILE, 1000.0) # رصيد تجريبي 1000$
live_data = load_storage(LIVE_FILE, 0.0)  # رصيد حقيقي

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
            # جلب آخر 50 شمعة (إطار 15 دقيقة)
            bars = exchange.fetch_ohlcv(self.symbol.replace('/',''), timeframe='15m', limit=50)
            df = pd.DataFrame(bars, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
            
            # مؤشرات تقنية بسيطة
            rsi = ta.rsi(df['c'], length=14).iloc[-1]
            ema_short = ta.ema(df['c'], length=9).iloc[-1]
            ema_long = ta.ema(df['c'], length=21).iloc[-1]
            
            print(f"🤖 [AI Logic] RSI: {rsi:.2f} | EMA: {ema_short:.2f}/{ema_long:.2f}")
            
            # استراتيجية الدخول
            if rsi < 35 and ema_short > ema_long: return "BUY"
            if rsi > 65 and ema_short < ema_long: return "SELL"
            return None
        except Exception as e:
            print(f"AI Analysis Error: {e}")
            return None

ai_engine = TradeAI()

# --- محرك التداول والتحكم ---
def update_engine():
    with trade_lock:
        # تحديث بيانات SIMULATION
        run_engine_logic(sim_data, SIM_FILE)
        # تحديث بيانات LIVE
        run_engine_logic(live_data, LIVE_FILE)

def run_engine_logic(data_source, file_path):
    if not data_source["open_trades"]:
        # إذا كان الـ AI مفعل ولا توجد صفقات، نقوم بالتحليل
        if data_source.get("ai_enabled"):
            signal = ai_engine.analyze()
            if signal:
                print(f"🤖 AI Signal Found: {signal} for {file_path}")
                # هنا يمكن استدعاء دالة فتح الصفقة آلياً (سأتركها لك للتفعيل عند الجاهزية)
    
    # تحديث الـ PnL والأسعار
    for trade in data_source["open_trades"][:]:
        try:
            curr_p = float(exchange.fetch_ticker(trade['symbol'].replace('/', ''))['last'])
            direction = 1 if trade['side'] == 'BUY' else -1
            trade['pnl'] = round((curr_p - trade['entry_price']) * trade['quantity'] * trade['leverage'] * direction, 2)
            
            # فحص الإغلاق التلقائي (SL/TP)
            if (trade['sl'] and ((direction==1 and curr_p<=trade['sl']) or (direction==-1 and curr_p>=trade['sl']))) or \
               (trade['tp'] and ((direction==1 and curr_p>=trade['tp']) or (direction==-1 and curr_p<=trade['tp']))):
                close_trade_logic(data_source, trade, curr_p, file_path, "AI_AUTO_EXIT")
        except: continue

def close_trade_logic(data_source, trade, exit_price, file_path, reason):
    data_source["balance"] += trade['pnl']
    trade.update({"status": "CLOSED", "exit_price": exit_price, "reason": reason})
    data_source["history"].append(trade)
    data_source["open_trades"].remove(trade)
    save_storage(data_source, file_path)

# --- المسارات (Endpoints) ---

@app.route('/status', methods=['GET'])
def get_status():
    mode = request.args.get('mode', 'SIMULATION')
    data = sim_data if mode == 'SIMULATION' else live_data
    btc_price = float(exchange.fetch_ticker('BTCUSDT')['last'])
    
    return jsonify({
        "mode": mode,
        "price": btc_price,
        "financials": {"balance": round(data["balance"], 2)},
        "open_trades": data["open_trades"],
        "ai_status": data.get("ai_enabled", False)
    })

@app.route('/toggle_ai', methods=['POST'])
def toggle_ai():
    mode = request.json.get('mode', 'SIMULATION')
    data = sim_data if mode == 'SIMULATION' else live_data
    data["ai_enabled"] = not data.get("ai_enabled", False)
    save_storage(data, SIM_FILE if mode == 'SIMULATION' else LIVE_FILE)
    return jsonify({"ai_enabled": data["ai_enabled"]})

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
                "quantity": req['quantity'],
                "leverage": req['leverage'],
                "sl": req.get('sl'),
                "tp": req.get('tp'),
                "pnl": 0.0,
                "timestamp": datetime.now().isoformat()
            }
            data_source["open_trades"].append(new_trade)
            save_storage(data_source, file_path)
            return jsonify({"status": "success", "trade": new_trade})
        except Exception as e:
            return jsonify({"status": "error", "msg": str(e)})

scheduler = BackgroundScheduler()
scheduler.add_job(update_engine, 'interval', seconds=5)
scheduler.start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
