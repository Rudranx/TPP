import random

try:
    from flask import Flask
except ImportError:
    Flask = None


app = Flask(__name__) if Flask else None
cache = {}
database = {}

for i in range(10000):
    database[i] = {
        "user": f"user_{i}",
        "score": random.randint(1, 1000),
        "payload": bytearray(512),
    }


def home():
    user_id = random.randint(1, 1000)
    if user_id in cache:
        data = cache[user_id]
    else:
        data = database[user_id]
        cache[user_id] = data
    data["payload"][user_id % 512] ^= data["score"] % 255
    return str(data["score"])


if app:
    app.route("/")(home)


if __name__ == "__main__":
    for _ in range(10000):
        home()
