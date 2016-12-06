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
    

    def __init__(self, stream):
        self.stream = stream

    def send(self, event, body, pk, **kwargs):
        self.stream.send({'event': event, 'body': body, 'pk': pk})

    @coroutine
    def start(self):

        required_keys = [self.ROS, self.SNT, self.MNT]

        def parse_steps(tasks):
            self.send(self.OPEN_CALL, None, None)
            for task in tasks:
                if task['type'] == 'job':
                    self.send(self.PARSE_JOB, task, None)
                if task['type'] == 'input':
                    self.send(self.PARSE_INPUT, task, None)
            self.send(self.CLOSE_CALL, None, None)

        def multi(token, body, pk): 
            if len(steps[token]) > 1:
                self.send(self.PARALLEL, token, pk)
                self.send(self.OPEN_BODY, token, pk)
            for thread in steps[token]:
                if steps[token][thread]:
                    body = steps[token][thread]
                    self.send(self.OPEN_THREAD, thread, pk)
                    self.send(self.PARSE_STEPS, body, pk)
                    parse_steps(body)
                    self.send(self.CLOSE_THREAD, thread, pk)
            if len(steps[token]) > 1:
                self.send(self.CLOSE_BODY, token, pk)
        
        while True:
            try:
                steps = (yield)
            except GeneratorExit:
                raise
            if not [steps[token] for token in required_keys if steps[token]]:
                self.send(self.EMPTY_STEP, None, None)
            for pk, (token, body) in enumerate(steps.items(), 1):
                if token == self.ROS:
                    #TODO
                    pass
                if token == self.SNT or token == self.MNT:
                    multi(token, body, pk)


@coroutine
def d3js_generator():
    pipeline = []
    item = {}
    while True:
        content = (yield)
        event = content.get('event')
        body = content.get('body')

        if event == Pipeline.OPEN_THREAD:
            item["contents"] = []
            item["name"] = body

        if event == Pipeline.PARSE_JOB:
            item["contents"].append({
                'name': body['name']
            })

        if event == Pipeline.CLOSE_THREAD:
            pipeline.append(item)
            item = {}

        if event == Pipeline.CLOSE_BODY:
            print(json.dumps({'contents': pipeline, 'name': 'Root'}))




if __name__ == '__main__':

    pipeline = Pipeline(d3js_generator())
    parser = pipeline.start()

    data = {
        'RunOnStart': [
            {
                'type': 'job', 
                'name': 'Test1'
            },
            {
                'type': 'job', 
                'name': 'Test2'
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
                },
            ],
        }
    }

    parser.send(data)
