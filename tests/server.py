from flask import *

app = Flask(__name__)


@app.route('/', methods=['GET'])
def get():
    return "Hello World!"

if __name__ == "__main__":
    app.run()