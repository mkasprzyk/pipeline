from werkzeug.contrib.cache import SimpleCache
from jenkinsapi.jenkins import Jenkins
import gevent
import json
import os


try:
    jenkins = Jenkins(os.environ.get('JENKINS_URL'),
        username=os.environ.get('JENKINS_USERNAME'),
        password=os.environ.get('JENKINS_PASSWORD'))
except Exception as e:
    #app.logger.error('Jenkins is unreachable')
    jenkins = None


def get_jobs_status(subscriptions, cache=None, channel=None):
    def publish(content, channel=None):
        if channel:
            sub = subscriptions.get(channel)
            sub.put(json.dumps(content))
        else:
            for _, sub in subscriptions.items():
                sub.put(json.dumps(content))

    def get_single_status(name, job, channel=channel):
        try:
            last_build = job.get_last_build()
            is_good = last_build.is_good()
        except:
            is_good = False
        status = {name: {
            'is_running': job.is_running(),
            'is_good': is_good,
            'channel': 'all'}}
        cache.set(name, status, timeout=0)
        publish(status, channel=channel)

    jobs = jenkins.get_jobs()
    for name, job in jobs:
        if cache.has(name):
            #if exist in cache, send only to channel
            content = cache.get(name)
            content[name]['channel'] = channel
            publish(content, channel=channel)
        else:
            get_single_status(name, job, channel=channel)
