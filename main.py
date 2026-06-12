"""
LeetCode Automation - Main Runner
Automatically logs into LeetCode, fetches daily problems,
solves them using AI solutions, submits, and sends email reports.
"""

import json
import time
import schedule
import threading
from datetime import datetime, timedelta
from pathlib import Path

from leetcode_client import LeetCodeClient
from problem_solver import ProblemSolver
from email_reporter import EmailReporter
from logger import setup_logger

logger = setup_logger("main")

# Load configuration
config_path = Path(__file__).parent / "config.json"
with open(config_path) as f:
    CONFIG = json.load(f)


def run_daily_automation():
    """Main automation function — runs every day at scheduled time."""
    logger.info(f"{'='*60}")
    logger.info(f"  LeetCode Daily Automation Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"{'='*60}")

    results = []
    client = LeetCodeClient(CONFIG["leetcode"])
    solver = ProblemSolver()
    reporter = EmailReporter(CONFIG["email"])

    try:
        # Step 1: Login to LeetCode
        logger.info("🔐 Logging into LeetCode...")
        if not client.login():
            logger.error("❌ Login failed! Aborting.")
            reporter.send_failure_email("Login to LeetCode failed.")
            return

        logger.info("✅ Login successful!")

        # Step 2: Fetch daily challenge problem
        logger.info("📥 Fetching today's daily challenge problem...")
        daily_problem = client.get_daily_challenge()
        if daily_problem:
            logger.info(f"  📌 Daily Challenge: {daily_problem['title']}")

        # Step 3: Fetch additional problems by difficulty mix
        logger.info("📋 Selecting problems for today's session...")
        difficulty_mix = CONFIG["automation"]["difficulty_mix"]
        problems_per_day = CONFIG["automation"]["problems_per_day"]
        topics = CONFIG["automation"]["topics"]

        selected_problems = client.select_daily_problems(
            count=problems_per_day,
            difficulty_mix=difficulty_mix,
            topics=topics,
            daily_challenge=daily_problem
        )

        logger.info(f"  ✅ Selected {len(selected_problems)} problems for today")

        # Step 4: Solve each problem and submit
        for i, problem in enumerate(selected_problems, 1):
            logger.info(f"\n{'─'*50}")
            logger.info(f"  Problem {i}/{len(selected_problems)}: {problem['title']}")
            logger.info(f"  Difficulty: {problem['difficulty']} | Slug: {problem['titleSlug']}")

            # Fetch full problem details (description + examples)
            logger.info("  📖 Fetching full problem details...")
            problem_detail = client.get_problem_detail(problem["titleSlug"])

            if not problem_detail:
                logger.warning(f"  ⚠️ Could not fetch details for {problem['title']}. Skipping.")
                results.append({
                    "title": problem["title"],
                    "status": "SKIPPED",
                    "reason": "Could not fetch problem details"
                })
                continue

            # Skip non-code problems (SQL, Shell, etc.)
            code_snippets = problem_detail.get("codeSnippets") or []
            has_python = any(s.get("langSlug") == "python3" for s in code_snippets)
            has_cpp = any(s.get("langSlug") == "cpp" for s in code_snippets)
            has_java = any(s.get("langSlug") == "java" for s in code_snippets)
            if not (has_python or has_cpp or has_java):
                logger.warning(f"  ⚠️ {problem['title']} is a non-code problem (SQL/Shell). Skipping.")
                results.append({
                    "title": problem["title"],
                    "status": "SKIPPED",
                    "reason": "Non-code problem (SQL/Shell)"
                })
                continue

            # Skip premium/locked problems with no content
            if problem_detail.get("content") is None:
                logger.warning(f"  ⚠️ {problem['title']} appears to be a premium/locked problem. Skipping.")
                results.append({
                    "title": problem["title"],
                    "status": "SKIPPED",
                    "reason": "Premium/locked problem"
                })
                continue

            # Generate solution using AI solver
            logger.info("  🤖 Generating solution...")
            accepted = False
            last_status = "Submission Error"
            last_solution_code = None
            last_language = None

            for solution_code, language in solver.get_all_solutions(problem_detail):
                last_solution_code = solution_code
                last_language = language

                logger.info(f"  ✅ Solution generated in {language}")
                logger.info("  🚀 Submitting solution...")
                
                submission_result = client.submit_solution(
                    slug=problem["titleSlug"],
                    code=solution_code,
                    language=language
                )

                if submission_result and submission_result.get("status_msg") == "Accepted":
                    runtime = submission_result.get("status_runtime", "N/A")
                    memory = submission_result.get("status_memory", "N/A")
                    logger.info(f"  🎉 ACCEPTED! Runtime: {runtime} | Memory: {memory}")
                    # If this wasn't the first try, print the alternative message for dashboard
                    if last_status != "Submission Error":
                        logger.info("  🎉 Alternative solution ACCEPTED!")
                        
                    results.append({
                        "title": problem["title"],
                        "difficulty": problem["difficulty"],
                        "status": "ACCEPTED",
                        "runtime": runtime,
                        "memory": memory,
                        "language": language,
                        "code": solution_code
                    })
                    accepted = True
                    break
                else:
                    status = submission_result.get("status_msg", "Unknown") if submission_result else "Submission Error"
                    last_status = status
                    logger.warning(f"  ❌ Submission result: {status}")
                    logger.info("  🔄 Trying alternative solution...")
                    time.sleep(15) # Longer delay before retry to avoid rate limits

            if not accepted:
                if last_solution_code is None:
                    logger.warning(f"  ⚠️ Could not generate solution for {problem['title']}")
                    results.append({
                        "title": problem["title"],
                        "status": "FAILED",
                        "reason": "Solution generation failed"
                    })
                else:
                    results.append({
                        "title": problem["title"],
                        "difficulty": problem["difficulty"],
                        "status": last_status,
                        "language": last_language,
                        "code": last_solution_code
                    })

            # Polite delay between problems (avoid 429 rate limit)
            time.sleep(15)

        # Step 5: Send email report
        logger.info(f"\n{'='*60}")
        logger.info("📧 Sending email report...")
        accepted = sum(1 for r in results if "ACCEPTED" in r.get("status", ""))
        logger.info(f"  Summary: {accepted}/{len(results)} problems accepted")
        if reporter.send_daily_report(results, date=datetime.now()):
            logger.info("  ✅ Email sent successfully!")
        else:
            logger.error("  ❌ Failed to send email report.")

    except Exception as e:
        logger.error(f"❌ Automation error: {e}", exc_info=True)
        reporter.send_failure_email(str(e))

    logger.info(f"\n{'='*60}")
    logger.info(f"  Automation Complete: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"{'='*60}\n")


def send_upcoming_notification_job():
    """Job to send the upcoming notification."""
    try:
        reporter = EmailReporter(CONFIG["email"])
        reporter.send_upcoming_notification(CONFIG["automation"]["run_time"])
        logger.info("✅ Upcoming notification email sent successfully!")
    except Exception as e:
        logger.error(f"❌ Failed to send upcoming notification: {e}")


def start_scheduler():
    """Schedule daily automation and keep it running."""
    run_time = CONFIG["automation"]["run_time"]
    
    # Calculate 1 minute before run_time
    run_time_obj = datetime.strptime(run_time, "%H:%M")
    notify_time_obj = run_time_obj - timedelta(minutes=1)
    notify_time = notify_time_obj.strftime("%H:%M")

    logger.info(f"⏰ Scheduler started — will run daily at {run_time}")
    logger.info(f"⏰ Upcoming notification will be sent at {notify_time}")
    logger.info(f"   Solving {CONFIG['automation']['problems_per_day']} problems per day")
    logger.info(f"   Email report → {CONFIG['email']['receiver_email']}")

    # Schedule daily run
    schedule.every().day.at(run_time).do(run_daily_automation)
    
    # Schedule upcoming notification
    schedule.every().day.at(notify_time).do(send_upcoming_notification_job)

    # Also run immediately on first launch
    logger.info("🚀 Running initial session now...")
    threading.Thread(target=run_daily_automation, daemon=True).start()

    # Keep scheduler alive
    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    import sys
    if "--once" in sys.argv:
        # Single-run mode — used by the dashboard server
        run_daily_automation()
    else:
        start_scheduler()
