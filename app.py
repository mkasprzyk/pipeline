from flask import Flask, Response, jsonify, render_template, request
from flask_restful import Resource, Api
from jenkinsapi.jenkins import Jenkins
from gevent.wsgi import WSGIServer
from gevent.queue import Queue
from gevent import monkey
monkey.patch_all()
import gevent
import tasks
import json
import os

from pipeline_parser import Pipeline, d3js_generator
from sse import ServerSentEvent


app = Flask(__name__)
api = Api(app)
subscriptions = []

try:
    jenkins = Jenkins(os.environ.get('JENKINS_URL'),
        username=os.environ.get('JENKINS_USERNAME'),
        password=os.environ.get('JENKINS_PASSWORD'))
except Exception as e:
    app.logger.error('Jenkins is unreachable')
    jenkins = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route("/events")
def events():
    app.logger.info('New subscriber: {}'.format(request.remote_addr))
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

@app.route("/call/<action>")
def call(action):
    handlers = {
        'get_jobs_status': tasks.get_jobs_status,
    }
    handler = handlers.get(action, None)
    if handler:
        app.logger.info('Spawn action: {}'.format(action))
        gevent.spawn(handler, subscriptions=subscriptions, jenkins=jenkins)
        status = 200
    else:
        app.logger.info('Unknown action: {}'.format(action))
        status = 404
    return jsonify({'status': status})


class Data(Resource):
    def get(self):
        stream = Queue()
        data = json.load(open('pipeline.json', encoding='utf-8'))
        pipeline = Pipeline(d3js_generator(stream)).start()
        pipeline.send(data.get('Steps'))
        return jsonify(stream.get())

api.add_resource(Data, '/pipeline')


if __name__ == '__main__':
    app.debug = True
    server = WSGIServer(("", 5000), app)
    server.serve_forever()

