from flask import Flask, Response, jsonify, render_template, request
from flask_restful import Resource, Api
from pipeline_parser import Pipeline, d3js_generator
from jenkinsapi.jenkins import Jenkins
from gevent.wsgi import WSGIServer
from gevent.queue import Queue
from sse import ServerSentEvent
import gevent
import json
import time
import os


app = Flask(__name__)
api = Api(app)
subscriptions = []

try:
    jenkins = Jenkins(os.environ.get('JENKINS_URL'),
        username=os.environ.get('JENKINS_USERNAME'),
        password=os.environ.get('JENKINS_PASSWORD'))
except Exception as e:
    jenkins = None

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
        result = None
        if jenkins:
            request = jenkins.get_jobs()
            result = {name: job.is_running() for name, job in request}
        for sub in subscriptions[:]:
            sub.put(result)
    gevent.spawn(notify)
    return "OK"

class Data(Resource):
    def get(self):
        data = json.load(open('fixtures/data.json'))

        stream = Queue()
        pipeline = Pipeline(d3js_generator(stream)).start()
        pipeline.send(data)
        return jsonify(stream.get())

api.add_resource(Data, '/pipeline')

if __name__ == '__main__':
    app.debug = True
    server = WSGIServer(("", 5000), app)
    server.serve_forever()

