"""
Email Reporter
Sends beautiful HTML email reports with LeetCode daily results.
"""

import smtplib
import json
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Dict, Any
from logger import setup_logger

logger = setup_logger("email_reporter")


class EmailReporter:
    def __init__(self, config: Dict):
        self.sender_email = config["sender_email"]
        self.sender_password = config["sender_password"]
        self.receiver_email = config["receiver_email"]
        self.smtp_host = config["smtp_host"]
        self.smtp_port = config["smtp_port"]

    def send_daily_report(self, results: List[Dict], date: datetime):
        """Send a beautiful HTML email report for the day."""
        subject = f"✅ LeetCode Daily Report — {date.strftime('%B %d, %Y')}"
        html = self._build_html_report(results, date)
        self._send_email(subject, html)

    def send_failure_email(self, error_msg: str):
        """Send a failure notification email."""
        subject = f"⚠️ LeetCode Automation Error — {datetime.now().strftime('%Y-%m-%d')}"
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; background: #1a1a2e; color: #eee; padding: 30px;">
          <div style="max-width: 600px; margin: auto; background: #16213e; border-radius: 15px; padding: 30px;">
            <h2 style="color: #e94560;">⚠️ Automation Failed</h2>
            <p style="color: #aaa;">The LeetCode automation encountered an error:</p>
            <pre style="background: #0f3460; padding: 15px; border-radius: 8px; color: #ff6b6b; white-space: pre-wrap;">{error_msg}</pre>
            <p style="color: #aaa; font-size: 12px;">Please check the logs at <code>automation.log</code></p>
          </div>
        </body>
        </html>
        """
        self._send_email(subject, html)

    def _build_html_report(self, results: List[Dict], date: datetime) -> str:
        """Build a beautiful HTML email report."""
        accepted = [r for r in results if "ACCEPTED" in r.get("status", "")]
        failed = [r for r in results if "ACCEPTED" not in r.get("status", "")]
        success_rate = int((len(accepted) / len(results)) * 100) if results else 0

        difficulty_colors = {
            "Easy": "#00b8a9",
            "Medium": "#f9ca24",
            "Hard": "#e94560"
        }

        # Build problem cards
        problem_cards = ""
        for i, r in enumerate(results, 1):
            status = r.get("status", "UNKNOWN")
            is_accepted = "ACCEPTED" in status
            status_color = "#00b8a9" if is_accepted else "#e94560"
            status_icon = "✅" if is_accepted else "❌"
            difficulty = r.get("difficulty", "Unknown")
            diff_color = difficulty_colors.get(difficulty, "#aaa")

            code_block = ""
            if r.get("code"):
                escaped_code = r["code"].replace("<", "&lt;").replace(">", "&gt;")
                code_block = f"""
                <div style="margin-top: 12px;">
                  <details>
                    <summary style="color: #00b8a9; cursor: pointer; font-size: 13px;">📋 View Solution Code</summary>
                    <pre style="background: #0a0a1a; padding: 12px; border-radius: 8px; overflow-x: auto; font-size: 12px; color: #a8d8ea; margin-top: 8px;">{escaped_code}</pre>
                  </details>
                </div>
                """

            stats_block = ""
            if is_accepted and r.get("runtime"):
                stats_block = f"""
                <div style="display: flex; gap: 15px; margin-top: 10px;">
                  <span style="background: #0f3460; padding: 4px 12px; border-radius: 20px; font-size: 12px; color: #a8d8ea;">
                    ⚡ {r.get('runtime', 'N/A')}
                  </span>
                  <span style="background: #0f3460; padding: 4px 12px; border-radius: 20px; font-size: 12px; color: #a8d8ea;">
                    💾 {r.get('memory', 'N/A')}
                  </span>
                  <span style="background: #0f3460; padding: 4px 12px; border-radius: 20px; font-size: 12px; color: #a8d8ea;">
                    🔤 {r.get('language', 'python3')}
                  </span>
                </div>
                """

            problem_cards += f"""
            <div style="background: #0f3460; border-radius: 12px; padding: 20px; margin-bottom: 15px; border-left: 4px solid {status_color};">
              <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                  <span style="color: #aaa; font-size: 13px;">Problem {i}</span>
                  <h3 style="margin: 5px 0; color: #e8e8e8; font-size: 16px;">{r.get('title', 'Unknown')}</h3>
                  <span style="background: {diff_color}22; color: {diff_color}; padding: 3px 10px; border-radius: 12px; font-size: 12px; font-weight: bold;">
                    {difficulty}
                  </span>
                </div>
                <div style="text-align: right;">
                  <div style="font-size: 24px;">{status_icon}</div>
                  <div style="color: {status_color}; font-size: 13px; font-weight: bold;">{status}</div>
                </div>
              </div>
              {stats_block}
              {code_block}
            </div>
            """

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="UTF-8">
          <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="margin: 0; padding: 0; background: #0a0a1a; font-family: 'Segoe UI', Arial, sans-serif;">
          <div style="max-width: 680px; margin: 30px auto; background: #16213e; border-radius: 20px; overflow: hidden; box-shadow: 0 20px 60px rgba(0,0,0,0.5);">

            <!-- Header -->
            <div style="background: linear-gradient(135deg, #0f3460 0%, #16213e 100%); padding: 35px 30px; text-align: center; border-bottom: 2px solid #0f3460;">
              <div style="font-size: 48px; margin-bottom: 10px;">🏆</div>
              <h1 style="margin: 0; color: #fff; font-size: 26px; font-weight: 700;">LeetCode Daily Report</h1>
              <p style="margin: 8px 0 0; color: #a8d8ea; font-size: 15px;">{date.strftime('%A, %B %d, %Y')}</p>
            </div>

            <!-- Stats Bar -->
            <div style="display: flex; background: #0f3460; padding: 0;">
              <div style="flex: 1; padding: 20px; text-align: center; border-right: 1px solid #16213e;">
                <div style="font-size: 32px; font-weight: 700; color: #00b8a9;">{len(accepted)}</div>
                <div style="color: #aaa; font-size: 13px; margin-top: 4px;">Accepted</div>
              </div>
              <div style="flex: 1; padding: 20px; text-align: center; border-right: 1px solid #16213e;">
                <div style="font-size: 32px; font-weight: 700; color: #e94560;">{len(failed)}</div>
                <div style="color: #aaa; font-size: 13px; margin-top: 4px;">Failed</div>
              </div>
              <div style="flex: 1; padding: 20px; text-align: center; border-right: 1px solid #16213e;">
                <div style="font-size: 32px; font-weight: 700; color: #f9ca24;">{len(results)}</div>
                <div style="color: #aaa; font-size: 13px; margin-top: 4px;">Total</div>
              </div>
              <div style="flex: 1; padding: 20px; text-align: center;">
                <div style="font-size: 32px; font-weight: 700; color: #a8d8ea;">{success_rate}%</div>
                <div style="color: #aaa; font-size: 13px; margin-top: 4px;">Success Rate</div>
              </div>
            </div>

            <!-- Progress Bar -->
            <div style="background: #0f3460; padding: 0 30px 20px;">
              <div style="background: #1a1a3e; border-radius: 10px; overflow: hidden; height: 8px;">
                <div style="width: {success_rate}%; height: 100%; background: linear-gradient(90deg, #00b8a9, #a8d8ea); transition: width 0.5s;"></div>
              </div>
            </div>

            <!-- Problems Section -->
            <div style="padding: 25px 30px;">
              <h2 style="color: #e8e8e8; font-size: 18px; margin: 0 0 20px; border-bottom: 1px solid #0f3460; padding-bottom: 10px;">
                📝 Today's Problems
              </h2>
              {problem_cards}
            </div>

            <!-- Footer -->
            <div style="background: #0f3460; padding: 20px 30px; text-align: center; border-top: 2px solid #16213e;">
              <p style="margin: 0; color: #aaa; font-size: 12px;">
                🤖 Generated by LeetCode Automation &nbsp;|&nbsp;
                ⏰ {date.strftime('%H:%M:%S')} &nbsp;|&nbsp;
                🐍 Python 3
              </p>
              <p style="margin: 8px 0 0; color: #666; font-size: 11px;">
                Next run scheduled tomorrow at the configured time
              </p>
            </div>

          </div>
        </body>
        </html>
        """
        return html

    def _send_email(self, subject: str, html_body: str):
        """Send an email via SMTP."""
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.sender_email
        msg["To"] = self.receiver_email

        msg.attach(MIMEText(html_body, "html"))

        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30) as server:
                server.ehlo()
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.sendmail(self.sender_email, self.receiver_email, msg.as_string())
            logger.info(f"  📧 Email sent to {self.receiver_email}")
        except smtplib.SMTPAuthenticationError:
            logger.error("  ❌ Email auth failed — check App Password in config.json")
        except Exception as e:
            logger.error(f"  ❌ Email send failed: {e}")
