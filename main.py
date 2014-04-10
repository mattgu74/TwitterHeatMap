# -*- coding: utf8 -*-
from twython import TwythonStreamer
from config import CONF
from pprint import pprint
from flask import Flask, render_template
from flask.ext.socketio import SocketIO, emit, BaseNamespace
import gevent

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)



class MyStreamer(TwythonStreamer):
    def __init__(self, *args, **kwargs):
        TwythonStreamer.__init__(self, *args, **kwargs)

    def on_success(self, data):
        emit('tweet', data)

    def on_error(self, status_code, data):
        print status_code, data, "STOP MySTREAMER !!"
        self.disconnect()


@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect', namespace='/test')
def test_connect():
    stream = MyStreamer(CONF['APP_KEY'], CONF['APP_SECRET'],
                    CONF['OAUTH_TOKEN'], CONF['OAUTH_TOKEN_SECRET'])
    stream.statuses.filter(locations="-5,42.2,8.13,51")

@socketio.on('disconnect', namespace='/test')
def test_disconnect():
    print('Client disconnected')

if __name__ == '__main__':
    try:
        socketio.run(app, port=55555, host="0.0.0.0")
    except KeyboardInterrupt:
        pass
