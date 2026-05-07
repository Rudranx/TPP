import time


def main():
    data = []
    for _ in range(32):
        data.append(bytearray(1024 * 1024))
        time.sleep(0.02)

    for block in data:
        block[0] = 1
        block[-1] = 1

    time.sleep(0.5)


if __name__ == "__main__":
    main()
