import random
import time


def main():
    rng = random.Random(2)
    users = [[rng.random() for _ in range(64)] for _ in range(400)]
    ads = [[rng.random() for _ in range(64)] for _ in range(1200)]
    campaign_cache = {}

    for campaign in range(300):
        campaign_cache[campaign] = bytearray(4096)
        if campaign % 40 == 0:
            time.sleep(0.005)

    score_sink = 0.0
    for request in range(2500):
        user = users[rng.randrange(len(users))]
        best_score = -1.0
        for _ in range(24):
            ad_id = rng.randrange(len(ads))
            ad = ads[ad_id]
            score = sum(u * a for u, a in zip(user, ad))
            if score > best_score:
                best_score = score
        campaign_cache[request % 300][request % 4096] = int(best_score) % 255
        score_sink += best_score
        if request % 150 == 0:
            time.sleep(0.005)

    print(f"{score_sink:.2f}")


if __name__ == "__main__":
    main()
