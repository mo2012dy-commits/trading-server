import os
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/status', methods=['GET'])
def get_status():
    # بيانات تجريبية للتأكد من الربط
    return jsonify({
        "symbol": "BTC/USDT",
        "price": "73130.1",
        "rsi": "72.17",
        "balance": "901.34",
        "pnl": "54.5",
        "trades": "3",
        "alerts": [{"msg": "تنبيه: RSI مرتفع 🚨", "type": "SELL"}]
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
