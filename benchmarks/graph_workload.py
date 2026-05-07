import random
from collections import defaultdict, deque


graph = defaultdict(list)

for _ in range(10000):
    u = random.randint(1, 1000)
    v = random.randint(1, 1000)
    graph[u].append(v)

visited = set()
queue = deque([1])

while queue:
    node = queue.popleft()
    if node in visited:
        continue
    visited.add(node)
    for neighbor in graph[node]:
        queue.append(neighbor)

print(len(visited))
