import random

try:
    import numpy as np
except ImportError:
    np = None


if np:
    A = np.random.rand(500, 500)
    B = np.random.rand(500, 500)
    C = np.matmul(A, B)
    print(C.shape)
else:
    size = 160
    A = [[random.random() for _ in range(size)] for _ in range(size)]
    B = [[random.random() for _ in range(size)] for _ in range(size)]
    C = [[0.0 for _ in range(size)] for _ in range(size)]
    for i in range(size):
        for k in range(size):
            aik = A[i][k]
            for j in range(size):
                C[i][j] += aik * B[k][j]
    print((len(C), len(C[0])))
