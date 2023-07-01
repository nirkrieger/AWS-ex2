''' 
This is the worker file
Logic:
It runs on an EC2 instance, runs a loop: as long as there's work to do:
a) fetch the endpoint nodes
b) ask them for work - gets id, buffer and iterations
c) do the work
d) puts the value back

'''
import base64
import requests
import hashlib
import json
from datetime import datetime, timedelta
import time 

class Worker:
    def __init__(self, instance_id='1', parent='localhost:8000', other='localhost:8001'):
        self.instance_id = instance_id
        self.parent = parent
        self.other = other

    def sendTerminate(self):
        resp = requests.post(f'http://{self.parent}/jobs/terminate/{self.instance_id}')
        return resp.status_code == 200
            


    def work(self, buffer, iterations):
        output = hashlib.sha512(buffer.encode('utf-8')).digest()
        for i in range(iterations - 1):
            output = hashlib.sha512(output).digest()
        return str(base64.b64encode(output))

    def loop(self):
        last_job = datetime.now()
        # while datetime.now() - last_job < timedelta(minutes=10):
        while datetime.now() - last_job < timedelta(seconds=20):
            print(f'Last Job: {last_job}, Now: {datetime.now()}')
            got_job = False
            for node in [self.parent, self.other]:
                # get a job
                print(f'Request to {node}')
                try:
                    response = requests.get(f'http://{node}/jobs/getJob')
                except:
                    print(f'Connection to {node} failed!')
                    continue
                # if valid
                if response.status_code != 200:
                    print(f'Connection status is {response.status_code}, continue!')
                    continue
                res = None
                try:
                    res = response.json()
                except:
                    print(f"ERROR in loading json from content: {response.content}")
                    continue

                got_job = True
                if res:
                    print(f'Starting work: iterations={res["iterations"]}, lendata={len(res["data"])}')
                    value = self.work(res['data'],res['iterations'])
                    print(f'Job Done! id:{res["id"]}, value:{value}')
                    try:
                        res = requests.put(f'http://{node}/jobs/updateResult', 
                                    data=json.dumps({'id': res['id'],
                                                        'value': value,
                                                        'complete_time': str(time.time())
                                                        }), headers={'Connection':'close'})
                        if res.status_code == 200:
                            print(f'Results sent to {node}/jobs/updateResult')
                        else:
                            print(f'status:{res.status_code}, {res.content}')
                    except:
                        print(f'Connection to {node} failed!')
                
                last_job = datetime.now()
                
            if not got_job:            
                print(f"Didn't get job, Sleep 10secs, now: {datetime.now()}")
                time.sleep(10)
                
        print(f"Timeout! no jobs since {last_job}. Terminate!")
        if self.sendTerminate():
            print(f"Worker {self.instance_id} is terminating!")
        else:
            print('Terminating failed!')
            

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='HW2 Worker usage')
    parser.add_argument('--parent', dest='parent', default='localhost:8000')
    parser.add_argument('--other', dest='other', default='localhost:8001')
    parser.add_argument('--instance-id', dest='instance_id', required=True)
    args = parser.parse_args()
    worker = Worker(args.instance_id, args.parent, args.other)
    print(f'Initialized a new worker, starting loop.')
    worker.loop()