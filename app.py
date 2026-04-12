import os
from flask import Flask, jsonify, request
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

# مفاتيح API من Render
API_KEY = os.getenv("BINANCE_API_KEY")
SECRET_KEY = os.getenv("BINANCE_SECRET_KEY")

# هيدرز لمحاكاة متصفح حقيقي وتجنب الحظر
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "message": "Trading Bot Server is running",
        "project": "Massnaa $"
    })

@app.route('/api/price', methods=['GET'])
def get_price():
    symbol = request.args.get('symbol', 'BTCUSDT').upper()
    try:
        # استخدام رابط الـ API المباشر مع الهيدرز
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
        response = requests.get(url, headers=HEADERS, timeout=10)
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({
                "error": "Binance rejected request",
                "code": response.status_code,
                "detail": response.text
            }), response.status_code
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
