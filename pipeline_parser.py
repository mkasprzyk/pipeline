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
    PARSE_STEPS = 'PARSE_STEPS'

    ROS = 'RunOnStart'
    SNT = 'SingleNameThreads'
    MNT = 'MultipleNamesThreads'

    def send(self, stream, event, body, pk):
        stream.send({'event': event, 'body': body, 'pk': pk})

    @coroutine
    def parse_steps(self, stream):
        while True:
            tasks = (yield)
            print(tasks)
            

    @coroutine
    def pipeline_parser(self, stream):

        required_keys = [self.ROS, self.SNT, self.MNT]

        def multi(stream, steps, body, pk): 
            if len(steps[token]) > 1:
                self.send(stream, self.PARALLEL, body, pk)
                self.send(stream, self.OPEN_BODY, body, pk)
            for thread in steps[token]:
                if steps[token][thread]:
                    self.send(stream, self.PARSE_STEPS, steps[token][thread], pk)
            if len(steps[token]) > 1:
                self.send(stream, self.CLOSE_BODY, body, pk)
        
        while True:
            try:
                steps = (yield)
            except GeneratorExit:
                raise
            if not [steps[token] for token in required_keys if steps[token]]:
                self.send(stream, self.EMPTY_STEP, None, None)
            for pk, (key, value) in enumerate(steps.items(), 1):
                if key == self.ROS:
                    self.send(stream, key, value, pk)
                if key == self.SNT or key == self.MNT:
                    multi(stream, steps, key, pk)


@coroutine
def printer():
  while True:
    stuff = (yield)
    #print stuff

pp = PipelineParser()

parser = pp.pipeline_parser(pp.parse_steps(printer()))

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
