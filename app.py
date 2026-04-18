from flask import Flask, jsonify
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import threading

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# مسار لجلب الحساب بنظام الـ REST القديم عشان نضمن الشغل
@app.route('/account', methods=['GET'])
def get_account():
    # هنا بنحط رصيد وهمي مؤقتاً للتأكد من الربط، ثم نربطه بمحرك بينانس
    return jsonify({
        "status": "success",
        "account": {
            "balance": 15450.75,  # جرب تحط رقم مميز عشان تعرف انه اشتغل
            "pnl": 125.5,
            "available": 15000.00
        }
    })

@socketio.on('connect')
def handle_connect():
    print("Mobile Connected!")
    emit('system_status', {'status': 'SAFE'})

# كود الاستجابة لطلب الرصيد عبر السوكيت
@socketio.on('get_account_data')
def handle_account_request():
    emit('account_data', {
        "balance": 15450.75,
        "pnl": 125.5
    })

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
