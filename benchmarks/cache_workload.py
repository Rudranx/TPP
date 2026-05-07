import random
import time


def main():
    rng = random.Random(5)
    cache = {key: bytearray(2048) for key in range(2500)}
    hot_keys = list(range(250))

    hits = 0
    for request in range(12000):
        if rng.random() < 0.85:
            key = rng.choice(hot_keys)
        else:
            key = rng.randrange(2500)
        value = cache[key]
        value[request % len(value)] ^= key % 255
        hits += 1
        if request % 600 == 0:
            time.sleep(0.005)

    print(hits)


if __name__ == "__main__":
    main()
