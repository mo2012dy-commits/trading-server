from flask import Flask, jsonify, request
from flask_cors import CORS
import os
from binance.client import Client

app = Flask(__name__)
CORS(app)

# جلب المفاتيح من بيئة العمل (Railway)
API_KEY = os.getenv('BINANCE_API_KEY')
API_SECRET = os.getenv('BINANCE_SECRET_KEY')

@app.route('/account', methods=['GET'])
def get_account():
    try:
        # الربط الفعلي مع بينانس
        client = Client(API_KEY, API_SECRET)
        
        # جلب بيانات الحساب (Futures)
        acc = client.futures_account()
        
        return jsonify({
            "status": "success",
            "account": {
                "balance": float(acc['totalWalletBalance']),
                "available": float(acc['availableBalance']),
                "pnl": float(acc['totalUnrealizedProfit']),
                "pnlPct": (float(acc['totalUnrealizedProfit']) / float(acc['totalWalletBalance']) * 100) if float(acc['totalWalletBalance']) > 0 else 0
            }
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    # مهم لـ Railway عشان يعرف المنفذ الصحيح
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
