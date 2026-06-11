"""
LeetCode API Client
Handles authentication via session cookie + Cloudflare bypass,
problem fetching, and solution submission via LeetCode's GraphQL API.
"""

import json
import time
import random
import requests
from typing import Optional, Dict, List, Any
from logger import setup_logger

logger = setup_logger("leetcode_client")

LEETCODE_BASE = "https://leetcode.com"
GRAPHQL_URL   = f"{LEETCODE_BASE}/graphql"


class LeetCodeClient:
    def __init__(self, config: Dict):
        self.username       = config.get("username", "")
        self.password       = config.get("password", "")
        self.session_cookie = config.get("session_cookie", "")
        self.csrf_token     = config.get("csrf_token", "")
        self.cf_clearance   = config.get("cf_clearance", "")

        self.session = requests.Session()
        self._solved_today: List[str] = []

    # ─────────────────────────────────────────────────────────────────────────
    # Authentication
    # ─────────────────────────────────────────────────────────────────────────

    def login(self) -> bool:
        """Inject all LeetCode session cookies to bypass Cloudflare."""
        domain = "leetcode.com"

        logger.info("  Injecting LeetCode session cookies...")
        if self.session_cookie:
            self.session.cookies.set("LEETCODE_SESSION", self.session_cookie, domain=domain)
        if self.csrf_token:
            self.session.cookies.set("csrftoken", self.csrf_token, domain=domain)
        if self.cf_clearance:
            self.session.cookies.set("cf_clearance", self.cf_clearance, domain=domain)

        # Set real browser headers to pass Cloudflare checks
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            "Accept":          "application/json, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Content-Type":    "application/json",
            "Referer":         "https://leetcode.com/",
            "Origin":          "https://leetcode.com",
            "x-csrftoken":     self.csrf_token,
        })

        if self._verify_login():
            logger.info("  Logged in successfully!")
            return True

        logger.error("  Cookie login failed — session may have expired.")
        return False

    def _verify_login(self) -> bool:
        """Verify authentication by querying user profile."""
        query = """
        query globalData {
            userStatus {
                isSignedIn
                username
            }
        }
        """
        try:
            resp = self._graphql(query)
            status = resp.get("data", {}).get("userStatus", {})
            if status.get("isSignedIn"):
                logger.info(f"  Confirmed logged in as: {status.get('username')}")
                return True
            return False
        except Exception as e:
            logger.warning(f"  Verify login error: {e}")
            return False

    def _save_session_cookie(self, cookie: str):
        """Persist new session cookie back to config.json."""
        try:
            import os
            config_path = os.path.join(os.path.dirname(__file__), "config.json")
            with open(config_path) as f:
                cfg = json.load(f)
            cfg["leetcode"]["session_cookie"] = cookie
            with open(config_path, "w") as f:
                json.dump(cfg, f, indent=2)
            logger.info("  Session cookie refreshed and saved.")
        except Exception as e:
            logger.warning(f"  Could not save session cookie: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # Problem Discovery
    # ─────────────────────────────────────────────────────────────────────────

    def get_daily_challenge(self) -> Optional[Dict]:
        """Fetch today's daily challenge problem."""
        query = """
        query questionOfToday {
            activeDailyCodingChallengeQuestion {
                date
                userStatus
                link
                question {
                    acRate
                    difficulty
                    title
                    titleSlug
                    topicTags { name }
                    hasSolution
                }
            }
        }
        """
        try:
            resp = self._graphql(query)
            active_daily = resp.get("data", {}).get("activeDailyCodingChallengeQuestion", {})
            if active_daily.get("userStatus") == "Finish":
                logger.info("  👉 Daily Challenge is already finished! Skipping and substituting with a common problem.")
                return None
            return active_daily.get("question")
        except Exception as e:
            logger.warning(f"  Could not fetch daily challenge: {e}")
            return None

    def select_daily_problems(
        self,
        count: int,
        difficulty_mix: List[str],
        topics: List[str],
        daily_challenge: Optional[Dict] = None
    ) -> List[Dict]:
        """Select `count` problems based on difficulty mix."""
        problems = []

        # Always include daily challenge first
        if daily_challenge:
            problems.append(daily_challenge)
            count -= 1

        # Count how many of each difficulty we need
        difficulty_counts: Dict[str, int] = {}
        for diff in difficulty_mix[:count]:
            difficulty_counts[diff] = difficulty_counts.get(diff, 0) + 1

        for difficulty, needed in difficulty_counts.items():
            fetched = self._fetch_problems_by_difficulty(difficulty, limit=needed * 5)
            random.shuffle(fetched)
            added = 0
            for p in fetched:
                if added >= needed:
                    break
                slug = p.get("titleSlug", "")
                if slug not in [x.get("titleSlug") for x in problems]:
                    problems.append(p)
                    added += 1

        return problems[:10]  # Safety cap

    def _fetch_problems_by_difficulty(self, difficulty: str, limit: int = 20) -> List[Dict]:
        """Fetch problems filtered by difficulty."""
        query = """
        query problemsetQuestionList($filters: QuestionListFilterInput, $limit: Int, $skip: Int) {
            problemsetQuestionList: questionList(
                categorySlug: "all-code-essentials"
                limit: $limit
                skip: $skip
                filters: $filters
            ) {
                total: totalNum
                questions: data {
                    acRate
                    difficulty
                    title
                    titleSlug
                    topicTags { name }
                    status
                }
            }
        }
        """
        skip = random.randint(0, 200)
        variables = {
            "filters": {"difficulty": difficulty.upper()},
            "limit":   limit,
            "skip":    skip,
        }
        try:
            resp = self._graphql(query, variables)
            questions = (
                resp.get("data", {})
                    .get("problemsetQuestionList", {})
                    .get("questions", [])
            )
            return [q for q in questions if q.get("status") != "ac"]
        except Exception as e:
            logger.warning(f"  Could not fetch {difficulty} problems: {e}")
            return []

    def get_problem_detail(self, slug: str) -> Optional[Dict]:
        """Fetch full problem details including description and code snippets."""
        query = """
        query questionData($titleSlug: String!) {
            question(titleSlug: $titleSlug) {
                questionId
                title
                titleSlug
                content
                difficulty
                topicTags { name }
                codeSnippets {
                    lang
                    langSlug
                    code
                }
                sampleTestCase
                exampleTestcases
                metaData
            }
        }
        """
        try:
            resp = self._graphql(query, {"titleSlug": slug})
            return resp.get("data", {}).get("question")
        except Exception as e:
            logger.warning(f"  Could not fetch problem detail for {slug}: {e}")
            return None

    # ─────────────────────────────────────────────────────────────────────────
    # Submission
    # ─────────────────────────────────────────────────────────────────────────

    def submit_solution(self, slug: str, code: str, language: str) -> Optional[Dict]:
        """Submit a solution and poll for the result."""
        submit_url = f"{LEETCODE_BASE}/problems/{slug}/submit/"

        # Refresh csrf from cookies
        csrf = self.session.cookies.get("csrftoken", self.csrf_token)
        self.session.headers["x-csrftoken"] = csrf

        detail = self.get_problem_detail(slug)
        if not detail:
            return None
        question_id = detail.get("questionId")

        payload = {
            "lang":        language,
            "question_id": question_id,
            "typed_code":  code,
        }

        try:
            resp = self.session.post(submit_url, json=payload, timeout=20)
            if resp.status_code != 200:
                logger.warning(f"  Submission HTTP {resp.status_code}")
                return None

            submission_id = resp.json().get("submission_id")
            if not submission_id:
                return None

            logger.info(f"  Submission #{submission_id} — waiting for result...")
            return self._poll_submission(submission_id)

        except Exception as e:
            logger.error(f"  Submission error: {e}")
            return None

    def _poll_submission(self, submission_id: int, max_wait: int = 30) -> Optional[Dict]:
        """Poll submission result until ready."""
        check_url = f"{LEETCODE_BASE}/submissions/detail/{submission_id}/check/"
        for attempt in range(max_wait):
            try:
                resp = self.session.get(check_url, timeout=10)
                data = resp.json()
                state = data.get("state", "")
                if state == "SUCCESS":
                    return data
                elif state in ("PENDING", "STARTED", ""):
                    time.sleep(1)
                else:
                    return data
            except Exception as e:
                logger.warning(f"  Poll attempt {attempt + 1} failed: {e}")
                time.sleep(1)
        return None

    # ─────────────────────────────────────────────────────────────────────────
    # GraphQL Helper
    # ─────────────────────────────────────────────────────────────────────────

    def _graphql(self, query: str, variables: Dict = None) -> Dict:
        """Execute a GraphQL query against LeetCode."""
        payload: Dict[str, Any] = {"query": query}
        if variables:
            payload["variables"] = variables
        resp = self.session.post(GRAPHQL_URL, json=payload, timeout=15)
        resp.raise_for_status()
        return resp.json()
