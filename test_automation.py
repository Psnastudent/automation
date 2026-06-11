"""
Test Suite - Verify automation components work correctly
Run: python test_automation.py
"""

import json
import sys
from pathlib import Path

def test_config():
    """Test config file is valid."""
    print("Testing config.json...")
    try:
        with open("config.json") as f:
            cfg = json.load(f)
        assert "leetcode" in cfg
        assert "email" in cfg
        assert "automation" in cfg
        print("  ✅ config.json is valid")
        return cfg
    except Exception as e:
        print(f"  ❌ config.json error: {e}")
        return None


def test_email(cfg):
    """Test email sending."""
    print("\nTesting email configuration...")
    from email_reporter import EmailReporter
    from datetime import datetime

    reporter = EmailReporter(cfg["email"])
    test_results = [
        {"title": "Two Sum", "difficulty": "Easy", "status": "ACCEPTED", "runtime": "48ms", "memory": "16.5MB", "language": "python3", "code": "# test"},
        {"title": "Climbing Stairs", "difficulty": "Easy", "status": "ACCEPTED", "runtime": "32ms", "memory": "14.2MB", "language": "python3", "code": "# test"},
        {"title": "Longest Palindrome", "difficulty": "Medium", "status": "Wrong Answer", "language": "python3"},
    ]
    try:
        reporter.send_daily_report(test_results, datetime.now())
        print(f"  ✅ Test email sent to {cfg['email']['receiver_email']}")
        print(f"     Check your inbox!")
    except Exception as e:
        print(f"  ❌ Email failed: {e}")
        print(f"     Hint: Use Gmail App Password, not your regular password")


def test_solver():
    """Test the problem solver."""
    print("\nTesting problem solver...")
    from problem_solver import ProblemSolver

    solver = ProblemSolver()
    test_problem = {
        "title": "Two Sum",
        "titleSlug": "two-sum",
        "difficulty": "Easy",
        "content": "<p>Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target.</p>",
        "codeSnippets": [
            {"lang": "Python3", "langSlug": "python3", "code": "class Solution:\n    def twoSum(self, nums: List[int], target: int) -> List[int]:"}
        ],
        "metaData": '{"params":[{"name":"nums","type":"integer[]"},{"name":"target","type":"integer"}],"return":{"type":"integer[]"}}',
        "sampleTestCase": "[2,7,11,15]\n9"
    }

    code, lang = solver.solve(test_problem)
    if code:
        print(f"  ✅ Solver generated {lang} solution:")
        print(f"     {code[:80]}...")
    else:
        print("  ❌ Solver returned no solution")


def main():
    print("=" * 50)
    print("  LeetCode Automation - Test Suite")
    print("=" * 50)
    print()

    cfg = test_config()
    if not cfg:
        sys.exit(1)

    test_solver()

    # Only test email if credentials are configured
    if (cfg["email"]["sender_email"] != "YOUR_GMAIL@gmail.com" and
            cfg["email"]["sender_password"] != "YOUR_APP_PASSWORD"):
        test_email(cfg)
    else:
        print("\n⚠️  Skipping email test — please update config.json with real credentials first")

    print("\n" + "=" * 50)
    print("  Tests Complete!")
    print("=" * 50)


if __name__ == "__main__":
    main()
