from flask import Flask, Response, jsonify, render_template, request
from werkzeug.contrib.cache import SimpleCache
from gevent import monkey; monkey.patch_all()
from gevent.wsgi import WSGIServer
from gevent.queue import Queue
from uuid import uuid4
import gevent
import tasks
import json

from pipeline_parser import Pipeline, d3js_generator, jobs_generator
from sse import ServerSentEvent

app = Flask(__name__)
cache = SimpleCache()
subscriptions = {}


def configuration(stream, generator):
    data = json.load(open('pipeline.json', encoding='utf-8'))
    if generator == 'pipeline':
        handler = d3js_generator(stream)
    if generator == 'jobs':
        handler = jobs_generator(stream)
    pipeline = Pipeline(handler).start()
    pipeline.send(data.get('Steps'))

@app.route('/')
def index():
    return render_template('index.html')

@app.route("/events")
def events():
    pk = str(uuid4())
    app.logger.info('New subscriber: {}, channel: {}'.format(request.remote_addr, pk))
    def gen():
        queue = Queue()
        subscriptions[pk] = queue
        subscriptions[pk].put(json.dumps({'__channel__': pk}))
        try:
            while True:
                result = queue.get()
                event = ServerSentEvent(str(result))
                yield event.encode()
        except GeneratorExit:
            del(subscriptions[pk])

    return Response(gen(), mimetype="text/event-stream")

@app.route("/call/<action>/<channel>")
def call(action, channel):
    stream = Queue()
    configuration(stream, 'jobs')
    jobs = stream.get()
    handlers = {
        'get_jobs_status': tasks.get_jobs_status,
    }
    handler = handlers.get(action, None)
    if handler:
        app.logger.info('Spawn action: {}'.format(action))
        gevent.spawn(handler, subscriptions,
                     cache=cache,
                     channel=channel,
                     jobs=jobs)
        status = 200
    else:
        app.logger.info('Unknown action: {}'.format(action))
        status = 404
    return jsonify({'status': status})


@app.route("/api/<generator>")
def data(generator):
    stream = Queue()
    configuration(stream, generator)
    return jsonify(stream.get())


if __name__ == '__main__':
    app.debug = True
    server = WSGIServer(("", 5000), app)
    server.serve_forever()
