import random
import time


def main():
    rng = random.Random(3)
    graph = {node: set() for node in range(5000)}
    for node in range(5000):
        for _ in range(6):
            graph[node].add(rng.randrange(5000))
        if node % 500 == 0:
            time.sleep(0.005)

    table = {node: bytearray(1024) for node in range(2500)}
    visited_total = 0
    for start in range(0, 5000, 25):
        stack = [start]
        visited = set()
        while stack and len(visited) < 200:
            node = stack.pop()
            if node in visited:
                continue
            visited.add(node)
            if node in table:
                table[node][node % 1024] = len(visited) % 255
            stack.extend(graph[node])
        visited_total += len(visited)
        if start % 250 == 0:
            time.sleep(0.005)

    print(visited_total)


if __name__ == "__main__":
    main()
