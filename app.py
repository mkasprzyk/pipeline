from flask import Flask, Response, jsonify, render_template, request
from flask_restful import Resource, Api
from jenkinsapi.jenkins import Jenkins
from gevent.wsgi import WSGIServer
from gevent.queue import Queue
from gevent import monkey
monkey.patch_all()
import gevent
import json
import time
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

@app.route("/update")
def update():
    def notify():
        result = None
        if jenkins:
            jobs = jenkins.get_jobs()
            data = {}
            for name, job in jobs:
                try:
                    last_build = job.get_last_build()
                    is_good = last_build.is_good()
                except:
                    is_good = False
                data[name] = {
                    'is_running': job.is_running(),
                    'is_good': is_good}
            result = json.dumps(data)
        for sub in subscriptions[:]:
            sub.put(result)

    gevent.spawn(notify)
    return jsonify({'status': 200})


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

