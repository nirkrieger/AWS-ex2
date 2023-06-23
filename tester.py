from time import sleep
import requests
import subprocess

node_a = 'localhost:8000'
node_b = 'localhost:8001'

session_a = requests.Session()
session_a.headers.update({'Connection':'close'})

sessions_b = requests.Session()
sessions_b.headers.update({'Connection':'close'})

print(">> Adding jobs to Node B")
for _ in range(5):
    response = sessions_b.put(f'http://{node_b}/enqueue?iterations=5', data='Hello World')
    if response.status_code != requests.status_codes.codes.all_ok:
        print(f"ERROR: server returns {response.status_code}")
#sleep(3)
print(">> Adding worker")
import os
a = subprocess.Popen('python3 worker.py')
print("SLEEP 3 SECS")
sleep(3)

print(">> Get jobs completed from node A")
response = requests.post(f'http://{node_a}/pullCompleted?top=3')
print(f">> Response: {response.content}")
#sleep(3)

# print(">> Get jobs completed from node A")
# response = sessions_b.post(f'http://{node_b}/pullCompleted?top=3')
# print(f">> Response: {response.content}")
#sleep(3)

a.kill()

