from itertools import chain
import json

def coroutine(fn):
    def wrapper(*args, **kwargs):
        result = fn(*args, **kwargs)
        next(result)
        return result
    return wrapper


class Pipeline(object):

    PARALLEL = 'PARALLEL'
    OPEN_BODY = 'OPEN_BODY'
    CLOSE_BODY = 'CLOSE_BODY'
    OPEN_CALL = 'OPEN_CALL'
    CLOSE_CALL = 'CLOSE_CALL'
    EMPTY_STEP = 'EMPTY_STEP'
    PARSE_STEPS = 'PARSE_STEPS'
    PARSE_JOB = 'PARSE_JOB'
    PARSE_INPUT = 'PARSE_INPUT'
    OPEN_THREAD = 'OPEN_THREAD'
    CLOSE_THREAD = 'CLOSE_THREAD'
    
    ROS = 'RunOnStart'
    SNT = 'SingleNameThreads'
    MNT = 'MultipleNamesThreads'

    def send(self, stream, event, body, pk, **kwargs):
        stream.send({'event': event, 'body': body, 'pk': pk})

    @coroutine
    def parser(self, stream):

        required_keys = [self.ROS, self.SNT, self.MNT]

        def parse_steps(stream, tasks):
            self.send(stream, self.OPEN_CALL, None, None)
            for task in tasks:
                if task['type'] == 'job':
                    self.send(stream, self.PARSE_JOB, task, None)
                if task['type'] == 'input':
                    self.send(stream, self.PARSE_INPUT, task, None)
            self.send(stream, self.CLOSE_CALL, None, None)

        def multi(stream, token, body, pk): 
            if len(steps[token]) > 1:
                self.send(stream, self.PARALLEL, token, pk)
                self.send(stream, self.OPEN_BODY, token, pk)
            for thread in steps[token]:
                if steps[token][thread]:
                    body = steps[token][thread]
                    self.send(stream, self.OPEN_THREAD, thread, pk)
                    self.send(stream, self.PARSE_STEPS, body, pk)
                    parse_steps(stream, body)
                    self.send(stream, self.CLOSE_THREAD, thread, pk)
            if len(steps[token]) > 1:
                self.send(stream, self.CLOSE_BODY, token, pk)
        
        while True:
            try:
                steps = (yield)
            except GeneratorExit:
                raise
            if not [steps[token] for token in required_keys if steps[token]]:
                self.send(stream, self.EMPTY_STEP, None, None)
            for pk, (token, body) in enumerate(steps.items(), 1):
                if token == self.ROS:
                    self.send(stream, token, body, pk)
                if token == self.SNT or token == self.MNT:
                    multi(stream, token, body, pk)


@coroutine
def d3js_generator():
    pipeline = []
    wc = {}
    while True:
        content = (yield)
        event = content.get('event')
        body = content.get('body')

        if event == Pipeline.OPEN_THREAD:
            wc["contents"] = []
            wc["name"] = body

        if event == Pipeline.PARSE_JOB:
            wc["contents"].append({
                'name': body['name']
            })

        if event == Pipeline.CLOSE_THREAD:
            pipeline.append(wc)

        if event == Pipeline.CLOSE_BODY:
            print(json.dumps({'contents': pipeline}))




if __name__ == '__main__':

    pipeline = Pipeline()
    parser = pipeline.parser(d3js_generator())

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
