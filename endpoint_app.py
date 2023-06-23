'''
This implements the endpoint node. It uses a Flask server listenening on 80 http.
1. on PUT:
    a. it stores the request in a db, (now a queue)
    b. calls a free worker
    c. returns 200:id to client
2. on pullCompleted:
    a. it gets the ids of the latest k items


- Sync with the other node

it also handles a pool of workers somehow TODO
'''
from datetime import datetime, timedelta
from flask import *
import requests
from urllib.request import urlopen, Request
import hashlib
from uuid import uuid4 as uuid
import json
import base64

import time
import atexit

from apscheduler.schedulers.background import BackgroundScheduler


app = Flask(__name__)

jobs_queue = []
jobs_completed= []

num_workers = 0
maxNumOfWorkers = 0


#TODO - assign value to other
other_endpoint = ''

# class Worker:
@app.before_request
def limit_requests():
    '''TODO: implement internal logic
    '''
    pass


@app.route('/jobs/updateResult', methods=['PUT'])
def update_result():
    '''
    Update result from worker
    '''
    req = json.loads(request.data)
    jobs_completed.append({'id': req['id'], 'value': req['value']})
    return "thanks"



@app.route('/jobs/getJob', methods=['GET'])
def get_job():
    '''
    Get job for worker
    '''
    if not jobs_queue:
        return 'No jobs available', 400
    return jobs_queue.pop(0)

@app.route('/enqueue', methods=['PUT'])
def enqueue_job():
    '''
    enqueues new requests
    '''
    buffer = request.get_data().decode('utf-8')
    iterations =  request.args.get('iterations')
    if not iterations.isdigit():
        return 'Bad Input', 400
    iterations = int(iterations)
    id = str(uuid())
    jobs_queue.append({'id': id, 'iterations': iterations, 'data': buffer, 'time': datetime.now()})

    # TODO make sure there are enough workers
    # return to client
    return id

@app.route('/jobs/pullCompleted', methods=['POST'])
def internal_get_completed_jobs():
    k = request.args.get('top')
    if not k.isdigit():
        return "Bad Input", 400
    
    return jobs_completed[-int(k):]
 

@app.route('/pullCompleted', methods=['POST'])
def get_completed_jobs():
    k = request.args.get('top')
    if not k.isdigit():
        return "Bad Input", 400
    k = int(k)
    top_k_jobs = jobs_completed[-int(k):]
    if top_k_jobs:
        return top_k_jobs
    # get other top k jobs
    if other_endpoint:
        try:
            response = requests.post(f'http://{other_endpoint}/jobs/pullCompleted?top={k}', headers={'Connection':'close'})
            if response.status_code == 200:
                return response.content
            return []
        except:
            return []
    return []

@app.route('/jobs/getQuota', methods=['GET'])
def try_get_node_quota():
    global maxNumOfWorkers
    if num_workers < maxNumOfWorkers:
        maxNumOfWorkers -= 1
        return {'possible': True}
    return {'possible': False}

def spawn_worker():
    pass

def check_workers_state():
    # no jobs no cry
    if len(jobs_queue) == 0:
        return
    
    first_job_time = datetime.strptime(jobs_queue[0], "%Y-%m-%d %H:%M:%S.%f")
    if datetime.now - first_job_time > timedelta(seconds=15):
        if num_workers < maxNumOfWorkers:
            spawn_worker()
        else:
            try:
                response = requests.get(f'http://{other_endpoint}/jobs/getQuota', headers={'Connection':'close'})
                if response.status_code == 200 and response.json()['possible'] == True:
                    maxNumOfWorkers+=1
                    spawn_worker()
            except:
                pass



if __name__ == '__main__':
    from argparse import ArgumentParser
    parser = ArgumentParser(description='Hash calculating EC2 endpoint flask server')
    parser.add_argument('--port', dest='port', type=int, default=8000, help='local port')
    parser.add_argument('--other', dest='other', help='other with port')
    parser.add_argument('--max-num', dest='max_num',type=int, default=3, help='max num of workers')
    args = parser.parse_args()
    other_endpoint = args.other
    maxNumOfWorkers = args.max_num

    # set background timer

    scheduler = BackgroundScheduler()
    scheduler.add_job(func=check_workers_state, trigger="interval", seconds=60)
    scheduler.start()

    # Shut down the scheduler when exiting the app
    atexit.register(lambda: scheduler.shutdown())


    app.run('0.0.0.0', port=args.port)