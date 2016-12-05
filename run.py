from flask import Flask, jsonify, render_template, request
from redis import Redis
from utils import make_celery

app = Flask(__name__)
app.config.update(
    CELERY_BROKER_URL='redis://localhost:6379',
    CELERY_RESULT_BACKEND='redis://localhost:6379'
)
celery = make_celery(app)

@celery.task
def update_status():
    return True

@app.route('/')
def index():
    result = update_status.delay()
    return render_template('index.html')

if __name__ == '__main__':
    app.run()

