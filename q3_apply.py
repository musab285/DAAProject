import os
import time

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = HERE

from q2_closest_pair import closest_pair_dc, closest_pair_brute
from q2_karatsuba import karatsuba_mul, schoolbook_mul

BRUTE_LIMIT = 4000


from q2_input import read_points as parse_points, read_numbers as parse_numbers


def read_points(path):
    with open(path, encoding="utf-8") as f:
        return parse_points(f.read())


def read_numbers(path):
    with open(path, encoding="utf-8") as f:
        return parse_numbers(f.read())


def run_closest_pair():
    folder = DATA
    print(f"{'file':40s} {'n':>6s} {'distance':>14s} {'dc ms':>9s} {'brute ms':>10s} {'check':>7s}")
    rows = []
    for name in sorted(os.listdir(folder)):
        if not name.startswith("q2_closest_pair_") or not name.endswith(".txt") or not os.path.isfile(os.path.join(folder, name)):
            continue
        pts = read_points(os.path.join(folder, name))
        t0 = time.perf_counter()
        dist, pair, _ = closest_pair_dc(pts)
        dc_ms = (time.perf_counter() - t0) * 1000

        if len(pts) <= BRUTE_LIMIT:
            t1 = time.perf_counter()
            bf_dist, _ = closest_pair_brute(pts)
            bf_ms = (time.perf_counter() - t1) * 1000
            ok = abs(bf_dist - dist) < 1e-9
            bf_text = f"{bf_ms:10.2f}"
            check = "ok" if ok else "MISMATCH"
        else:
            bf_ms = None
            bf_text = f"{'-':>10s}"
            own = ((pair[0][0] - pair[1][0]) ** 2 + (pair[0][1] - pair[1][1]) ** 2) ** 0.5
            check = "pair ok" if abs(own - dist) < 1e-9 else "BAD PAIR"

        print(f"{name:40s} {len(pts):6d} {dist:14.6f} {dc_ms:9.3f} {bf_text} {check:>7s}")
        rows.append({"file": name, "n": len(pts), "distance": dist, "pair": pair,
                     "dc_ms": dc_ms, "brute_ms": bf_ms, "check": check})
    print()
    return rows


def run_integer_multiplication():
    folder = DATA
    print(f"{'file':44s} {'a':>6s} {'b':>6s} {'karatsuba ms':>13s} {'schoolbook ms':>14s} {'check':>7s}")
    rows = []
    for name in sorted(os.listdir(folder)):
        if not name.startswith("q2_integer_multiplication_") or not name.endswith(".txt") or not os.path.isfile(os.path.join(folder, name)):
            continue
        a, b = read_numbers(os.path.join(folder, name))
        t0 = time.perf_counter()
        product = karatsuba_mul(a, b)
        k_ms = (time.perf_counter() - t0) * 1000

        t1 = time.perf_counter()
        sb = schoolbook_mul(a, b)
        sb_ms = (time.perf_counter() - t1) * 1000

        ok = sb == product
        print(f"{name:44s} {len(a):6d} {len(b):6d} {k_ms:13.3f} {sb_ms:14.2f} {'ok' if ok else 'MISMATCH':>7s}")
        rows.append({"file": name, "a_digits": len(a), "b_digits": len(b),
                     "product_digits": len(product), "product": product,
                     "karatsuba_ms": k_ms, "schoolbook_ms": sb_ms,
                     "check": "ok" if ok else "MISMATCH"})
    print()
    return rows


def main():
    print("Q3 - divide and conquer closest pair of points")
    print()
    cp_rows = run_closest_pair()
    print("Q3 - Karatsuba integer multiplication")
    print()
    im_rows = run_integer_multiplication()

    print("answers for the report")
    print()
    for r in cp_rows:
        p = r["pair"]
        print(f"{r['file']:40s} closest pair = {p[0]} and {p[1]}  distance = {r['distance']:.6f}")
    print()
    for r in im_rows:
        head = r["product"][:28]
        tail = r["product"][-8:]
        print(f"{r['file']:44s} product has {r['product_digits']} digits  starts {head}... ends {tail}")


if __name__ == "__main__":
    main()
