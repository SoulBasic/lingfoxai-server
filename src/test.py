from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit

app = Flask(__name__,
            static_folder='../www',
            template_folder="../www",
            static_url_path="")
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode=None)

@app.route('/')
def index():
    return render_template('index.html')

    emit('my_pong')


@socketio.event
def connect():
    print("connected")
    emit('my_response', {'data': 'Connected', 'count': 0})


@socketio.on('disconnect')
def test_disconnect():
    print('Client disconnected', request.sid)


if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", port=80, allow_unsafe_werkzeug=True)