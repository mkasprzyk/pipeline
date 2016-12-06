from flask import Flask, Response, jsonify, render_template, request
from flask_restful import Resource, Api
from gevent.wsgi import WSGIServer
from gevent.queue import Queue
from sse import ServerSentEvent
import grequests
import gevent
import json
import time

app = Flask(__name__)
api = Api(app)
subscriptions = []


@app.route('/')
def index():
    return render_template('index.html')

@app.route("/events")
def events():
    def gen():
        queue = Queue()
        subscriptions.append(queue)
        try:
            while True:
                result = queue.get()
                event = ServerSentEvent(str(result))
                yield event.encode()
        except GeneratorExit:
            subscriptions.remove(queue)
    return Response(gen(), mimetype="text/event-stream")

@app.route("/update")
def publish():
    def notify():
        URLS = ['http://google.pl']
        requests = (grequests.get(u) for u in URLS)
        responses = grequests.map(requests)
        for sub in subscriptions[:]:
            sub.put([r.status_code for r in responses])
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

