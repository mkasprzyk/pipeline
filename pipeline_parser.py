def coroutine(fn):
    def wrapper(*args, **kwargs):
        result = fn(*args, **kwargs)
        next(result)
        return result
    return wrapper



class PipelineParser(object):

    PARALLEL = 'PARALLEL'
    OPEN_BODY = 'OPEN_BODY'
    CLOSE_BODY = 'CLOSE_BODY'
    EMPTY_STEP = 'EMPTY_STEP'

    @coroutine
    def pipeline_parser(self, stream):

        ROS = 'RunOnStart'
        SNT = 'SingleNameThreads'
        MNT = 'MultipleNamesThreads'
        required_keys = [ROS, SNT, MNT]

        def send(event, body, pk):
            stream.send({event: body, 'pk': pk})

        def multi(steps, token, pk): 
            if len(steps[token]) > 1:
                send(token, self.PARALLEL, pk)
                send(token, self.OPEN_BODY, pk)
            for thread in steps[token]:
                if steps[token][thread]:
                    send(token, steps[token][thread], pk)
            if len(steps[token]) > 1:
                send(token, self.CLOSE_BODY, pk)
        
        while True:
            while True:
                try:
                    steps = (yield)
                except GeneratorExit:
                    raise
                if not [steps[token] for token in required_keys if steps[token]]:
                    send(None, self.EMPTY_STEP)
                for pk, (key, value) in enumerate(steps.items(), 1):
                    if key == ROS:
                        send(ROS, value, pk)
                    if key == SNT:
                        multi(steps, SNT, pk)
                    if key == MNT:
                        multi(steps, MNT, pk)


@coroutine
def printer():
  while True:
    stuff = (yield)
    print stuff


parser = PipelineParser().pipeline_parser(printer())

if __name__ == '__main__':

    data = {
        'RunOnStart': [
            {
                'type': 'job', 
                'name': 'Test'
            }],
        
        'SingleNameThreads': {},

        'MultipleNamesThreads': {
            'TEST1': [
                {
                    'type': 'job',
                    'name': 'JOB1_1'
                },
                {
                    'type': 'job',
                    'name': 'JOB1_2'
                }
            ],
            'TEST2': [
                {
                    'type': 'job',
                    'name': 'JOB2_1'
                },
                {
                    'type': 'job',
                    'name': 'JOB2_2'
                }
            ],
        }
    }

    parser.send(data)
