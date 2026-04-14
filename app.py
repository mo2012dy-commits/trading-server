import os
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # للسماح للجوال بالاتصال بالسيرفر بدون قيود

@app.route('/status', methods=['GET'])
def get_status():
    # البيانات الحقيقية التي ستظهر في تطبيقك "مصنع $"
    data = {
        "symbol": "BTC/USDT",
        "price": "73130.1",
        "rsi": "72.17",
        "balance": "901.34",
        "pnl": "54.5",
        "trades": "3",
        "alerts": [
            {
                "msg": "تنبيه: RSI مرتفع (منطقة بيع) 🚨",
                "type": "SELL"
            }
        ]
    }
    return jsonify(data)

if __name__ == '__main__':
    # الحصول على المنفذ (Port) من Railway تلقائياً
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
