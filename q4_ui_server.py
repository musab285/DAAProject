import json
import os
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = HERE

from q2_closest_pair import closest_pair_dc, closest_pair_brute
from q2_karatsuba import karatsuba_mul, schoolbook_mul

SHAPES = {
    "q2_closest_pair_01_120.txt": "uniform random",
    "q2_closest_pair_02_250.txt": "uniform random",
    "q2_closest_pair_03_400.txt": "gaussian cloud",
    "q2_closest_pair_04_600.txt": "8 clusters",
    "q2_closest_pair_05_900.txt": "jittered grid",
    "q2_closest_pair_06_1500.txt": "uniform random",
    "q2_closest_pair_07_2500.txt": "8 clusters",
    "q2_closest_pair_08_4000.txt": "uniform random",
    "q2_closest_pair_09_6000.txt": "circle plus noise",
    "q2_closest_pair_10_10000.txt": "uniform random",
}


from q2_input import read_points, read_numbers
from q4_steps import Steps


def detect(text):
    data = [l.strip() for l in text.splitlines() if l.strip()]
    if not data:
        raise ValueError("the file is empty")
    if len(data[0].split()) >= 2:
        return "closest_pair"
    if len(data) > 1 and len(data[1].split()) >= 2:
        return "closest_pair"
    return "integer_multiplication"


def closest_pair_result(pts):
    px = sorted(pts)
    collector = Steps(px)
    cutoff = 3 if len(pts) <= 32 else 16
    t0 = time.perf_counter()
    dist, pair, px = closest_pair_dc(pts, cutoff=cutoff, on_step=collector)
    elapsed = (time.perf_counter() - t0) * 1000
    steps = collector.finish([f"Closest pair: {pair[0]} and {pair[1]}", f"Minimum distance = {dist:.6g}"])

    brute = None
    if len(pts) <= 3000:
        t1 = time.perf_counter()
        b_dist, _ = closest_pair_brute(pts)
        brute = {"distance": b_dist, "ms": (time.perf_counter() - t1) * 1000,
                 "match": abs(b_dist - dist) < 1e-9}

    return {"points": [list(p) for p in px],
            "distance": dist,
            "pair": [list(pair[0]), list(pair[1])],
            "steps": steps,
            "cutoff": cutoff, "omitted": collector.omitted,
            "brute": brute,
            "ms": elapsed,
            "n": len(pts)}


def karatsuba_result(a, b):
    collector = Steps()
    threshold = 1 if max(len(a), len(b)) <= 100 else 16
    t0 = time.perf_counter()
    product = karatsuba_mul(a, b, threshold=threshold, on_step=collector)
    elapsed = (time.perf_counter() - t0) * 1000
    steps = collector.finish(["All subproducts have been combined.",
                              "Apply the original operand signs to obtain the final product."])

    t1 = time.perf_counter()
    sb = schoolbook_mul(a, b)
    sb_ms = (time.perf_counter() - t1) * 1000

    return {"product": product, "threshold": threshold, "omitted": collector.omitted,
            "product_digits": len(product.lstrip("-")),
            "a": a, "b": b,
            "a_digits": len(a.lstrip("-")), "b_digits": len(b.lstrip("-")),
            "steps": steps,
            "schoolbook_ms": sb_ms,
            "match": sb == product,
            "ms": elapsed}


def catalogue():
    out = []
    for kind in ("closest_pair", "integer_multiplication"):
        folder = DATA
        for name in sorted(os.listdir(folder)):
            path = os.path.join(folder, name)
            if not name.startswith("q2_" + kind + "_") or not name.endswith(".txt") or not os.path.isfile(path):
                continue
            entry = {"kind": kind, "name": name, "bytes": os.path.getsize(path)}
            with open(path) as f:
                text = f.read()
            if kind == "closest_pair":
                entry["n"] = len(read_points(text))
                entry["shape"] = SHAPES.get(name, "custom")
            else:
                a, b = read_numbers(text)
                entry["a_digits"] = len(a)
                entry["b_digits"] = len(b)
                entry["shape"] = "unbalanced" if len(a) != len(b) else "balanced"
            out.append(entry)
    return out


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, code, body, ctype="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj, allow_nan=False).encode())

    def do_GET(self):
        url = urlparse(self.path)
        if url.path in ("/", "/index.html"):
            with open(os.path.join(HERE, "q4_ui.html"), "rb") as f:
                return self._send(200, f.read(), "text/html")
        if url.path == "/q4_ui.js":
            with open(os.path.join(HERE, "q4_ui.js"), "rb") as f:
                return self._send(200, f.read(), "text/javascript")
        if url.path == "/api/files":
            return self._json({"files": catalogue()})
        if url.path == "/api/file":
            name = os.path.basename(parse_qs(url.query).get("name", [""])[0])
            for kind in ("closest_pair", "integer_multiplication"):
                path = os.path.join(DATA, name)
                if name.startswith("q2_" + kind + "_") and name.endswith(".txt") and os.path.isfile(path):
                    with open(path) as f:
                        text = f.read()
                    return self._json({"ok": True, "kind": kind, "name": name,
                                       "preview": "\n".join(text.splitlines()[:60]),
                                       "lines": len(text.splitlines()),
                                       "size": os.path.getsize(path)})
            return self._json({"ok": False, "error": "file not found"}, 404)
        return self._json({"ok": False, "error": "not found"}, 404)

    def do_POST(self):
        url = urlparse(self.path)
        if url.path not in ("/api/run", "/api/prepare"):
            return self._json({"ok": False, "error": "not found"}, 404)
        try:
            length = int(self.headers.get("Content-Length") or 0)
            if length < 0 or length > 21 * 1024 * 1024:
                return self._json({"ok": False, "error": "request is too large"}, 413)
            body = json.loads(self.rfile.read(length) or b"{}")
            if not isinstance(body, dict):
                raise ValueError("request must be a JSON object")
            if not isinstance(body.get("name", ""), str):
                raise ValueError("name must be a string")
            if "content" in body and not isinstance(body["content"], str):
                raise ValueError("content must be a string")
            if "content" in body:
                text = body["content"]
                name = body.get("name", "uploaded.txt")
                kind = detect(text)
            else:
                name = os.path.basename(body.get("name", ""))
                path = None
                for k in ("closest_pair", "integer_multiplication"):
                    candidate = os.path.join(DATA, name)
                    if name.startswith("q2_" + k + "_") and name.endswith(".txt") and os.path.isfile(candidate):
                        path = candidate
                        break
                if path is None:
                    return self._json({"ok": False, "error": "file not found"}, 404)
                with open(path) as f:
                    text = f.read()
                kind = detect(text)

            if url.path == "/api/prepare":
                result = {"points": read_points(text)} if kind == "closest_pair" else dict(zip(("a", "b"), read_numbers(text)))
                return self._json({"ok": True, "kind": kind, "name": name, "input": result,
                                   "preview": "\n".join(text.splitlines()[:60]), "size": len(text.encode())})

            if kind == "closest_pair":
                pts = read_points(text)
                if len(pts) < 2:
                    return self._json({"ok": False, "error": "need at least two points"}, 400)
                result = closest_pair_result(pts)
            else:
                try:
                    a, b = read_numbers(text)
                except IndexError:
                    return self._json({"ok": False, "error": "need two lines with one integer each"}, 400)
                result = karatsuba_result(a, b)
            return self._json({"ok": True, "kind": kind, "name": name, "result": result})
        except Exception as exc:
            return self._json({"ok": False, "error": str(exc)}, 400)


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"open http://localhost:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
