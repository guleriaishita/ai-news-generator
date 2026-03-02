import os
import resend
from datetime import date
from dotenv import load_dotenv

load_dotenv()

resend.api_key = os.getenv("RESEND_API_KEY", "")

# Use "onboarding@resend.dev" for sandbox testing (no domain verification needed).
# Swap for a verified sender address when going to production.
FROM_ADDRESS = os.getenv("RESEND_FROM", "AI News Digest <onboarding@resend.dev>")

# Without a verified domain, Resend only delivers to the account owner's address.
# Set RESEND_VERIFIED_EMAIL to that address; any other subscriber gets a clear 400.
RESEND_VERIFIED_EMAIL = os.getenv("RESEND_VERIFIED_EMAIL", "").strip()


class SandboxRestrictionError(Exception):
    """Raised when the recipient isn't the Resend-verified address in sandbox mode."""


def _build_html(articles: list[dict]) -> str:
    """Build the newsletter HTML body from a list of processed articles."""
    today = date.today().strftime("%B %-d, %Y")

    category_colors = {
        "AI Tools":      "#2471a3",
        "Industry News": "#1e8449",
        "Ethics":        "#b7950b",
        "Research":      "#7d3c98",
    }

    rows = ""
    for article in articles:
        color    = category_colors.get(article.get("category", ""), "#555")
        title    = article.get("title", "")
        url      = article.get("url", "#")
        summary  = article.get("summary", "")
        category = article.get("category", "")
        source   = article.get("source", "")

        source_tag = (
            f"&nbsp;&middot;&nbsp;<span style='font-size:11px;color:#aaa;'>{source}</span>"
            if source else ""
        )

        rows += f"""
        <tr>
          <td style="padding:16px 0; border-bottom:1px solid #eee;">
            <span style="font-size:11px;font-weight:600;color:{color};
                         text-transform:uppercase;letter-spacing:0.05em;">
              {category}
            </span>
            {source_tag}
            <br>
            <a href="{url}" style="font-size:15px;font-weight:600;color:#111;
                                   text-decoration:none;line-height:1.4;
                                   display:inline-block;margin:6px 0 4px;">
              {title}
            </a>
            <br>
            <span style="font-size:13px;color:#555;line-height:1.5;">{summary}</span>
          </td>
        </tr>
        """

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>AI News Digest – {today}</title>
</head>
<body style="margin:0;padding:0;background:#f7f7f5;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f7f7f5;padding:32px 16px;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0"
               style="background:#fff;border:1px solid #e4e4e0;border-radius:8px;overflow:hidden;">

          <!-- Header -->
          <tr>
            <td style="padding:24px 28px 20px;border-bottom:1px solid #eee;">
              <span style="font-size:20px;font-weight:700;color:#111;">AI News Digest</span><br>
              <span style="font-size:12px;color:#999;">{today}</span>
            </td>
          </tr>

          <!-- Articles -->
          <tr>
            <td style="padding:0 28px;">
              <table width="100%" cellpadding="0" cellspacing="0">
                {rows}
              </table>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding:20px 28px;border-top:1px solid #eee;font-size:12px;color:#aaa;">
              You're receiving this because you subscribed to AI News Digest.
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def build_newsletter_html(articles: list[dict]) -> str:
    """Public wrapper — builds the newsletter HTML without sending it."""
    return _build_html(articles)


def send_welcome_email(to_email: str, articles: list[dict]) -> None:
    """
    Send the newsletter to `to_email`.

    In sandbox mode (RESEND_VERIFIED_EMAIL set), only the account owner's verified
    address is deliverable. Any other address raises SandboxRestrictionError so the
    UI gets an honest explanation rather than a silent failure.
    """
    if not resend.api_key:
        raise RuntimeError(
            "RESEND_API_KEY is not set. Add it to backend/.env to enable email sending."
        )

    if RESEND_VERIFIED_EMAIL and to_email.lower() != RESEND_VERIFIED_EMAIL.lower():
        raise SandboxRestrictionError(
            f"This demo runs in Resend sandbox mode, which only allows sending "
            f"to the verified developer address. "
            f"Please use {RESEND_VERIFIED_EMAIL} to test email delivery. "
            f"In production (with a verified domain), any address would work."
        )

    html_body = _build_html(articles)
    today = date.today().strftime("%B %-d, %Y")

    print(f"[email] Sending newsletter to '{to_email}'...")
    resend.Emails.send({
        "from": FROM_ADDRESS,
        "to": [to_email],
        "subject": f"AI News Digest – {today}",
        "html": html_body,
    })
    print(f"[email] Delivered to '{to_email}'")
