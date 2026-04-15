import os, ccxt, uuid, json, pandas as pd, pandas_ta as ta
from flask import Flask, jsonify, request
from flask_cors import CORS
from threading import Lock
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)
CORS(app)
trade_lock = Lock()

# --- الإعدادات العامة (مصنع $) ---
TRADING_MODE = "SIMULATION" 
DATA_FILE = "trading_data.json"

# 1. إعداد الربط مع بينانس
exchange = ccxt.binance({
    'apiKey': os.environ.get('BINANCE_API_KEY'),
    'secret': os.environ.get('BINANCE_SECRET_KEY'),
    'enableRateLimit': True,
    'options': {'defaultType': 'future'}
})

# 2. نظام التخزين الدائم
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f: return json.load(f)
        except: pass
    return {"balance": 10000.0, "peak_equity": 10000.0, "open_trades": [], "history": []}

def save_data():
    with open(DATA_FILE, 'w') as f: json.dump(paper_trading, f, indent=4)

paper_trading = load_data()
system_status = {"status": "HEALTHY", "details": ""}

# --- إدارة المخاطر (Risk Manager) ---
def get_risk_profile(current_prices):
    open_trades = paper_trading["open_trades"]
    unrealized_pnl = 0.0
    locked_margin = 0.0
    
    for trade in open_trades:
        symbol = trade['symbol']
        curr_p = current_prices.get(symbol)
        locked_margin += (trade['quantity'] * trade['entry_price']) / trade['leverage']
        
        if curr_p:
            direction = 1 if trade['side'] == 'BUY' else -1
            trade['pnl'] = round((curr_p - trade['entry_price']) * trade['quantity'] * direction, 2)
            unrealized_pnl += trade['pnl']

    equity = round(paper_trading["balance"] + unrealized_pnl, 2)
    free_margin = max(0, round(paper_trading["balance"] - locked_margin, 2))
    margin_level = round(equity / locked_margin, 2) if locked_margin > 0 else 999.0
    
    if equity > paper_trading["peak_equity"]: paper_trading["peak_equity"] = equity
    drawdown = round(((paper_trading["peak_equity"] - equity) / paper_trading["peak_equity"]) * 100, 2)

    risk_data = {"status": "NORMAL", "color": "#4CAF50", "can_trade": True}
    if margin_level < 1.1: risk_data.update({"status": "CRITICAL", "color": "#8B0000", "can_trade": False})
    elif margin_level < 1.3: risk_data.update({"status": "WARNING", "color": "#FF9800", "can_trade": False})
        
    return equity, margin_level, drawdown, free_margin, risk_data

# --- محرك الإغلاق والـ Engine ---
def close_trade(trade, exit_price, reason="MANUAL"):
    if trade['status'] != "OPEN": return
    margin = (trade['quantity'] * trade['entry_price']) / trade['leverage']
    paper_trading["balance"] += round(margin + trade['pnl'], 2)
    trade.update({"status": "CLOSED", "exit_price": exit_price, "closed_at": datetime.now().isoformat(), "reason": reason})
    paper_trading["history"].append(trade)
    paper_trading["open_trades"].remove(trade)
    print(f"✅ [CLOSED] {trade['symbol']} | PnL: {trade['pnl']}$ | Reason: {reason}")
    save_data()

def update_engine():
    with trade_lock:
        if not paper_trading["open_trades"]: return
        try:
            symbols = list(set([t['symbol'] for t in paper_trading["open_trades"]]))
            prices = {s: float(exchange.fetch_ticker(s.replace('/', ''))['last']) for s in symbols}
            for trade in paper_trading["open_trades"][:]:
                curr_p = prices.get(trade['symbol'])
                if not curr_p: continue
                dir = 1 if trade['side'] == 'BUY' else -1
                trade['pnl'] = round((curr_p - trade['entry_price']) * trade['quantity'] * dir, 2)
                
                is_sl = (dir == 1 and curr_p <= trade['sl']) or (dir == -1 and curr_p >= trade['sl']) if trade['sl'] else False
                is_tp = (dir == 1 and curr_p >= trade['tp']) or (dir == -1 and curr_p <= trade['tp']) if trade['tp'] else False
                is_liq = (dir == 1 and curr_p <= trade['liq']) or (dir == -1 and curr_p >= trade['liq'])
                
                if is_sl or is_tp or is_liq:
                    close_trade(trade, curr_p, "AUTO_EXIT")
            system_status.update({"status": "HEALTHY", "details": ""})
        except Exception as e: system_status.update({"status": "ERROR", "details": str(e)})

# --- المسارات (Endpoints) ---
@app.route('/status', methods=['GET'])
def status():
    try:
        symbols = list(set([t['symbol'] for t in paper_trading["open_trades"]] + ['BTC/USDT']))
        prices = {s: float(exchange.fetch_ticker(s.replace('/', ''))['last']) for s in symbols}
        equity, m_level, d_down, f_margin, risk = get_risk_profile(prices)
        win_rate = round((len([t for t in paper_trading["history"] if t.get('pnl', 0) > 0]) / len(paper_trading["history"])) * 100, 2) if paper_trading["history"] else 0.0
        return jsonify({"mode": TRADING_MODE, "price": prices.get('BTC/USDT'), "financials": {"equity": equity, "balance": round(paper_trading["balance"], 2), "free_margin": f_margin}, "risk": {**risk, "margin_level": m_level, "drawdown": f"{d_down}%"}, "system": system_status, "stats": {"win_rate": f"{win_rate}%", "open_trades": len(paper_trading["open_trades"])}})
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/trade', methods=['POST'])
def open_trade():
    with trade_lock:
        data = request.json
        symbol = data.get('symbol', 'BTC/USDT')
        if any(t['symbol'] == symbol for t in paper_trading["open_trades"]): return jsonify({"status": "error", "msg": "الصفقة مفتوحة بالفعل"}), 400
        try:
            # الحل: جلب أسعار كل العملات المفتوحة + الجديدة لفحص المخاطرة الشامل
            check_symbols = list(set([t['symbol'] for t in paper_trading["open_trades"]] + [symbol]))
            prices = {s: float(exchange.fetch_ticker(s.replace('/', ''))['last']) for s in check_symbols}
            curr_p = prices[symbol]
            _, _, _, _, risk = get_risk_profile(prices)
            
            if not risk['can_trade']: return jsonify({"status": "error", "msg": "المخاطرة عالية جداً"}), 403
            lev, qty = data.get('leverage', 10), data.get('quantity', 0.01)
            cost = (qty * curr_p) / lev
            if cost > paper_trading["balance"]: return jsonify({"status": "error", "msg": "الرصيد لا يكفي"}), 400

            new_t = {"id": str(uuid.uuid4())[:8], "symbol": symbol, "side": data.get('side'), "entry_price": curr_p, "quantity": qty, "leverage": lev, "sl": data.get('sl'), "tp": data.get('tp'), "liq": round(curr_p * (1 - ((1 if data.get('side') == 'BUY' else -1) * (1 / lev))), 2), "pnl": 0.0, "status": "OPEN", "timestamp": datetime.now().isoformat()}
            paper_trading["balance"] -= cost
            paper_trading["open_trades"].append(new_t)
            print(f"🚀 [OPENED] {symbol} | Side: {data.get('side')} | Cost: {cost}$") # تسجيل الفتح
            save_data(); return jsonify({"status": "success", "trade": new_t})
        except Exception as e: return jsonify({"status": "error", "details": str(e)}), 500

@app.route('/close', methods=['POST']) # مسار الإغلاق اليدوي الاختياري
def manual_close():
    trade_id = request.json.get('trade_id')
    with trade_lock:
        trade = next((t for t in paper_trading["open_trades"] if t['id'] == trade_id), None)
        if trade:
            curr_p = float(exchange.fetch_ticker(trade['symbol'].replace('/', ''))['last'])
            close_trade(trade, curr_p, "MANUAL")
            return jsonify({"status": "success"})
    return jsonify({"status": "error", "msg": "الصفقة غير موجودة"}), 404

scheduler = BackgroundScheduler(); scheduler.add_job(update_engine, 'interval', seconds=2); scheduler.start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
