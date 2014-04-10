# -*- coding: utf8 -*-
from gevent import monkey; monkey.patch_all()

from pprint import pprint

import gevent
from twython import TwythonStreamer
import flask
from flask import Flask, render_template, request, g, current_app
from flask.ext.socketio import SocketIO, emit, BaseNamespace
from werkzeug.local import LocalProxy

from config import CONF


app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)


class MyStreamer(TwythonStreamer):
    def __init__(self, *args, **kwargs):
        TwythonStreamer.__init__(self, *args, **kwargs)
        print('INIT '*10)
        self.queues = {}

    def on_success(self, data):
        for queues in self.queues.values():
            queues.put_nowait(data)

    def on_error(self, status_code, data):
        print status_code, data, "STOP MySTREAMER !!"
        self.disconnect()

    def get_queue(self, uid):
        return self.queues.setdefault(uid, gevent.queue.Queue())

    def delete_queue(self, uid):
        del self.queues[uid]


streamer = MyStreamer(CONF['APP_KEY'], CONF['APP_SECRET'],
                CONF['OAUTH_TOKEN'], CONF['OAUTH_TOKEN_SECRET'])
green = gevent.spawn(streamer.statuses.filter, locations="-5,42.2,8.13,51")


@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect', namespace='/test')
def test_connect():
    uid = request.namespace.socket.sessid
    print('Client %s connected' % uid)
    queue = streamer.get_queue(uid)
    while True:
        tweet = queue.get(timeout=60)
        emit('tweet', tweet)


@socketio.on('disconnect', namespace='/test')
def test_disconnect():
    uid = request.namespace.socket.sessid
    print('Client %s disconnected' % uid)
    streamer.delete_queue(uid)


if __name__ == '__main__':
    try:
        socketio.run(app, port=55555, host="0.0.0.0")
    except KeyboardInterrupt:
        pass
