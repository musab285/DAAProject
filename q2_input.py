"""Strict parsers shared by the command-line runner and web interface."""
from q2_closest_pair import _points
from q2_karatsuba import normalize_integer


def read_points(text):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    expected = None
    if lines and len(lines[0].split()) == 1:
        try:
            expected = int(lines.pop(0))
        except ValueError:
            raise ValueError("point count must be an integer") from None
    points = []
    for line in lines:
        parts = line.split()
        if len(parts) != 2:
            raise ValueError("each point must contain exactly two coordinates")
        points.append(tuple(map(float, parts)))
    if expected is not None and expected != len(points):
        raise ValueError("point count does not match the header")
    return _points(points)


def read_numbers(text):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) != 2:
        raise ValueError("need exactly two lines with one integer each")
    return tuple(normalize_integer(line) for line in lines)
