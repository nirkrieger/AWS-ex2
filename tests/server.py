from flask import *

app = Flask(__name__)

@app.route('/put', methods=['PUT'])
def put():
    pass

@app.route('/get/<int:num>', methods=['GET'])
def get(num):
    if int(num) == 5:
        return {1:2}
    return 'No jobs available', 400

if __name__ == "__main__":
    app.run()