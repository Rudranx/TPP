import math
import random

try:
    import numpy as np
except ImportError:
    np = None


def vector(size):
    if np:
        return np.random.rand(size)
    return [random.random() for _ in range(size)]


def cosine_similarity(a, b):
    if np:
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    return dot / max(norm_a * norm_b, 1e-9)


embeddings = {i: vector(128) for i in range(5000)}
ads = {i: vector(128) for i in range(1000)}


if __name__ == "__main__":
    best_ad = 0.0
    for _ in range(20000):
        user = random.randint(1, 1000)
        user_vec = embeddings[user]
        scores = []
        for ad_id in range(50):
            ad_vec = ads[ad_id]
            scores.append(cosine_similarity(user_vec, ad_vec))
        best_ad += max(scores)
    print(f"{best_ad:.4f}")
