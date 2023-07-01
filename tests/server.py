from flask import *
from datetime import datetime

app = Flask(__name__)

count = 0

@app.route('/jobs/getJob')
def get():
    global count
    if count < 1:
        count += 1
        return {'id': 123, 'iterations': 2, 'data': "BUFFER DATA!!!", 'time': datetime.now()}
    return "End!", 400

@app.route('/jobs/updateResult', methods=['PUT'])
def update():
    return 'True'

@app.route('/jobs/terminate/<instance_id>', methods=['POST'])
def terminate_worker(instance_id):
    return 'True'


if __name__ == "__main__":
    app.run(port=8000)