from flask import Flask
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from config import Config
import threading

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# استدعاء المحركات (سنقوم ببرمجتها في الخطوة التالية)
# من المهم أن يكون الربط هنا لحظياً (إضافة 56)

@socketio.on('connect')
def handle_connect():
    print("Mobile Connected to Factory $ Engine")
    emit('system_status', {'status': 'SAFE', 'mode': Config.DEFAULT_MODE})

@socketio.on('emergency_stop')
def handle_emergency():
    # إضافة 53: مفتاح القطع الفوري
    print("EMERGENCY STOP TRIGGERED FROM MOBILE")
    # هنا سيتم استدعاء أمر إغلاق كافة الصفقات من engine_trade

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=Config.PORT)
