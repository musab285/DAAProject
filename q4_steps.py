"""Readable playback events collected from the running algorithms."""
from q2_karatsuba import _to_str


def number(limbs):
    text = _to_str(limbs)
    return text if len(text) <= 90 else f"{text[:45]}…{text[-20:]} ({len(text)} digits)"


class Steps:
    def __init__(self, points=None):
        self.points = points
        self.steps = []
        self.omitted = 0

    def __call__(self, event):
        depth, kind = event['depth'], event['kind']
        if depth > 2 or (len(self.steps) >= 110 and depth != 0):
            self.omitted += 1
            return
        step = dict(event)
        step['title'] = kind.replace('_', ' ').title()
        step['boxes'], step['splits'] = [], []
        if self.points is not None:
            pts = self.points[event['lo']:event['hi']]
            step['boxes'] = [[min(x for x, _ in pts), min(y for _, y in pts),
                              max(x for x, _ in pts), max(y for _, y in pts)]]
            if kind == 'split':
                step['splits'] = [event['mid_x']]
                lines = [f"Split {len(pts)} points at x = {event['mid_x']:.6g}.",
                         f"Solve the left {event['left']} points, then the right {event['right']} points."]
            elif kind == 'base':
                lines = [f"Base case: compare pairs within these {len(pts)} points."]
            elif kind == 'compare':
                a, b = event['pair']
                lines = [f"Compare {a} with {b}.",
                         f"distance = hypot({a[0] - b[0]:.6g}, {a[1] - b[1]:.6g}) = {event['distance']:.6g}",
                         f"Best distance in this comparison loop = {event['best']:.6g}."]
            elif kind == 'merge':
                lines = [f"Left result: {event['left_distance']}; right result: {event['right_distance']}.",
                         "Keep the smaller distance, then check across the dividing line."]
            elif kind == 'strip':
                step['splits'] = [event['mid_x']]
                lines = [f"Check {event['size']} points within distance {event['width']:.6g} of the split.",
                         "Compare nearby points in y order to find a pair crossing the split."]
            else:
                lines = [f"Return the best pair for these {len(pts)} points.",
                         f"Distance: {event['distance']}."]
        else:
            # Only decimal strings are sent to the browser, preserving large integers.
            for key, value in list(step.items()):
                if key in ('a', 'b', 'a1', 'a0', 'b1', 'b0', 'value', 'z2', 'z1', 'z0', 'product'):
                    step[key] = number(value)
            if kind == 'split':
                h = event['half'] * 9
                lines = [f"a = {step['a']}", f"b = {step['b']}",
                         f"Split at {h} decimal digits: a = a₁ × 10^{h} + a₀; b = b₁ × 10^{h} + b₀.",
                         f"a₁ = {step['a1']}; a₀ = {step['a0']}",
                         f"b₁ = {step['b1']}; b₀ = {step['b0']}"]
            elif kind == 'multiply':
                lines = ["Base case: use ordinary multiplication.",
                         f"{step['a']} × {step['b']} = {step['product']}"]
            elif kind == 'combine':
                h = event['half'] * 9
                lines = [f"Combine: z₂ × 10^{2*h} + z₁ × 10^{h} + z₀",
                         f"z₂ = {step['z2']}", f"z₁ = {step['z1']}", f"z₀ = {step['z0']}",
                         f"Subproblem product = {step['product']}"]
            else:
                formulas = {'z2': 'z₂ = a₁ × b₁', 'z0': 'z₀ = a₀ × b₀',
                            'sum_product': 's = (a₁ + a₀) × (b₁ + b₀)', 'z1': 'z₁ = s − z₂ − z₀'}
                lines = [formulas[kind], f"Result = {step['value']}"]
        step['lines'] = lines
        self.steps.append(step)

    def finish(self, lines):
        if self.omitted:
            self.steps.append(dict(kind='summary', title='Recursion summary', depth=0,
                                   boxes=[], splits=[], lines=[
                                       f"{self.omitted} additional operations were computed but grouped to keep playback short.",
                                       "Deeper calls return their results to the parent steps shown here."]))
        self.steps.append(dict(kind='answer', title='Final answer', depth=0,
                               boxes=[], splits=[], lines=lines))
        return self.steps
