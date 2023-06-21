'''
This implements the endpoint node. It uses a Flask server listenening on 80 http.
1. on PUT:
    a. it stores the request in a db, (now a queue)
    b. calls a free worker
    c. returns 200:id to client
2. on pullCompleted:
    a. it gets the ids of the latest k items

it also handles a pool of workers somehow TODO
'''
from flask import *
import hashlib
from uuid import uuid4 as uuid
import json
import base64

app = Flask(__name__)

jobs_queue = []
jobs_completed= []


# class Worker:

#     def work(self):
#         job = jobs_queue.pop()
#         is_busy = True
#         final_hash_value = self.__do_work(job['data'], job['iterations'])
#         jobs_completed.append({'id': job['id'], 'value': final_hash_value})
    

#     def __do_work(self, buffer, iterations):
#         output = hashlib.sha512(buffer).digest()
#         for i in range(iterations - 1):
#             output = hashlib.sha512(output).digest()
#         return output       
def get_work():
    job = jobs_queue.pop()
    final_hash_value = work(job['data'], job['iterations'])
    jobs_completed.append({'id': job['id'], 'value': final_hash_value})
    
    
def work(buffer, iterations):
    ''' temp function '''
    output = hashlib.sha512(buffer).digest()
    for i in range(iterations - 1):
        output = hashlib.sha512(output).digest()
    return str(base64.b64encode(output))

@app.route('/enqueue', methods=['PUT'])
def enqueue():
    '''
    enqueues new requests
    '''
    buffer = request.get_data()
    iterations =  request.args.get('iterations')
    if not iterations.isdigit():
        return 'Bad Input', 400
    iterations = int(iterations)
    id = str(uuid())
    jobs_queue.append({'id': id, 'iterations': iterations, 'data': buffer})
    # TODO later add to dynamodb

    #call a worker
    get_work()
    # return to client
    return id

@app.route('/pullCompleted', methods=['POST'])
def pull_completed():
    k = request.args.get('top')
    if not k.isdigit():
        return "Bad Input", 400
    
    k = int(k)
    if k > len(jobs_completed):
        k = len(jobs_completed)

    top_k_jobs = jobs_completed[-int(k):]
    # import pdb;pdb.set_trace()
    return json.dumps(top_k_jobs)


if __name__ == '__main__':
    app.run('0.0.0.0', port=80)