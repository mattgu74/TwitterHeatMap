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
        self.queue = gevent.queue.Queue()

    def on_success(self, data):
        self.queue.put_nowait(data)
        if self.queue.qsize() > 10000:
            self.queue.get()

    def on_error(self, status_code, data):
        print status_code, data, "STOP MySTREAMER !!"
        self.disconnect()


class WatchDog:
    def __init__(self):
        self.init()

    def init(self):
        self.streamer = MyStreamer(CONF['APP_KEY'], CONF['APP_SECRET'],
                        CONF['OAUTH_TOKEN'], CONF['OAUTH_TOKEN_SECRET'])
        self.green = gevent.spawn(self.streamer.statuses.filter, track="korben,utc,innovation,innovations,startup,tech,technologie,html5,js,google,api,sdk,webdesign,design,web")

    def check_alive(self):
        if self.green.dead:
            self.streamer.disconnect()
            self.green.kill()
            # reload
            self.init()

dog = WatchDog()


@app.route('/')
def index():
    dog.check_alive()
    return render_template('index1.html')

@app.route('/2')
def index2():
    dog.check_alive()
    return render_template('index2.html')

@socketio.on('connect', namespace='/test')
def test_connect():
    dog.check_alive()
    uid = request.namespace.socket.sessid
    print('Client %s connected' % uid)
    while True:
        try:
            tweet = dog.streamer.queue.get(timeout=5)
        except gevent.queue.Empty:
            dog.check_alive()
        else:
            emit('tweet', tweet, broadcast=True)


@socketio.on('disconnect', namespace='/test')
def test_disconnect():
    dog.check_alive()
    uid = request.namespace.socket.sessid
    print('Client %s disconnected' % uid)


if __name__ == '__main__':
    try:
        socketio.run(app, port=55555, host="0.0.0.0")
    except KeyboardInterrupt:
        pass
