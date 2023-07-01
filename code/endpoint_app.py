'''
This implements the endpoint node. It uses a Flask server listenening on 80 http.
1. on PUT:
    a. it stores the request in a db, (now a queue)
    b. calls a free worker
    c. returns 200:id to client
2. on pullCompleted:
    a. it gets the ids of the latest k items


- Sync with the other node

'''
from datetime import datetime, timedelta
from flask import *
import requests
from uuid import uuid4 as uuid
import json
import atexit
import boto3
import paramiko

from apscheduler.schedulers.background import BackgroundScheduler

#TODO: REMOVE!
import os
import signal
import subprocess


app = Flask(__name__)

jobs_queue = []
jobs_completed= []

maxNumOfWorkers = 0

other_endpoint = ''
is_test = False


class WorkerManager:
    def __init__(self, parent, other, is_test=False, config=None):
        if config is None:
            with open(r'config.json', 'r') as f:
                config = json.load(f)
        self.config = config
        self.parent = parent
        self.other = other
        self.is_test = is_test
        self.workers = {}

    def num_workers(self):
        return len(self.workers)
    
    def spawn_subprocess(self):
        #start a subprocess of worker
        # start subprocess and get pid
        # store pid in dict
        pro = subprocess.Popen(f'python3 code/worker.py --parent localhost:8000 --other localhost:8001 --instance-id 123  > worker.log', stdout=subprocess.PIPE, 
                                shell=True) 
        app.logger.info(f"Spawning a worker subprocess, pid={pro.pid}")
        self.workers[pro.pid] = pro
        return True
    
    def spawn_ec2_instance(self):
        try:
            app.logger.info('Spawning a new instance')
            ec2 = boto3.resource('ec2')
            instance_params = {
                    # 'ImageId': 'ami-042e8287309f5df03',  # Ubuntu 20.04 LTS 64-bit image
                    'ImageId': 'ami-09420243907777c4a',  # Ubuntu 22.10 LTS 64-bit image
                    'InstanceType': 't2.micro',
                    'KeyName': self.config['key_name'],  # Replace with your key pair name
                    'MinCount': 1,
                    'MaxCount': 1,
                    'SecurityGroupIds': [self.config['sec_grp']]
                    }

            instance = ec2.create_instances(**instance_params)[0]
            instance.wait_until_running()
            instance.load()
            app.logger.info(f"Instance created - {instance.instance_id} @ {instance.public_ip_address}")
        except:
            app.logger.error("ERROR: Creating an instance failed!")
            return False

        self.workers[instance.instance_id] = instance
        ssh = paramiko.SSHClient()
        try:
            app.logger.info(f'Connecting via SSH to {instance.public_ip_address}...')
            with open(f"{self.config['key_name']}.pem") as f:
                key = paramiko.RSAKey.from_private_key(f)
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(instance.public_ip_address, username='ubuntu', pkey=key)
            app.logger.info('Connected!')
        except:
            app.logger.error(f'Connecting via SSH failed!')
            return False
        
        try:
            # Copy the setup.sh script to the instance
            local_script, remote_script = 'worker_setup.sh', '/home/ubuntu/worker_setup.sh'
            local_worker_code, remote_worker_code = 'worker.py', '/home/ubuntu/worker.py'
            sftp_client = ssh.open_sftp()
            app.logger.info(f'Copying {local_script}')
            sftp_client.put(local_script, remote_script)
            app.logger.info(f'Copying {local_worker_code}')
            sftp_client.put(local_worker_code, remote_worker_code)
            sftp_client.close()
        except:
            app.logger.error('Establishing SFTP session failed')
            return False
        
        app.logger.info(f'Running {remote_script}')
        # Run the setup.sh script on the instance
        stdin, stdout, stderr = ssh.exec_command(f'chmod +x {remote_script} && {remote_script}')
        exit_status = stdout.channel.recv_exit_status()
        if exit_status != 0:
            app.logger.error(f'worker setup has failed! {stderr.read()}')
        app.logger.info('===== SETUP IS DONE! =====\n')
        app.logger.info(f'Running: nohup python3 worker.py --parent {self.parent} --other {self.other} --instance-id {instance.instance_id}  &> server.log &')
        # Run the setup.sh script on the instance
        stdin, stdout, stderr = ssh.exec_command(f'nohup python3 worker.py --parent {self.parent} --other {self.other} --instance-id {instance.instance_id}  &> worker.log &')
        
        return True

    def spawn(self):
        if self.is_test:
            return self.spawn_subprocess()
        else:
            return self.spawn_ec2_instance()
    
    def terminate_ec2_instance(self, instance_id):
        self.workers[instance_id].terminate()
        self.workers.pop(instance_id)
        return True
        
    def terminate(self, instance_id):
        if instance_id in self.workers:
            if self.is_test:
                # it's already terminated.
                self.workers.pop(instance_id)
                return True
            else:
                return self.terminate_ec2_instance(instance_id)
        app.logger.error(f'Big Balagan! worker {instance_id} is not in workers!')
        return False



@app.route('/jobs/terminate/<instance_id>', methods=['POST'])
def terminate_worker(instance_id):
    app.logger.info(f"Terminating instance {instance_id}")
    return str(manager.terminate(instance_id))


@app.route('/jobs/updateResult', methods=['PUT'])
def update_result():
    '''
    Update result from worker
    '''
    req = json.loads(request.data)
    app.logger.info(f"get results: {req}")
    jobs_completed.append({'id': req['id'], 'value': req['value']})
    return "thanks"



@app.route('/jobs/getJob', methods=['GET'])
def get_job():
    '''
    Get job for worker
    '''
    if not jobs_queue:
        return 'No jobs available', 400
    job = jobs_queue.pop(0)
    app.logger.info(f"Return new job: {job}")
    return job

@app.route('/enqueue', methods=['PUT'])
def enqueue_job():
    '''
    enqueues new requests
    '''
    buffer = request.get_data().decode('utf-8')
    iterations =  request.args.get('iterations')
    app.logger.info(f'Got request {iterations}, {buffer}')
    if iterations is None or not iterations.isdigit():
        return 'Bad Input', 400
    iterations = int(iterations)
    id = str(uuid())
    jobs_queue.append({'id': id, 'iterations': iterations, 'data': buffer, 'time': datetime.now()})
    app.logger.info(f"Got new job: {jobs_queue[-1]}, jobs queue len is {len(jobs_queue)}")

    # return to client
    return id

@app.route('/jobs/pullCompleted', methods=['POST'])
def internal_get_completed_jobs():
    k = request.args.get('top')
    if k is None or not k.isdigit():
        return "Bad Input", 400
    
    return jobs_completed[-int(k):]

@app.route('/jobs/getNumWorkers')
def get_num_workers():
    return manager.num_workers()

@app.route('/pullCompleted', methods=['POST'])
def get_completed_jobs():
    k = request.args.get('top')
    if k is None or not k.isdigit():
        return "Bad Input", 400
    k = int(k)
    top_k_jobs = jobs_completed[-int(k):]
    if top_k_jobs:
        return top_k_jobs
    app.logger.info("Don't have k jobs, ask other endpoint")
    # get other top k jobs
    if other_endpoint:
        try:
            response = requests.post(f'http://{other_endpoint}/jobs/pullCompleted?top={k}', headers={'Connection':'close'})
            if response.status_code == 200:
                return response.content
            return []
        except:
            app.logger.error(f'Connection to {other_endpoint} failed!')
            return []
    return []

@app.route('/jobs/getQuota', methods=['GET'])
def try_get_node_quota():
    global maxNumOfWorkers
    if manager.num_workers < maxNumOfWorkers:
        maxNumOfWorkers -= 1
        return {'possible': True}
    return {'possible': False}

def check_workers_state():
    global maxNumOfWorkers
    # no jobs no cry
    if len(jobs_queue) == 0:
        return
    
    first_job_time = jobs_queue[0]['time']
    to_spawn = False
    if datetime.now() - first_job_time > timedelta(seconds=15):
        app.logger.info(f'It has been more than 15 seconds since last worked job.')
        if manager.num_workers() < maxNumOfWorkers: 
            app.logger.info('Sufficient quota for spawining a worker.')
            to_spawn = True
        else:
            app.logger.warning(f'Insufficient quota, checking with {other_endpoint}')
            try:
                response = requests.get(f'http://{other_endpoint}/jobs/getQuota', headers={'Connection':'close'})
                if response.status_code == 200 and response.json()['possible'] == True:
                    app.logger.info(f'{other_endpoint} has given us an extra one')
                    maxNumOfWorkers+=1
                    to_spawn = True
            except:
                app.logger.error(f'Connection to {other_endpoint} failed!')
    if to_spawn:
        app.logger.info('Spawning a new worker...')
        res = manager.spawn()
        if res:
            app.logger.error('Worker spawned successfuly!')
        else:
            app.logger.error('ERROR in spawning worker')
                



if __name__ == '__main__':
    from argparse import ArgumentParser
    parser = ArgumentParser(description='Hash calculating EC2 endpoint flask server')
    parser.add_argument('--port', dest='port', type=int, default=8000, help='local port')
    parser.add_argument('--other', dest='other', help='other with port')
    parser.add_argument('--max-num', dest='max_num',type=int, default=3, help='max num of workers')
    parser.add_argument('--test', dest='test', default=False, action='store_true')
    args = parser.parse_args()
    other_endpoint = args.other
    maxNumOfWorkers = args.max_num
    is_test = args.test
    ip = requests.get('https://api.ipify.org').content.decode('utf8')
    print(f"Got IP {ip}")

    manager = WorkerManager(parent=f'{ip}:{args.port}', other=other_endpoint, is_test=args.test)
    # set background timer
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=check_workers_state, trigger="interval", seconds=120)
    scheduler.start()

    # Shut down the scheduler when exiting the app
    atexit.register(lambda: scheduler.shutdown())


    app.run('0.0.0.0', port=args.port, debug=True)  