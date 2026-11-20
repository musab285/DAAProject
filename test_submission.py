import json
import io
import math
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
from q2_closest_pair import closest_pair_dc, closest_pair_brute, trace
from q2_karatsuba import karatsuba_mul, schoolbook_mul
from q2_input import read_points, read_numbers
import q2_generate_datasets as generator
import q4_ui_server as server


class Algorithms(unittest.TestCase):
    def test_multiplication(self):
        rng = random.Random(17)
        cases = [('0', '0'), ('-000', '+123'), ('-12', '-34'), ('-12', '34')]
        for digits in (1, 9, 18, 80, 170, 300, 600):
            cases.append((''.join(rng.choices('123456789', k=digits)),
                          ''.join(rng.choices('0123456789', k=digits + 19))))
        for a, b in cases:
            expected = str(int(a) * int(b))
            self.assertEqual(schoolbook_mul(a, b), expected)
            for threshold in (1, 2, 16):
                self.assertEqual(karatsuba_mul(a, b, threshold), expected)
        self.assertTrue(karatsuba_mul('0', '1', trace=True)[1])
        for value in ('', '+', '1_2', '1.2', 'abc', '１２'):
            with self.assertRaises(ValueError):
                karatsuba_mul(value, '2')
        for threshold in (0, -1, 1.5, True):
            with self.assertRaises(ValueError):
                karatsuba_mul('2', '3', threshold)

    def test_closest_pair(self):
        rng = random.Random(19)
        cases = [[(0, 0), (0, 0)], [(1e200, 0), (2e200, 0)],
                 [(0, 0), (1e-200, 0)]]
        cases += [[(rng.randrange(-30, 30), rng.randrange(-30, 30))
                   for _ in range(n)] for n in (2, 3, 17, 33, 101)]
        for points in cases:
            expected = closest_pair_brute(points)[0]
            for cutoff in (2, 3, 16):
                actual, pair, _ = closest_pair_dc(points, cutoff)
                self.assertEqual(actual, expected)
                self.assertEqual(math.dist(*pair), expected)
        for points in ([], [(1, 2)], [(0, 0), (math.nan, 2)],
                       [(0, 0), (math.inf, 2)]):
            for fn in (closest_pair_dc, closest_pair_brute, trace):
                with self.assertRaises(ValueError):
                    fn(points)
        for cutoff in (0, 1, -1, True, 2.5):
            with self.assertRaises(ValueError):
                closest_pair_dc([(0, 0), (1, 1)], cutoff)

    def test_parsing(self):
        self.assertEqual(read_points('2\n0 0\n1 1'), [(0, 0), (1, 1)])
        self.assertEqual(read_points('0 0\n1 1'), [(0, 0), (1, 1)])
        self.assertEqual(read_numbers('-0012\n+003'), ('-12', '3'))
        for text in ('3\n0 0\n1 1', '0 0 8\n1 1', '2\nnan 0\n0 0'):
            with self.assertRaises(ValueError):
                read_points(text)
        for text in ('', '1', '1\n2\n3', '1_2\n3'):
            with self.assertRaises(ValueError):
                read_numbers(text)
        self.assertEqual(server.detect('-12\n34'), 'integer_multiplication')
        self.assertEqual(server.karatsuba_result('0', '1')['product'], '0')
        json.dumps(server.closest_pair_result([(0, 0), (1e200, 0)]), allow_nan=False)

    def test_recorded_steps(self):
        points = [(1, 1), (2, 2), (3, 8), (5, 5), (6, 5), (9, 9)]
        result = server.closest_pair_result(points)
        self.assertEqual(result['distance'], closest_pair_brute(points)[0])
        kinds = [s['kind'] for s in result['steps']]
        self.assertEqual(kinds[0], 'split')
        self.assertEqual(kinds[-1], 'answer')
        for kind in ('base', 'compare', 'merge', 'strip', 'combine'):
            self.assertIn(kind, kinds)
        for step in result['steps']:
            if step['kind'] == 'compare':
                self.assertEqual(math.dist(*step['pair']), step['distance'])
        events = []
        a, b = '123456789123456789', '987654321987654321'
        product = karatsuba_mul(a, b, threshold=1, on_step=events.append)
        self.assertEqual(product, str(int(a) * int(b)))
        from q2_karatsuba import _to_str
        root = {e['kind']: e for e in events if e['depth'] == 0}
        z2 = int(_to_str(root['z2']['value']))
        z0 = int(_to_str(root['z0']['value']))
        z1 = int(_to_str(root['z1']['value']))
        shift = 10 ** (9 * root['split']['half'])
        self.assertEqual(z2 * shift ** 2 + z1 * shift + z0, int(product))
        result = server.karatsuba_result(a, b)
        self.assertEqual(result['steps'][-1]['kind'], 'answer')
        self.assertTrue(all('lines' in step for step in result['steps']))
        # Large runs still calculate the full answer while limiting playback.
        large = server.closest_pair_result([(i, i % 7) for i in range(1000)])
        self.assertGreater(large['omitted'], 0)
        self.assertLess(len(large['steps']), 150)
        json.dumps(large, allow_nan=False)

    def test_all_datasets_and_reproducibility(self):
        catalog = json.loads((ROOT / 'q2_catalog.json').read_text())
        with tempfile.TemporaryDirectory() as tmp:
            original_cp, original_im = generator.CP, generator.IM
            # Generate into a temporary tree, including the catalog.
            original_here = generator.HERE
            try:
                generator.HERE = tmp
                generator.CP = tmp
                generator.IM = tmp
                generator.main()
                for kind, entries in catalog.items():
                    self.assertEqual(len(entries), 10)
                    for entry in entries:
                        path = ROOT / entry['file']
                        self.assertEqual(path.read_text(), (Path(tmp) / entry['file']).read_text())
                        text = path.read_text()
                        if kind == 'closest_pair':
                            points = read_points(text)
                            self.assertEqual(len(points), entry['n'])
                            self.assertIsNotNone(closest_pair_dc(points)[1])
                        else:
                            a, b = read_numbers(text)
                            self.assertEqual((len(a), len(b)), (entry['a_digits'], entry['b_digits']))
                            self.assertEqual(karatsuba_mul(a, b), schoolbook_mul(a, b))
            finally:
                generator.HERE, generator.CP, generator.IM = original_here, original_cp, original_im


class API(unittest.TestCase):
    def request(self, method, path, payload=b''):
        class Connection:
            def __init__(self):
                self.output = bytearray()

            def makefile(self, mode, *args):
                return io.BytesIO(
                    f"{method} {path} HTTP/1.0\r\nContent-Length: {len(payload)}\r\n\r\n".encode()
                    + payload)

            def sendall(self, data):
                self.output.extend(data)

        connection = Connection()
        server.Handler(connection, ('127.0.0.1', 1234), None)
        headers, body = bytes(connection.output).split(b'\r\n\r\n', 1)
        return int(headers.split()[1]), body

    def test_prepare_does_not_calculate_answers(self):
        for content, kind in [('2\n0 0\n3 4', 'closest_pair'), ('12\n34', 'integer_multiplication')]:
            with patch.object(server, 'closest_pair_result', side_effect=AssertionError('calculation during input load')), \
                 patch.object(server, 'karatsuba_result', side_effect=AssertionError('calculation during input load')):
                status, body = self.request('POST', '/api/prepare', json.dumps({'content': content}).encode())
                self.assertEqual(status, 200, body)
                data = json.loads(body)
                self.assertEqual(data['kind'], kind)
                self.assertIn('input', data)
                self.assertNotIn('result', data)
        status, body = self.request('POST', '/api/prepare', json.dumps({'name': 'q2_closest_pair_01_120.txt'}).encode())
        self.assertEqual(status, 200)
        self.assertEqual(len(json.loads(body)['input']['points']), 120)

    def test_requests(self):
        for path in ('/', '/q4_ui.js', '/api/files'):
            status, _ = self.request('GET', path)
            self.assertEqual(status, 200)
        status, body = self.request('GET', '/api/files')
        files = json.loads(body)['files']
        self.assertEqual(len(files), 20)
        for entry in files:
            status, body = self.request('GET', '/api/file?name=' + entry['name'])
            self.assertEqual(status, 200)
            self.assertEqual(json.loads(body)['kind'], entry['kind'])
        for name in ('q2_closest_pair_01_120.txt', 'q2_integer_multiplication_01_50.txt'):
            status, body = self.request('POST', '/api/run', json.dumps({'name': name}).encode())
            self.assertEqual(status, 200, body)
        cases = [(b'{' , 400), (b'[]', 400), (b'{"content":""}', 400),
                 (b'{"content":123}', 400), (b'{"name":null}', 400),
                 (b'{"name":"missing.txt"}', 404)]
        cases += [(json.dumps({'content': text}).encode(), 200)
                  for text in ('0\n1', '-12\n34', '2\n0 0\n3 4')]
        for payload, expected in cases:
            status, body = self.request('POST', '/api/run', payload)
            data = json.loads(body)
            self.assertEqual(status, expected, data)
            self.assertEqual(data['ok'], status == 200)


if __name__ == '__main__':
    unittest.main()
