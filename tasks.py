import json

def get_jobs_status(subscriptions, jenkins):
    jobs = jenkins.get_jobs()
    for name, job in jobs:
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