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


def get_jobs_status(subscriptions):
    def get_single_status(name, job):
        try:
            last_build = job.get_last_build()
            is_good = last_build.is_good()
        except:
            is_good = False
        for sub in subscriptions[:]:
            sub.put(
                json.dumps({
                    name: {
                        'is_running': job.is_running(),
                        'is_good': is_good
                    }
                })
            )

    jobs = jenkins.get_jobs()
    for name, job in jobs:
        gevent.spawn(get_single_status, name, job)
