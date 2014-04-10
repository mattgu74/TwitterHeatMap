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


class WatchDog:
    def __init__(self):
        self.init()

    def init(self):
        self.streamer = MyStreamer(CONF['APP_KEY'], CONF['APP_SECRET'],
                        CONF['OAUTH_TOKEN'], CONF['OAUTH_TOKEN_SECRET'])
        self.green = gevent.spawn(self.streamer.statuses.filter, locations="-5,42.2,8.13,51")

    def check_alive(self):
        if self.green.dead:
            self.streamer.disconnect()
            self.green.kill()
            # save queeus
            queues = self.streamer.queues
            # reload
            self.init()
            # restor queues
            self.streamer.queues = queues

dog = WatchDog()


@app.route('/')
def index():
    dog.check_alive()
    return render_template('index.html')

@socketio.on('connect', namespace='/test')
def test_connect():
    dog.check_alive()
    uid = request.namespace.socket.sessid
    print('Client %s connected' % uid)
    queue = dog.streamer.get_queue(uid)
    while True:
        try:
            tweet = queue.get(timeout=5)
        except gevent.queue.Empty:
            dog.check_alive()
        else:
            emit('tweet', tweet)


@socketio.on('disconnect', namespace='/test')
def test_disconnect():
    dog.check_alive()
    uid = request.namespace.socket.sessid
    print('Client %s disconnected' % uid)
    dog.streamer.delete_queue(uid)


if __name__ == '__main__':
    try:
        socketio.run(app, port=55555, host="0.0.0.0")
    except KeyboardInterrupt:
        pass
