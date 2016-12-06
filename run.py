from flask import Flask, Response, jsonify, render_template, request
from flask_restful import Resource, Api
from gevent.wsgi import WSGIServer
from gevent.queue import Queue
from sse import ServerSentEvent
import gevent
import json
import time

app = Flask(__name__)
api = Api(app)
subscriptions = []

@app.route('/')
def index():
    return render_template('index.html')

@app.route("/subscribe")
def subscribe():
    def gen():
        q = Queue()
        subscriptions.append(q)
        try:
            while True:
                result = q.get()
                ev = ServerSentEvent(str(result))
                yield ev.encode()
        except GeneratorExit:
            subscriptions.remove(q)
    return Response(gen(), mimetype="text/event-stream")

@app.route("/tasks")
def tasks():
    return Response("Tasks: {}".format(len(subscriptions)))

@app.route("/update")
def publish():
    def notify():
        msg = str(time.time())
        for sub in subscriptions[:]:
            sub.put(msg)
    gevent.spawn(notify)
    return "OK"

class Pipeline(Resource):
    def get(self):
        with open('static/data/fixture.json') as data:
            return json.load(data)


api.add_resource(Pipeline, '/pipeline')

if __name__ == '__main__':
    app.debug = True
    server = WSGIServer(("", 5000), app)
    server.serve_forever()

