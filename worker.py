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
    def __init__(self, nodes=['localhost:8000']):
        self.nodes = nodes

    def work(self, buffer, iterations):
        output = hashlib.sha512(buffer.encode('utf-8')).digest()
        for i in range(iterations - 1):
            output = hashlib.sha512(output).digest()
        return str(base64.b64encode(output))

    def loop(self):
        last_job = datetime.now()
        while datetime.now() - last_job < timedelta(minutes=10):
            for node in self.nodes:
                # get a job
                response = requests.get(f'http://{node}/jobs/getJob', headers={'Connection':'close'})
                # if valid
                if response.status_code == 200:
                    try:
                        res = response.json()
                        if res:
                            value = self.work(res['data'],res['iterations'])
                            # print(f'Job Done! id:{res["id"]}, value:{value}')
                            res = requests.put(f'http://{node}/jobs/updateResult', 
                                            data=json.dumps({'id': res['id'],
                                                                'value': value,
                                                                'complete_time': str(time.time())
                                                                }), headers={'Connection':'close'})
                            last_job = datetime.now()
                    except:
                        print("ERROR in loading json")

if __name__ == '__main__':
    worker = Worker(['localhost:8000', 
                     'localhost:8001'])
    worker.loop()