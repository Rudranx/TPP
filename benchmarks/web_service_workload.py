import random
import time


def make_payload(seed, size=4096):
    rng = random.Random(seed)
    return bytearray(rng.getrandbits(8) for _ in range(size))


def main():
    rng = random.Random(1)
    sessions = {}
    route_cache = {}

    for user_id in range(600):
        sessions[user_id] = make_payload(user_id, size=2048)
        if user_id % 25 == 0:
            time.sleep(0.005)

    routes = ["/feed", "/search", "/profile", "/messages", "/ads"]
    for request_id in range(5000):
        user_id = rng.randrange(600)
        route = rng.choice(routes)
        key = (route, user_id % 128)
        if key not in route_cache:
            route_cache[key] = make_payload(request_id, size=1024)

        session = sessions[user_id]
        response = route_cache[key]
        session[request_id % len(session)] ^= response[request_id % len(response)]

        if request_id % 250 == 0:
            time.sleep(0.005)


if __name__ == "__main__":
    main()
