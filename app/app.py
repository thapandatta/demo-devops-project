
from flask import Flask, request

app = Flask(__name__)

@app.route("/")
def home():
    instance_ip = request.host.split(":")[0]
    return f"Hello from {instance_ip}"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
