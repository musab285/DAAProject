import json
import math
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
CP = HERE
IM = HERE


def points_uniform(n, rng):
    return [(rng.uniform(0, 1000), rng.uniform(0, 1000)) for _ in range(n)]


def points_gaussian(n, rng):
    return [(rng.gauss(500, 150), rng.gauss(500, 150)) for _ in range(n)]


def points_clustered(n, rng):
    centers = [(rng.uniform(100, 900), rng.uniform(100, 900)) for _ in range(8)]
    out = []
    for i in range(n):
        cx, cy = centers[i % 8]
        out.append((rng.gauss(cx, 12), rng.gauss(cy, 12)))
    return out


def points_grid(n, rng):
    side = int(math.ceil(math.sqrt(n)))
    step = 1000 / side
    out = []
    for i in range(side):
        for j in range(side):
            if len(out) == n:
                return out
            out.append((i * step + rng.uniform(0, step / 3), j * step + rng.uniform(0, step / 3)))
    return out


def points_circle(n, rng):
    out = []
    for i in range(n):
        t = 2 * math.pi * i / n
        out.append((500 + 300 * math.cos(t) + rng.uniform(-1, 1), 500 + 300 * math.sin(t) + rng.uniform(-1, 1)))
    return out


CP_FILES = [
    ("q2_closest_pair_01_120.txt", 120, points_uniform),
    ("q2_closest_pair_02_250.txt", 250, points_uniform),
    ("q2_closest_pair_03_400.txt", 400, points_gaussian),
    ("q2_closest_pair_04_600.txt", 600, points_clustered),
    ("q2_closest_pair_05_900.txt", 900, points_grid),
    ("q2_closest_pair_06_1500.txt", 1500, points_uniform),
    ("q2_closest_pair_07_2500.txt", 2500, points_clustered),
    ("q2_closest_pair_08_4000.txt", 4000, points_uniform),
    ("q2_closest_pair_09_6000.txt", 6000, points_circle),
    ("q2_closest_pair_10_10000.txt", 10000, points_uniform),
]

IM_FILES = [
    ("q2_integer_multiplication_01_50.txt", 50, 50),
    ("q2_integer_multiplication_02_100.txt", 100, 100),
    ("q2_integer_multiplication_03_250.txt", 250, 250),
    ("q2_integer_multiplication_04_500.txt", 500, 500),
    ("q2_integer_multiplication_05_1000.txt", 1000, 1000),
    ("q2_integer_multiplication_06_2000.txt", 2000, 2000),
    ("q2_integer_multiplication_07_4000.txt", 4000, 4000),
    ("q2_integer_multiplication_08_6000.txt", 6000, 6000),
    ("q2_integer_multiplication_09_8000.txt", 8000, 8000),
    ("q2_integer_multiplication_10_unbalanced.txt", 500, 12000),
]


def digits(n, rng):
    if isinstance(n, bool) or not isinstance(n, int) or n < 1:
        raise ValueError("digit count must be a positive integer")
    return rng.choice("123456789") + "".join(rng.choice("0123456789") for _ in range(n - 1))


def main():
    os.makedirs(CP, exist_ok=True)
    os.makedirs(IM, exist_ok=True)
    catalog = {"closest_pair": [], "integer_multiplication": []}

    for i, (name, n, gen) in enumerate(CP_FILES):
        rng = random.Random(100 + i)
        pts = gen(n, rng)
        with open(os.path.join(CP, name), "w") as f:
            f.write(f"{n}\n")
            for x, y in pts:
                f.write(f"{x:.6f} {y:.6f}\n")
        catalog["closest_pair"].append({"file": name, "n": n, "seed": 100 + i})

    for i, (name, la, lb) in enumerate(IM_FILES):
        rng = random.Random(500 + i)
        a, b = digits(la, rng), digits(lb, rng)
        with open(os.path.join(IM, name), "w") as f:
            f.write(a + "\n" + b + "\n")
        catalog["integer_multiplication"].append(
            {"file": name, "a_digits": la, "b_digits": lb, "seed": 500 + i})

    with open(os.path.join(HERE, "q2_catalog.json"), "w") as f:
        json.dump(catalog, f, indent=2)
    print("datasets written")


if __name__ == "__main__":
    main()
