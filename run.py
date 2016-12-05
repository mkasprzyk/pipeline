from flask import Flask, jsonify, render_template, request
from flask_restful import Resource, Api
from utils import make_celery
import json

app = Flask(__name__)
api = Api(app)
app.config.update(
    CELERY_BROKER_URL='redis://localhost:6379',
    CELERY_RESULT_BACKEND='redis://localhost:6379'
)
celery = make_celery(app)


@app.route('/')
def index():
    result = update_status.delay()
    return render_template('index.html')

@celery.task
def update_status():
    return True

class Pipeline(Resource):
    def get(self):
        with open('static/data/fixture.json') as data:
            return json.load(data)

api.add_resource(Pipeline, '/pipeline')

if __name__ == '__main__':
    app.run()

