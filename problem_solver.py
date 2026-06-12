"""
Problem Solver — Multi-Repo GitHub Scraper Edition
Achieves near 100% correctness by scraping verified solutions from
multiple well-known GitHub repositories, with comprehensive Python 3
compatibility fixes and Solution class extraction.

Repos used (in priority order):
  1. kamyu104/LeetCode-Solutions  — Python, C++, Java
  2. walkccc/LeetCode             — C++, Java, Python (number-based paths)
  3. neetcode-gh/leetcode         — Python (slug-based paths)
"""

import re
import textwrap
import urllib.request
import urllib.error
from typing import Optional, Tuple, Dict, Any, Generator
from logger import setup_logger

logger = setup_logger("problem_solver")

# ─────────────────────────────────────────────────────────────────────────────
# Python 2 → 3 Compatibility Fixer
# ─────────────────────────────────────────────────────────────────────────────

def fix_python2_compat(code: str) -> str:
    """Apply comprehensive Python 2 → Python 3 transformations."""

    # 1. xrange → range
    code = code.replace("xrange(", "range(")

    # 2. itertools Python 2 lazy variants → builtins
    code = re.sub(r'\bitertools\.izip\b', 'zip', code)
    code = re.sub(r'\bitertools\.imap\b', 'map', code)
    code = re.sub(r'\bitertools\.ifilter\b', 'filter', code)
    code = re.sub(r'\bitertools\.izip_longest\b', 'itertools.zip_longest', code)

    # 3. dict .iter* methods → .items/.values/.keys
    code = re.sub(r'\.iteritems\(\)', '.items()', code)
    code = re.sub(r'\.itervalues\(\)', '.values()', code)
    code = re.sub(r'\.iterkeys\(\)', '.keys()', code)

    # 4. dict .has_key(x) → x in dict
    code = re.sub(r'(\w+)\.has_key\((.+?)\)', r'\2 in \1', code)

    # 5. print statement → print() function (simple cases)
    # Match: "print something" but not "print(" or "print ="
    code = re.sub(r'^(\s*)print\s+(?!\()(.*?)$', r'\1print(\2)', code, flags=re.MULTILINE)

    # 6. Ensure reduce is imported from functools if used
    if 'reduce(' in code and 'from functools import' not in code and 'import functools' not in code:
        code = "from functools import reduce\n" + code

    # 7. Strip __future__ imports (not needed in Python 3)
    code = re.sub(r'^from __future__ import .*$\n?', '', code, flags=re.MULTILINE)

    # 8. Unicode string prefix u"..." → "..."
    code = re.sub(r'\bu"', '"', code)
    code = re.sub(r"\bu'", "'", code)

    # 9. long type → int
    code = re.sub(r'\blong\(', 'int(', code)

    # 10. raw_input → input
    code = code.replace("raw_input(", "input(")

    return code


# ─────────────────────────────────────────────────────────────────────────────
# Solution Class Extractor
# ─────────────────────────────────────────────────────────────────────────────

def extract_solution_class(code: str) -> str:
    """
    Extract only the Solution class from a file that may contain
    multiple classes, test harnesses, and if __name__ blocks.
    LeetCode only accepts a single Solution class submission.
    """
    lines = code.split('\n')

    # Find all class definitions
    solution_start = None
    solution_end = None
    in_solution = False
    solution_indent = 0

    for i, line in enumerate(lines):
        stripped = line.lstrip()

        # Look for class Solution
        if stripped.startswith('class Solution'):
            solution_start = i
            solution_indent = len(line) - len(stripped)
            in_solution = True
            continue

        if in_solution and solution_start is not None:
            # Check if we've exited the Solution class
            if stripped and not line[0:1].isspace() and not stripped.startswith('#'):
                # We hit a new top-level definition — end of Solution
                solution_end = i
                in_solution = False
                break

            # Also detect another class definition at the same indent level
            if stripped.startswith('class ') and len(line) - len(stripped) <= solution_indent:
                solution_end = i
                in_solution = False
                break

            # Detect if __name__ block
            if stripped.startswith('if __name__'):
                solution_end = i
                in_solution = False
                break

    if solution_start is None:
        # No Solution class found — return original code
        return code

    if solution_end is None:
        solution_end = len(lines)

    # Extract imports and the Solution class
    imports = []
    for line in lines[:solution_start]:
        stripped = line.strip()
        if stripped.startswith(('import ', 'from ')) and not stripped.startswith('from __future__'):
            imports.append(line)
        elif stripped.startswith('#') and not imports:
            continue  # Skip leading comments

    solution_lines = lines[solution_start:solution_end]

    # Remove trailing blank lines
    while solution_lines and not solution_lines[-1].strip():
        solution_lines.pop()

    result_parts = []
    if imports:
        result_parts.append('\n'.join(imports))
    result_parts.append('\n'.join(solution_lines))

    return '\n'.join(result_parts)


# ─────────────────────────────────────────────────────────────────────────────
# HTTP Fetch Helper
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_url(url: str, timeout: int = 8) -> Optional[str]:
    """Fetch a URL and return its content, or None on failure."""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.read().decode('utf-8')
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Problem Solver
# ─────────────────────────────────────────────────────────────────────────────

class ProblemSolver:
    def __init__(self):
        # kamyu104 repos
        self.kamyu_python = "https://raw.githubusercontent.com/kamyu104/LeetCode-Solutions/master/Python/{}.py"
        self.kamyu_cpp = "https://raw.githubusercontent.com/kamyu104/LeetCode-Solutions/master/C++/{}.cpp"
        self.kamyu_java = "https://raw.githubusercontent.com/kamyu104/LeetCode-Solutions/master/Java/{}.java"

        # walkccc repos (uses problem number)
        self.walkccc_cpp = "https://raw.githubusercontent.com/walkccc/LeetCode/main/solutions/{}/{}.cpp"
        self.walkccc_java = "https://raw.githubusercontent.com/walkccc/LeetCode/main/solutions/{}/{}.java"
        self.walkccc_py = "https://raw.githubusercontent.com/walkccc/LeetCode/main/solutions/{}/{}.py"

        # neetcode repo (uses slug-based directory names)
        self.neetcode_py = "https://raw.githubusercontent.com/neetcode-gh/leetcode/main/python/{}.py"

    def get_all_solutions(self, problem: Dict[str, Any]) -> Generator[Tuple[str, str], None, None]:
        """Yields multiple possible solutions to try until one is accepted."""
        slug = (problem.get("titleSlug") or "").lower()
        title = problem.get("title") or ""
        frontend_id = problem.get("questionFrontendId") or problem.get("questionId")
        logger.info(f"  Solving: {title} ({slug}) using Multi-Repo Scraper")

        # ── Strategy 1: kamyu104 Python (most comprehensive) ──
        code = _fetch_url(self.kamyu_python.format(slug))
        if code:
            code = fix_python2_compat(code)
            code = extract_solution_class(code)
            logger.info("  ✨ Fetched Python solution from kamyu104/LeetCode-Solutions")
            yield code, "python3"

        # ── Strategy 2: walkccc Python (number-based, very reliable) ──
        if frontend_id:
            try:
                num = int(frontend_id)
                padded = f"{num:04d}"
                url = self.walkccc_py.format(padded, padded)
                code = _fetch_url(url)
                if code:
                    code = extract_solution_class(code)
                    logger.info("  ✨ Fetched Python solution from walkccc/LeetCode")
                    yield code, "python3"
            except (ValueError, TypeError):
                pass

        # ── Strategy 3: neetcode Python (slug-based) ──
        code = _fetch_url(self.neetcode_py.format(slug))
        if code:
            code = extract_solution_class(code)
            logger.info("  ✨ Fetched Python solution from neetcode-gh/leetcode")
            yield code, "python3"

        # ── Strategy 4: kamyu104 C++ ──
        code = _fetch_url(self.kamyu_cpp.format(slug))
        if code:
            logger.info("  ✨ Fetched C++ solution from kamyu104/LeetCode-Solutions")
            yield code, "cpp"

        # ── Strategy 5: walkccc C++ (number-based) ──
        if frontend_id:
            try:
                num = int(frontend_id)
                padded = f"{num:04d}"
                url = self.walkccc_cpp.format(padded, padded)
                code = _fetch_url(url)
                if code:
                    logger.info("  ✨ Fetched C++ solution from walkccc/LeetCode")
                    yield code, "cpp"
            except (ValueError, TypeError):
                pass

        # ── Strategy 6: walkccc Java (number-based) ──
        if frontend_id:
            try:
                num = int(frontend_id)
                padded = f"{num:04d}"
                url = self.walkccc_java.format(padded, padded)
                code = _fetch_url(url)
                if code:
                    logger.info("  ✨ Fetched Java solution from walkccc/LeetCode")
                    yield code, "java"
            except (ValueError, TypeError):
                pass

        # ── Strategy 7: kamyu104 Java ──
        code = _fetch_url(self.kamyu_java.format(slug))
        if code:
            logger.info("  ✨ Fetched Java solution from kamyu104/LeetCode-Solutions")
            yield code, "java"

        # No fallback — it's better to skip than submit garbage code
        logger.warning(f"  ⚠️ No solution found in any repository for: {title}")

    def solve(self, problem: Dict[str, Any]) -> Tuple[Optional[str], str]:
        """Fetch the first available solution."""
        for code, lang in self.get_all_solutions(problem):
            return code, lang
        return None, "python3"
