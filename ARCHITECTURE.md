# LeetCode Automation Bot — Architecture & Flow

This document outlines the technical stack, internal processes, and the mechanisms used to bypass Cloudflare security in the LeetCode Automation Bot.

---

## 🛠️ Technology Stack

| Technology | Purpose |
|------------|---------|
| **Python 3.11** | The core programming language running the automation scripts, handling logic, and coordinating API calls. |
| **Flask** | A lightweight web framework used to serve the mobile-friendly web dashboard and provide REST API endpoints. |
| **Flask-CORS** | Enables Cross-Origin Resource Sharing so the dashboard API can be accessed from different devices (like your phone). |
| **APScheduler** | (Advanced Python Scheduler) Runs in the background of the Flask server to trigger the automation script at the exact scheduled time every day. |
| **Gunicorn** | A production-grade WSGI HTTP server used to run the Flask app reliably in cloud environments (like Render). |
| **Requests** | A Python HTTP library used to make API calls to LeetCode's GraphQL endpoints and submit solutions. |
| **HTML/CSS/JS** | Used for the frontend dashboard. It is configured as a **Progressive Web App (PWA)** using a Service Worker (`sw.js`) and Manifest (`manifest.json`) so it can be installed on phones. |

---

## ⚙️ How It Works & Internal Process Flow

### The Execution Flow
1. **The Scheduler:** `APScheduler` runs continuously inside `server.py`. Every minute, it checks the clock. When the scheduled time hits (e.g., `08:00 AM`), it triggers `_run_automation_thread()`.
2. **The Automation Script:** The server launches `main.py` in the background.
3. **Problem Selection:** `leetcode_client.py` queries LeetCode's GraphQL API. It fetches the "Daily Challenge" and then searches for additional problems (based on your Easy/Medium/Hard config) that you haven't solved yet.
4. **AI Solving:** The problem description, hints, and starter code are sent to an LLM (via `problem_solver.py`). The AI generates an optimal solution in Python.
5. **Submission:** The generated code is submitted back to LeetCode via their internal API.
6. **Result Polling:** The script polls LeetCode for the result (Accepted, Wrong Answer, Time Limit). If it fails, it asks the AI to fix the bug and tries again.
7. **Reporting:** Once 5 problems are solved, the script saves the results to `logs/history.json` and `email_reporter.py` sends an email summary.
8. **Dashboard Streaming:** While all of this happens, `server.py` uses **Server-Sent Events (SSE)** to stream the live logs and progress bars directly to your phone's web dashboard in real-time.

---

## 🛡️ Cracking Cloudflare ("I am not a robot")

LeetCode is heavily protected by **Cloudflare**, which uses advanced browser fingerprinting, JavaScript challenges, and CAPTCHAs ("I am not a robot") to block automated bots.

### The Bypass Strategy: "Cookie Injection & Header Spoofing"
Instead of trying to programmatically solve the CAPTCHA (which is nearly impossible for a basic script), the bot uses a bypass strategy. 

When you initially log into LeetCode on your real browser, you solve the Cloudflare challenge. Cloudflare rewards your browser with a `cf_clearance` cookie. This cookie acts as a "VIP Pass" that tells Cloudflare: *"I am a verified human, do not challenge me again for the next year."*

**Here is how `leetcode_client.py` uses this:**
1. **Cookie Injection:** You provide your `LEETCODE_SESSION`, `csrftoken`, and most importantly, the `cf_clearance` cookie in `config.json`.
2. **Session Hijacking:** The Python `requests.Session()` injects these exact cookies into its memory.
3. **Browser Spoofing:** The script updates its HTTP headers to exactly match a real browser:
   ```python
   "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36"
   ```
4. **The Result:** When the bot makes a request to LeetCode, Cloudflare inspects the request. It sees the valid `cf_clearance` VIP pass and a normal-looking `User-Agent`. Cloudflare completely skips the "I am not a robot" check and allows the bot direct access to the API.

---

## 🚀 How to Run the Project

### Running Locally (On your Laptop)
1. Open a terminal in the project folder.
2. Install dependencies: `pip install -r requirements.txt`
3. Start the dashboard: `python dashboard/server.py`
4. Open `http://localhost:5050` in your browser.

### Running Live (In the Cloud)
1. Upload the code to a private GitHub repository.
2. Connect the repository to a free hosting provider like **Render.com**.
3. Render will use the `Procfile` to automatically run `gunicorn wsgi:app`.
4. The bot will now run 24/7 in the cloud. You can open your Render URL on your phone and click **"Add to Home Screen"** to install the dashboard app!
