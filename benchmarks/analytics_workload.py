import random
import time


def main():
    rng = random.Random(4)
    rows = 900
    cols = 96
    matrix = [[rng.random() for _ in range(cols)] for _ in range(rows)]
    weights = [rng.random() for _ in range(cols)]
    buckets = [0.0 for _ in range(32)]

    for iteration in range(80):
        for row_id, row in enumerate(matrix):
            value = sum(item * weight for item, weight in zip(row, weights))
            buckets[row_id % len(buckets)] += value
        if iteration % 8 == 0:
            time.sleep(0.005)

    print(sum(buckets))


if __name__ == "__main__":
    main()
