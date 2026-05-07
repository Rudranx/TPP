import random


hashmap = {}

for i in range(100000):
    key = random.randint(1, 10000)
    hashmap[key] = random.randint(1, 100000)

total = 0
for _ in range(50000):
    key = random.randint(1, 1000)
    value = hashmap.get(key)
    if value is not None:
        total += value

print(total)
