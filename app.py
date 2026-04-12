import os
from flask import Flask, jsonify, request
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

API_KEY = os.getenv("BINANCE_API_KEY")
SECRET_KEY = os.getenv("BINANCE_SECRET_KEY")

@app.route('/')
def home():
    return jsonify({"status": "online", "message": "Trading Bot Server is running"})

@app.route('/api/price', methods=['GET'])
def get_price():
    symbol = request.args.get('symbol', 'BTCUSDT')
    try:
        url = f"[https://api.binance.com/api/v3/ticker/price?symbol=](https://api.binance.com/api/v3/ticker/price?symbol=){symbol}"
        response = requests.get(url)
        data = response.json()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
