# -*- coding: utf-8 -*-

def coroutine(fn):
    def wrapper(*args, **kwargs):
        result = fn(*args, **kwargs)
        next(result)
        return result
    return wrapper


class Pipeline(object):

    START = 'START'
    STOP = 'STOP'
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
                sections = (yield)
            except GeneratorExit:
                raise
            self.send(self.START, None, None)
            for steps in sections:
                if not [steps[token] for token in required_keys if steps[token]]:
                    self.send(self.EMPTY_STEP, None, None)
                for pk, (token, body) in enumerate(steps.items(), 1):
                    if token == self.ROS:
                        parse_steps(body)
                    if token == self.SNT or token == self.MNT:
                        multi(token, body, pk)
            self.send(self.STOP, None, None)


@coroutine
def d3js_generator(stream):
    CONTENTS = 'contents'
    pipeline = []
    threads = {}
    item = {}

    while True:
        content = (yield)
        event = content.get('event')
        body = content.get('body')

        if event == Pipeline.OPEN_BODY:
            #prepare container for threads
            threads[CONTENTS] = []
            threads['name'] = 'parallel'

        if event == Pipeline.OPEN_THREAD:
            item[CONTENTS] = []
            item["name"] = body

        if event == Pipeline.PARSE_JOB:
            if not item:
                pipeline.append({
                    'name': body['name']
                })
            else:
                item[CONTENTS].append({
                    'name': body['name']
                })

        if event == Pipeline.CLOSE_THREAD:
            if not threads:
                pipeline.append(item)
            else:
                threads[CONTENTS].append(item)
            item = {}

        if event == Pipeline.CLOSE_BODY:
            pipeline.append(threads)
            threads = {}

        if event == Pipeline.STOP:
            stream.put({'contents': pipeline, 'name': 'Root'})


if __name__ == '__main__':
    from queue import Queue
    import json

    stream = Queue()
    pipeline = Pipeline(d3js_generator(stream)).start()
    data = json.load(open('fixtures/data.json', encoding='utf-8'))

    pipeline.send(data)
    print(stream.get())
