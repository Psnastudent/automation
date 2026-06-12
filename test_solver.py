"""Quick test to verify the solver works end-to-end."""
import sys
sys.path.insert(0, ".")

from problem_solver import fix_python2_compat, extract_solution_class, ProblemSolver

# Test 1: Python 2 compat fixes
print("=== Test 1: Python 2 Compat Fixes ===")
code = (
    "import itertools\n"
    "class Helper:\n"
    "    pass\n"
    "class Solution:\n"
    "    def solve(self, nums):\n"
    "        for a,b in itertools.izip(nums, nums[1:]):\n"
    "            d = {}\n"
    "            for k,v in d.iteritems():\n"
    "                pass\n"
    "        return list(range(10))\n"
    'if __name__=="__main__":\n'
    "    pass\n"
)
fixed = fix_python2_compat(code)
extracted = extract_solution_class(fixed)
print(extracted)
assert "zip(" in extracted, "izip should be replaced with zip"
assert ".items()" in extracted, "iteritems should be replaced with items"
assert "Helper" not in extracted, "Helper class should be stripped"
assert '__name__' not in extracted, "if __name__ block should be stripped"
print("PASSED!\n")

# Test 2: Solver fetches from kamyu104
print("=== Test 2: Solver fetches Two Sum ===")
solver = ProblemSolver()
problem = {"titleSlug": "two-sum", "title": "Two Sum", "questionFrontendId": "1"}
code, lang = solver.solve(problem)
assert code is not None, "Should find a solution for Two Sum"
assert "class Solution" in code, "Should contain Solution class"
print(f"Language: {lang}, Code length: {len(code)}")
print("PASSED!\n")

# Test 3: Solver fetches from walkccc (by number)
print("=== Test 3: Solver gets multiple solutions ===")
problem = {"titleSlug": "add-two-numbers", "title": "Add Two Numbers", "questionFrontendId": "2"}
solutions = list(solver.get_all_solutions(problem))
print(f"Found {len(solutions)} solution(s)")
for code, lang in solutions:
    print(f"  - {lang}: {len(code)} chars")
assert len(solutions) >= 1, "Should find at least 1 solution"
print("PASSED!\n")

print("=== ALL TESTS PASSED ===")
