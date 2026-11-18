"""20 small coding problems. Each has a reference solution (the oracle), a random input
generator, a few *visible* examples (what a model sees) and hand-picked edge cases.
Hidden tests = edge cases + random inputs, with expected outputs computed by the reference."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


@dataclass
class Problem:
    name: str
    title: str
    doc: str
    signature: str
    ref: str
    gen: Callable
    visible: list
    edge: list
    alts: list = field(default_factory=list)


def _ints(rng, lo, hi, nmin, nmax):
    return [rng.randint(lo, hi) for _ in range(rng.randint(nmin, nmax))]


def _to_roman(n):
    out = ""
    for v, s in [(1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"), (50, "L"),
                 (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]:
        while n >= v:
            out += s
            n -= v
    return out


def _gen_two_sum(rng):
    return (_ints(rng, -5, 9, 0, 8), rng.randint(-6, 14))


def _gen_parens(rng):
    close = {"(": ")", "[": "]", "{": "}"}
    if rng.random() < 0.5:
        out, st = [], []
        for _ in range(rng.randint(0, 6)):
            if st and rng.random() < 0.5:
                out.append(close[st.pop()])
            else:
                c = rng.choice("([{")
                st.append(c)
                out.append(c)
        while st:
            out.append(close[st.pop()])
        return ("".join(out),)
    return ("".join(rng.choice("()[]{}a") for _ in range(rng.randint(0, 9))),)


def _sorted_list(rng):
    return sorted(_ints(rng, -3, 8, 0, 6))


def _gen_lcp(rng):
    base = "".join(rng.choice("ab") for _ in range(rng.randint(0, 4)))
    return ([base + "".join(rng.choice("abc") for _ in range(rng.randint(0, 3))) for _ in range(rng.randint(0, 4))],)


def _gen_nested(rng, depth=3):
    out = []
    for _ in range(rng.randint(0, 4)):
        if depth > 0 and rng.random() < 0.35:
            out.append(_gen_nested(rng, depth - 1))
        else:
            out.append(rng.randint(0, 9))
    return out


def _gen_matrix(rng):
    rows, cols = rng.randint(0, 4), rng.randint(1, 4)
    return ([[rng.randint(0, 9) for _ in range(cols)] for _ in range(rows)],)


def _gen_text(rng):
    words = ["the", "Cat", "dog", "don't", "A", "it's"]
    seps = [" ", ", ", ". ", "!", "  "]
    return ("".join(rng.choice(words) + rng.choice(seps) for _ in range(rng.randint(0, 6))),)


def _gen_year_month(rng):
    year = rng.choice([1900, 2000, 2023, 2024, 2100, 1996, 4, 100, 400, 2400, rng.randint(1, 2500)])
    return (year, rng.randint(1, 12))


def _gen_grid(rng):
    rows, cols = rng.randint(0, 4), rng.randint(1, 4)
    return ([[1 if rng.random() < 0.25 else 0 for _ in range(cols)] for _ in range(rows)],)


def _gen_rpn(rng):
    def build(d):
        if d == 0 or rng.random() < 0.3:
            v = rng.randint(-9, 9)
            return [str(v)], v
        lt, lv = build(d - 1)
        rt, rv = build(d - 1)
        op = rng.choice("+-*/")
        if op == "/" and rv == 0:
            op = "+"
        v = lv + rv if op == "+" else lv - rv if op == "-" else lv * rv if op == "*" else int(lv / rv)
        return lt + rt + [op], v
    return (build(rng.randint(0, 3))[0],)


PROBLEMS: list[Problem] = [
    Problem(
        "two_sum", "Two Sum (first pair)",
        "Return (i, j) with i < j and nums[i] + nums[j] == target, choosing the smallest i, then the smallest j. Return None if no pair exists.",
        "def solve(nums, target)",
        '''def solve(nums, target):
    for i in range(len(nums)):
        for j in range(i + 1, len(nums)):
            if nums[i] + nums[j] == target:
                return (i, j)
    return None
''',
        _gen_two_sum,
        [([2, 7, 11, 15], 9), ([3, 2, 4], 6), ([1, 2, 3], 10), ([3, 3], 6)],
        [([], 0), ([5], 5), ([0, 0], 0), ([-1, 1, 0], 0), ([1, 5, 1, 5], 6)],
    ),
    Problem(
        "valid_parens", "Balanced brackets",
        "Return True if the brackets ()[]{} in s are balanced and properly nested. Other characters are ignored.",
        "def solve(s)",
        '''def solve(s):
    pairs = {')': '(', ']': '[', '}': '{'}
    stack = []
    for ch in s:
        if ch in '([{':
            stack.append(ch)
        elif ch in pairs:
            if not stack or stack.pop() != pairs[ch]:
                return False
    return not stack
''',
        _gen_parens,
        [("()",), ("()[]{}",), ("(]",), ("{[]}",)],
        [("",), ("(",), (")",), ("a(b)c",), ("((",), ("([)]",), ("}{",)],
        ['''def solve(s):
    s = ''.join(c for c in s if c in '()[]{}')
    prev = None
    while prev != s:
        prev = s
        s = s.replace('()', '').replace('[]', '').replace('{}', '')
    return s == ''
'''],
    ),
    Problem(
        "roman_to_int", "Roman numerals",
        "Convert a valid Roman numeral string to an integer. The empty string is 0.",
        "def solve(s)",
        '''def solve(s):
    vals = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
    total = 0
    for i, ch in enumerate(s):
        v = vals[ch]
        if i + 1 < len(s) and vals[s[i + 1]] > v:
            total -= v
        else:
            total += v
    return total
''',
        lambda rng: (_to_roman(rng.randint(1, 3999)),),
        [("III",), ("IV",), ("IX",), ("LVIII",)],
        [("",), ("MCMXCIV",), ("MMMCMXCIX",), ("XLII",), ("CDXLIV",)],
        ['''def solve(s):
    vals = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
    total = 0
    prev = 0
    for ch in reversed(s):
        v = vals[ch]
        if v < prev:
            total -= v
        else:
            total += v
        prev = v
    return total
'''],
    ),
    Problem(
        "merge_sorted", "Merge two sorted lists",
        "Merge two ascending lists a and b into one ascending list.",
        "def solve(a, b)",
        '''def solve(a, b):
    i = j = 0
    out = []
    while i < len(a) and j < len(b):
        if a[i] <= b[j]:
            out.append(a[i])
            i += 1
        else:
            out.append(b[j])
            j += 1
    out.extend(a[i:])
    out.extend(b[j:])
    return out
''',
        lambda rng: (_sorted_list(rng), _sorted_list(rng)),
        [([1, 3, 5], [2, 4, 6]), ([], [1]), ([1, 2], [1, 2]), ([5], [1, 2, 3])],
        [([], []), ([1], []), ([2, 2], [2]), ([-3, 0], [-3, -1, 4])],
        ["def solve(a, b):\n    return sorted(a + b)\n"],
    ),
    Problem(
        "lcp", "Longest common prefix",
        "Return the longest common prefix of a list of strings. Return '' for an empty list.",
        "def solve(strs)",
        '''def solve(strs):
    if not strs:
        return ''
    prefix = strs[0]
    for s in strs[1:]:
        while not s.startswith(prefix):
            prefix = prefix[:-1]
    return prefix
''',
        _gen_lcp,
        [(["flower", "flow", "flight"],), (["dog", "car"],), (["a"],), (["ab", "ab"],)],
        [([],), ([""],), (["abc", "ab", "abcd"],), (["x", "xy", ""],)],
        ['''def solve(strs):
    out = []
    for chars in zip(*strs):
        if len(set(chars)) != 1:
            break
        out.append(chars[0])
    return ''.join(out)
'''],
    ),
    Problem(
        "flatten", "Flatten nested lists",
        "Flatten arbitrarily nested lists of integers into one flat list, preserving left-to-right order.",
        "def solve(nested)",
        '''def solve(nested):
    out = []
    for item in nested:
        if isinstance(item, list):
            out.extend(solve(item))
        else:
            out.append(item)
    return out
''',
        lambda rng: (_gen_nested(rng),),
        [([1, [2, 3], 4],), ([[1], [2, [3]]],), ([],), ([1, 2],)],
        [([[]],), ([[[[5]]]],), ([[], [[]], 1],)],
        ['''def solve(nested):
    out = []
    stack = [iter(nested)]
    while stack:
        for item in stack[-1]:
            if isinstance(item, list):
                stack.append(iter(item))
                break
            out.append(item)
        else:
            stack.pop()
    return out
'''],
    ),
    Problem(
        "second_largest", "Second largest distinct value",
        "Return the second largest distinct value in xs, or None if there are fewer than two distinct values.",
        "def solve(xs)",
        '''def solve(xs):
    distinct = sorted(set(xs))
    if len(distinct) < 2:
        return None
    return distinct[-2]
''',
        lambda rng: (_ints(rng, -5, 5, 0, 7),),
        [([3, 1, 2],), ([5, 5, 4],), ([7],), ([1, 2, 2],)],
        [([],), ([2, 2, 2],), ([-1, -2],), ([4, 4, 3, 3],)],
        ['''def solve(xs):
    first = second = None
    for x in xs:
        if first is None or x > first:
            if first is not None:
                second = first
            first = x
        elif x != first and (second is None or x > second):
            second = x
    return second
'''],
    ),
    Problem(
        "rotate90", "Rotate matrix 90 degrees",
        "Rotate a rectangular matrix (list of rows) 90 degrees clockwise and return the new matrix.",
        "def solve(m)",
        '''def solve(m):
    if not m:
        return []
    return [[m[r][c] for r in range(len(m) - 1, -1, -1)] for c in range(len(m[0]))]
''',
        _gen_matrix,
        [([[1, 2], [3, 4]],), ([[1, 2, 3]],), ([[1], [2], [3]],), ([[1, 2, 3], [4, 5, 6]],)],
        [([],), ([[7]],), ([[1, 2], [3, 4], [5, 6]],)],
        ["def solve(m):\n    return [list(r) for r in zip(*m[::-1])]\n"],
    ),
    Problem(
        "gcd_lcm", "GCD and LCM",
        "Return (gcd, lcm) of two positive integers as a tuple.",
        "def solve(a, b)",
        '''def solve(a, b):
    x, y = a, b
    while y:
        x, y = y, x % y
    return (x, a // x * b)
''',
        lambda rng: (rng.randint(1, 60), rng.randint(1, 60)),
        [(12, 18), (7, 5), (10, 10), (4, 8)],
        [(1, 1), (1, 97), (97, 1), (36, 48), (100, 75)],
        ["import math\n\n\ndef solve(a, b):\n    g = math.gcd(a, b)\n    return (g, a * b // g)\n"],
    ),
    Problem(
        "bisect_left", "Insertion index",
        "Return the index of the first element of the ascending list xs that is >= target (len(xs) if there is none).",
        "def solve(xs, target)",
        '''def solve(xs, target):
    lo, hi = 0, len(xs)
    while lo < hi:
        mid = (lo + hi) // 2
        if xs[mid] < target:
            lo = mid + 1
        else:
            hi = mid
    return lo
''',
        lambda rng: (_sorted_list(rng), rng.randint(-4, 9)),
        [([1, 3, 5, 7], 5), ([1, 3, 5, 7], 4), ([1, 3], 0), ([1, 3], 9)],
        [([], 1), ([2, 2, 2], 2), ([2, 2, 2], 3), ([2, 2, 2], 1), ([1, 2, 2, 3], 2)],
        ['''def solve(xs, target):
    for i, x in enumerate(xs):
        if x >= target:
            return i
    return len(xs)
'''],
    ),
    Problem(
        "word_freq", "Word frequencies",
        "Count words case-insensitively. A word is a run of letters and apostrophes. Return a dict mapping word to count.",
        "def solve(text)",
        '''def solve(text):
    counts = {}
    word = ''
    for ch in text.lower() + ' ':
        if ch.isalpha() or ch == "'":
            word += ch
        else:
            if word:
                counts[word] = counts.get(word, 0) + 1
            word = ''
    return counts
''',
        _gen_text,
        [("the cat the dog",), ("Hello, hello!",), ("",), ("don't stop",)],
        [("  ",), ("A a A",), ("it's it's, ok.",), ("a1b",)],
        ['''import re
from collections import Counter


def solve(text):
    return dict(Counter(re.findall(r"[a-z']+", text.lower())))
'''],
    ),
    Problem(
        "max_subarray", "Maximum subarray sum",
        "Return the maximum sum of a non-empty contiguous subarray of xs. Return 0 for an empty list.",
        "def solve(xs)",
        '''def solve(xs):
    if not xs:
        return 0
    best = cur = xs[0]
    for x in xs[1:]:
        cur = max(x, cur + x)
        best = max(best, cur)
    return best
''',
        lambda rng: (_ints(rng, -6, 6, 0, 8),),
        [([-2, 1, -3, 4, -1, 2, 1, -5, 4],), ([1],), ([5, 4, -1, 7, 8],), ([1, 2, 3],)],
        [([],), ([-3, -1, -2],), ([-1],), ([0, 0],), ([2, -1, 2],)],
        ['''def solve(xs):
    if not xs:
        return 0
    return max(sum(xs[i:j]) for i in range(len(xs)) for j in range(i + 1, len(xs) + 1))
'''],
    ),
    Problem(
        "collatz", "Collatz steps",
        "Return the number of steps to reach 1 when repeatedly applying: n even -> n/2, n odd -> 3n+1. n = 1 takes 0 steps.",
        "def solve(n)",
        '''def solve(n):
    steps = 0
    while n != 1:
        n = n // 2 if n % 2 == 0 else 3 * n + 1
        steps += 1
    return steps
''',
        lambda rng: (rng.randint(1, 60),),
        [(1,), (2,), (6,), (7,)],
        [(3,), (27,), (16,), (97,)],
        ['''def solve(n):
    if n == 1:
        return 0
    return 1 + solve(n // 2 if n % 2 == 0 else 3 * n + 1)
'''],
    ),
    Problem(
        "partition_equal", "Equal-sum partition",
        "Return True if the list of positive integers can be split into two groups with equal sums.",
        "def solve(xs)",
        '''def solve(xs):
    total = sum(xs)
    if total % 2:
        return False
    reachable = {0}
    for x in xs:
        reachable |= {r + x for r in reachable}
    return total // 2 in reachable
''',
        lambda rng: (_ints(rng, 1, 9, 0, 7),),
        [([1, 5, 11, 5],), ([1, 2, 3, 5],), ([2, 2],), ([1],)],
        [([],), ([3, 3, 3, 3],), ([1, 1, 1],), ([9, 1, 4, 4],)],
        ['''def solve(xs):
    total = sum(xs)
    if total % 2:
        return False
    target = total // 2
    return any(sum(x for k, x in enumerate(xs) if mask >> k & 1) == target for mask in range(1 << len(xs)))
'''],
    ),
    Problem(
        "pascal_row", "Pascal's triangle row",
        "Return row n (0-indexed) of Pascal's triangle as a list.",
        "def solve(n)",
        '''def solve(n):
    row = [1]
    for _ in range(n):
        row = [1] + [row[i] + row[i + 1] for i in range(len(row) - 1)] + [1]
    return row
''',
        lambda rng: (rng.randint(0, 12),),
        [(0,), (1,), (4,), (2,)],
        [(3,), (5,), (10,), (12,)],
        ["import math\n\n\ndef solve(n):\n    return [math.comb(n, k) for k in range(n + 1)]\n"],
    ),
    Problem(
        "days_in_month", "Days in a month",
        "Return the number of days in the given month (1-12) of the given year, using Gregorian leap-year rules.",
        "def solve(year, month)",
        '''def solve(year, month):
    if month == 2:
        leap = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
        return 29 if leap else 28
    return 30 if month in (4, 6, 9, 11) else 31
''',
        _gen_year_month,
        [(2023, 1), (2024, 2), (2023, 4), (2023, 2)],
        [(1900, 2), (2000, 2), (2100, 2), (2400, 2), (1999, 12), (2023, 11)],
        ["import calendar\n\n\ndef solve(year, month):\n    return calendar.monthrange(year, month)[1]\n"],
    ),
    Problem(
        "dedupe", "Remove duplicates",
        "Remove duplicates from xs, keeping the first occurrence of each value and preserving order.",
        "def solve(xs)",
        '''def solve(xs):
    seen = set()
    out = []
    for x in xs:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out
''',
        lambda rng: (_ints(rng, 0, 5, 0, 10),),
        [([1, 2, 1, 3],), ([1, 1, 1],), ([],), ([3, 2, 1],)],
        [([5, 4, 5, 4, 3],), ([0, 0, 1],), ([2],)],
        ["def solve(xs):\n    return list(dict.fromkeys(xs))\n"],
    ),
    Problem(
        "prime_factors", "Prime factorisation",
        "Return the prime factors of n (n >= 2) in ascending order, repeated by multiplicity.",
        "def solve(n)",
        '''def solve(n):
    factors = []
    d = 2
    while d * d <= n:
        while n % d == 0:
            factors.append(d)
            n //= d
        d += 1
    if n > 1:
        factors.append(n)
    return factors
''',
        lambda rng: (rng.randint(2, 400),),
        [(12,), (13,), (2,), (30,)],
        [(4,), (97,), (360,), (1024,), (49,)],
        ['''def solve(n):
    for d in range(2, int(n ** 0.5) + 1):
        if n % d == 0:
            return [d] + solve(n // d)
    return [n]
'''],
    ),
    Problem(
        "unique_paths", "Grid paths with obstacles",
        "Count paths from the top-left to the bottom-right cell moving only right or down. Cells equal to 1 are blocked. Return 0 for an empty grid or a blocked start or end.",
        "def solve(grid)",
        '''def solve(grid):
    if not grid or not grid[0] or grid[0][0] == 1 or grid[-1][-1] == 1:
        return 0
    rows, cols = len(grid), len(grid[0])
    ways = [[0] * cols for _ in range(rows)]
    ways[0][0] = 1
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == 1:
                ways[r][c] = 0
            elif r or c:
                ways[r][c] = (ways[r - 1][c] if r else 0) + (ways[r][c - 1] if c else 0)
    return ways[-1][-1]
''',
        _gen_grid,
        [([[0, 0], [0, 0]],), ([[0, 0, 0], [0, 1, 0], [0, 0, 0]],), ([[0]],), ([[0, 0, 0]],)],
        [([],), ([[0, 1], [0, 0]],), ([[0, 0], [1, 0]],), ([[0, 0], [0, 1]],), ([[0, 0, 0], [0, 0, 0], [0, 0, 0]],), ([[1]],)],
    ),
    Problem(
        "eval_rpn", "Reverse Polish notation",
        "Evaluate a reverse Polish expression given as a list of string tokens. Operators are + - * /. Division truncates toward zero. Return an int.",
        "def solve(tokens)",
        '''def solve(tokens):
    stack = []
    for tok in tokens:
        if tok in ('+', '-', '*', '/'):
            b = stack.pop()
            a = stack.pop()
            if tok == '+':
                stack.append(a + b)
            elif tok == '-':
                stack.append(a - b)
            elif tok == '*':
                stack.append(a * b)
            else:
                stack.append(int(a / b))
        else:
            stack.append(int(tok))
    return stack[0]
''',
        _gen_rpn,
        [(["2", "1", "+", "3", "*"],), (["4", "13", "5", "/", "+"],), (["7"],),
         (["5", "1", "2", "+", "4", "*", "+", "3", "-"],)],
        [(["7", "-2", "/"],), (["-7", "2", "/"],), (["3", "4", "-"],), (["0", "5", "*"],)],
    ),
]

BY_NAME = {p.name: p for p in PROBLEMS}
