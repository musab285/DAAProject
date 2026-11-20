BASE = 10 ** 9


def normalize_integer(text):
    s = str(text).strip()
    sign = "-" if s.startswith("-") else ""
    digits = s[1:] if s.startswith(("-", "+")) else s
    if not digits or any(c not in "0123456789" for c in digits):
        raise ValueError("expected a decimal integer")
    digits = digits.lstrip("0") or "0"
    return sign + digits if digits != "0" else "0"


def _to_limbs(text):
    s = normalize_integer(text).lstrip("-")
    limbs = []
    for i in range(len(s), 0, -9):
        limbs.append(int(s[max(0, i - 9):i]))
    return limbs or [0]


def _to_str(limbs):
    limbs = _trim(limbs)
    out = [str(limbs[-1])]
    for v in reversed(limbs[:-1]):
        out.append(str(v).rjust(9, "0"))
    return "".join(out)


def _trim(a):
    i = len(a) - 1
    while i > 0 and a[i] == 0:
        i -= 1
    return a[:i + 1]


def _add(a, b):
    n = max(len(a), len(b))
    out = [0] * (n + 1)
    carry = 0
    for i in range(n):
        s = (a[i] if i < len(a) else 0) + (b[i] if i < len(b) else 0) + carry
        out[i] = s % BASE
        carry = s // BASE
    out[n] = carry
    return _trim(out)


def _sub(a, b):
    out = [0] * len(a)
    borrow = 0
    for i in range(len(a)):
        s = a[i] - (b[i] if i < len(b) else 0) - borrow
        if s < 0:
            s += BASE
            borrow = 1
        else:
            borrow = 0
        out[i] = s
    return _trim(out)


def _shift(a, m):
    return [0] * m + a if a != [0] else [0]


def _schoolbook(a, b):
    a, b = _trim(a), _trim(b)
    if a == [0] or b == [0]:
        return [0]
    out = [0] * (len(a) + len(b))
    for i, ai in enumerate(a):
        carry = 0
        for j, bj in enumerate(b):
            cur = out[i + j] + ai * bj + carry
            out[i + j] = cur % BASE
            carry = cur // BASE
        k = i + len(b)
        while carry:
            cur = out[k] + carry
            out[k] = cur % BASE
            carry = cur // BASE
            k += 1
    return _trim(out)


def _karatsuba(a, b, m, nodes, depth, on_step=None):
    def emit(kind, **values):
        if on_step:
            on_step(dict(kind=kind, depth=depth, **values))
    a, b = _trim(a), _trim(b)
    nodes.append({"depth": depth, "size": max(len(a), len(b)), "m": max(len(a), len(b)) // 2 if min(len(a), len(b)) > m else None})
    if min(len(a), len(b)) <= m:
        result = _schoolbook(a, b)
        emit("multiply", a=a, b=b, product=result)
        return result

    half = max(len(a), len(b)) // 2
    a1, a0 = (a[half:], a[:half]) if len(a) > half else ([0], a)
    b1, b0 = (b[half:], b[:half]) if len(b) > half else ([0], b)

    emit("split", a=a, b=b, a1=a1, a0=a0, b1=b1, b0=b0, half=half)
    z2 = _karatsuba(a1, b1, m, nodes, depth + 1, on_step)
    emit("z2", value=z2)
    z0 = _karatsuba(a0, b0, m, nodes, depth + 1, on_step)
    emit("z0", value=z0)
    z1 = _karatsuba(_add(a1, a0), _add(b1, b0), m, nodes, depth + 1, on_step)
    emit("sum_product", value=z1)
    z1 = _sub(_sub(z1, z2), z0)
    emit("z1", value=z1)

    result = _trim(_add(_add(_shift(z2, 2 * half), _shift(z1, half)), z0))
    emit("combine", z2=z2, z1=z1, z0=z0, half=half, product=result)
    return result


def karatsuba_mul(a, b, threshold=16, trace=False, on_step=None):
    if isinstance(threshold, bool) or not isinstance(threshold, int) or threshold < 1:
        raise ValueError("threshold must be a positive integer")
    a, b = normalize_integer(a), normalize_integer(b)
    nodes = []
    product = _karatsuba(_to_limbs(a), _to_limbs(b), threshold, nodes, 0, on_step)
    out = _to_str(product)
    if out != "0" and (a.startswith("-") != b.startswith("-")):
        out = "-" + out
    if trace:
        return out, nodes
    return out


def schoolbook_mul(a, b):
    a, b = normalize_integer(a), normalize_integer(b)
    out = _to_str(_schoolbook(_to_limbs(a), _to_limbs(b)))
    return "-" + out if out != "0" and (a.startswith("-") != b.startswith("-")) else out
