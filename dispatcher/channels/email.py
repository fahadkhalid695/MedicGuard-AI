"""Email notification channel via SendGrid."""

import asyncio
from functools import partial

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content

from dispatcher.config import SENDGRID_API_KEY, SENDGRID_FROM_EMAIL, SENDGRID_FROM_NAME


async def send_email(to_email: str, subject: str, html_body: str) -> dict:
    """
    Send an email via SendGrid. Runs the synchronous client in a thread pool.

    Returns:
        {"status_code": int, "message_id": str} on success
    Raises:
        Exception on failure
    """
    if not to_email:
        raise ValueError("No email address provided")
    if not SENDGRID_API_KEY:
        raise RuntimeError("SendGrid API key not configured")

    message = Mail(
        from_email=Email(SENDGRID_FROM_EMAIL, SENDGRID_FROM_NAME),
        to_emails=To(to_email),
        subject=subject,
        html_content=Content("text/html", html_body),
    )

    loop = asyncio.get_running_loop()
    sg = SendGridAPIClient(SENDGRID_API_KEY)

    response = await loop.run_in_executor(
        None,
        partial(sg.send, message),
    )

    return {
        "status_code": response.status_code,
        "message_id": response.headers.get("X-Message-Id", ""),
    }


def build_alert_email_html(
    patient_name: str,
    severity: str,
    summary: str,
    action: str,
    dashboard_link: str,
    agent_signals: list[dict],
) -> str:
    """Build a formatted HTML email for a critical alert."""
    severity_colors = {
        "low": "#eab308",
        "medium": "#f97316",
        "high": "#dc2626",
        "critical": "#7f1d1d",
    }
    color = severity_colors.get(severity, "#6b7280")

    signals_html = ""
    for sig in agent_signals:
        signals_html += f"""
        <tr>
            <td style="padding:8px;border-bottom:1px solid #e5e7eb;font-weight:600;">{sig.get('agent', 'Unknown')}</td>
            <td style="padding:8px;border-bottom:1px solid #e5e7eb;">{sig.get('severity', '').upper()}</td>
            <td style="padding:8px;border-bottom:1px solid #e5e7eb;">{sig.get('reason', '')}</td>
        </tr>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;margin:0;padding:20px;background:#f8fafc;">
        <div style="max-width:600px;margin:0 auto;background:white;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);">
            <!-- Header -->
            <div style="background:{color};padding:20px 24px;color:white;">
                <h1 style="margin:0;font-size:18px;">🚨 MediGuard AI — {severity.upper()} Alert</h1>
                <p style="margin:4px 0 0;opacity:0.9;font-size:14px;">Patient: {patient_name}</p>
            </div>

            <!-- Body -->
            <div style="padding:24px;">
                <h2 style="margin:0 0 8px;font-size:16px;color:#1e293b;">Summary</h2>
                <p style="margin:0 0 16px;color:#475569;line-height:1.5;">{summary}</p>

                <h2 style="margin:0 0 8px;font-size:16px;color:#1e293b;">Recommended Action</h2>
                <p style="margin:0 0 24px;color:#475569;line-height:1.5;font-weight:600;">{action}</p>

                <!-- Agent Signals -->
                <h2 style="margin:0 0 8px;font-size:16px;color:#1e293b;">Agent Signals</h2>
                <table style="width:100%;border-collapse:collapse;font-size:13px;margin-bottom:24px;">
                    <thead>
                        <tr style="background:#f1f5f9;">
                            <th style="padding:8px;text-align:left;">Agent</th>
                            <th style="padding:8px;text-align:left;">Severity</th>
                            <th style="padding:8px;text-align:left;">Reason</th>
                        </tr>
                    </thead>
                    <tbody>
                        {signals_html}
                    </tbody>
                </table>

                <!-- CTA -->
                <a href="{dashboard_link}" style="display:inline-block;background:#3b82f6;color:white;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:600;font-size:14px;">
                    View Patient Dashboard →
                </a>
            </div>

            <!-- Footer -->
            <div style="padding:16px 24px;background:#f8fafc;border-top:1px solid #e2e8f0;font-size:12px;color:#94a3b8;">
                This is an automated alert from MediGuard AI. Do not reply to this email.
            </div>
        </div>
    </body>
    </html>
    """
