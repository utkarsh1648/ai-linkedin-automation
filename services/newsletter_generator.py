"""
Newsletter renderer.

HTML output uses fully inline styles — required for Gmail, Outlook, and most
email clients which strip <style> blocks. Layout is table-based for Outlook
compatibility (no CSS Grid / Flexbox).

Plain-text fallback is generated for spam filter scoring and plain-text clients.
"""

from typing import List, Dict


class HTMLRenderer:
    """Renders the AI news newsletter as email-safe HTML and plain text."""

    # Brand colours
    _ACCENT = "#6366f1"          # indigo
    _ACCENT_DARK = "#4f46e5"
    _BG = "#f8fafc"
    _CARD_BG = "#ffffff"
    _TEXT = "#1e293b"
    _MUTED = "#64748b"
    _BORDER = "#e2e8f0"

    @staticmethod
    def render_newsletter(
        intro_text: str,
        articles: List[Dict[str, str]],
        subscriber_name: str = "",
        unsubscribe_url: str = "",
    ) -> str:
        """
        Renders a fully inline-styled, email-safe HTML newsletter.

        Args:
            intro_text: AI-generated intro paragraph.
            articles: List of article dicts (title, description, url, urlToImage).
            subscriber_name: Used in the personalised greeting ("Hi Utkarsh").
            unsubscribe_url: Token-based unsubscribe link embedded in the footer.
        """
        greeting = f"Hi {subscriber_name}," if subscriber_name else "Hi there,"
        c = HTMLRenderer  # shorthand

        article_blocks = ""
        for idx, article in enumerate(articles, 1):
            title = article.get("title", "No Title")
            desc = article.get("description", "")
            url = article.get("url", "#")
            img_url = article.get("urlToImage", "")

            img_block = ""
            if img_url:
                img_block = f"""
                <tr>
                  <td style="padding:0 0 16px 0;">
                    <img src="{img_url}" alt="{title}"
                         width="560" style="display:block;width:100%;max-width:560px;
                         height:auto;border-radius:8px;border:0;" />
                  </td>
                </tr>"""

            article_blocks += f"""
            <!-- Article {idx} -->
            <tr>
              <td style="padding:0 0 4px 0;">
                <table width="100%" cellpadding="0" cellspacing="0" border="0"
                       style="background:{c._CARD_BG};border-radius:12px;
                              border:1px solid {c._BORDER};margin-bottom:20px;">
                  <tr>
                    <td style="padding:24px 28px;">
                      <table width="100%" cellpadding="0" cellspacing="0" border="0">
                        <tr>
                          <td style="padding:0 0 4px 0;">
                            <span style="font-size:11px;font-weight:700;letter-spacing:1px;
                                         text-transform:uppercase;color:{c._ACCENT};">
                              #{idx}
                            </span>
                          </td>
                        </tr>
                        <tr>
                          <td style="padding:0 0 12px 0;">
                            <h2 style="margin:0;font-size:18px;font-weight:700;
                                        line-height:1.4;color:{c._TEXT};
                                        font-family:Arial,Helvetica,sans-serif;">
                              {title}
                            </h2>
                          </td>
                        </tr>
                        {img_block}
                        <tr>
                          <td style="padding:0 0 20px 0;">
                            <p style="margin:0;font-size:15px;line-height:1.6;
                                       color:{c._MUTED};
                                       font-family:Arial,Helvetica,sans-serif;">
                              {desc}
                            </p>
                          </td>
                        </tr>
                        <tr>
                          <td>
                            <a href="{url}" target="_blank"
                               style="display:inline-block;background:{c._ACCENT};
                                      color:#ffffff;text-decoration:none;
                                      padding:10px 22px;border-radius:6px;
                                      font-size:14px;font-weight:600;
                                      font-family:Arial,Helvetica,sans-serif;">
                              Read Article →
                            </a>
                          </td>
                        </tr>
                      </table>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
            <tr><td style="height:4px;"></td></tr>"""

        unsubscribe_block = ""
        if unsubscribe_url:
            unsubscribe_block = f"""
            | <a href="{unsubscribe_url}"
                 style="color:{c._MUTED};text-decoration:underline;
                         font-family:Arial,Helvetica,sans-serif;font-size:12px;">
                Unsubscribe
              </a>"""

        return f"""<!DOCTYPE html>
<html lang="en" xmlns="http://www.w3.org/1999/xhtml">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1.0" />
  <meta http-equiv="X-UA-Compatible" content="IE=edge" />
  <title>Your AI News Digest</title>
  <!--[if mso]>
  <noscript><xml><o:OfficeDocumentSettings>
    <o:PixelsPerInch>96</o:PixelsPerInch>
  </o:OfficeDocumentSettings></xml></noscript>
  <![endif]-->
</head>
<body style="margin:0;padding:0;background-color:{c._BG};
             font-family:Arial,Helvetica,sans-serif;-webkit-text-size-adjust:100%;">

  <!-- Preheader (hidden inbox preview text) -->
  <div style="display:none;max-height:0;overflow:hidden;
              color:{c._BG};font-size:1px;line-height:1px;">
    Your curated AI news for today — {len(articles)} stories, hand-picked by AI ‌&zwnj;
  </div>

  <!-- Outer wrapper -->
  <table width="100%" cellpadding="0" cellspacing="0" border="0"
         style="background-color:{c._BG};">
    <tr>
      <td align="center" style="padding:32px 16px;">

        <!-- Email card — max 600px -->
        <table width="600" cellpadding="0" cellspacing="0" border="0"
               style="max-width:600px;width:100%;">

          <!-- Header -->
          <tr>
            <td style="background:{c._ACCENT};border-radius:12px 12px 0 0;
                        padding:32px 40px;text-align:center;">
              <p style="margin:0 0 6px 0;font-size:12px;font-weight:700;
                          letter-spacing:2px;text-transform:uppercase;
                          color:rgba(255,255,255,0.7);">
                AI NEWS DIGEST
              </p>
              <h1 style="margin:0;font-size:28px;font-weight:800;color:#ffffff;
                          line-height:1.2;">
                🔥 Top Trending AI Stories
              </h1>
            </td>
          </tr>

          <!-- Greeting + intro -->
          <tr>
            <td style="background:{c._CARD_BG};padding:32px 40px 24px 40px;
                        border-left:1px solid {c._BORDER};
                        border-right:1px solid {c._BORDER};">
              <p style="margin:0 0 8px 0;font-size:17px;font-weight:700;
                          color:{c._TEXT};">
                {greeting}
              </p>
              <p style="margin:0;font-size:15px;line-height:1.7;color:{c._MUTED};
                          border-left:3px solid {c._ACCENT};padding-left:16px;">
                {intro_text}
              </p>
            </td>
          </tr>

          <!-- Divider -->
          <tr>
            <td style="background:{c._CARD_BG};padding:0 40px;
                        border-left:1px solid {c._BORDER};
                        border-right:1px solid {c._BORDER};">
              <hr style="border:none;border-top:1px solid {c._BORDER};margin:0;" />
            </td>
          </tr>

          <!-- Articles -->
          <tr>
            <td style="background:{c._BG};padding:24px 40px;
                        border-left:1px solid {c._BORDER};
                        border-right:1px solid {c._BORDER};">
              <table width="100%" cellpadding="0" cellspacing="0" border="0">
                {article_blocks}
              </table>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background:{c._CARD_BG};border-radius:0 0 12px 12px;
                        border:1px solid {c._BORDER};padding:24px 40px;
                        text-align:center;">
              <p style="margin:0 0 8px 0;font-size:13px;color:{c._MUTED};
                          font-family:Arial,Helvetica,sans-serif;">
                You're receiving this because you subscribed to <strong>AI News Digest</strong>.
              </p>
              <p style="margin:0;font-size:12px;color:{c._MUTED};
                          font-family:Arial,Helvetica,sans-serif;">
                <a href="#" style="color:{c._MUTED};text-decoration:underline;">
                  View in browser
                </a>
                {unsubscribe_block}
              </p>
            </td>
          </tr>

        </table>
        <!-- /Email card -->

      </td>
    </tr>
  </table>

</body>
</html>"""

    @staticmethod
    def render_plaintext_newsletter(
        intro_text: str,
        articles: List[Dict[str, str]],
        subscriber_name: str = "",
        unsubscribe_url: str = "",
    ) -> str:
        """
        Plain-text fallback — improves deliverability and serves plain-text email clients.
        """
        greeting = f"Hi {subscriber_name}," if subscriber_name else "Hi there,"
        lines = [
            "AI NEWS DIGEST — Top Trending AI Stories",
            "=" * 50,
            "",
            greeting,
            "",
            intro_text,
            "",
            "-" * 50,
        ]

        for idx, article in enumerate(articles, 1):
            title = article.get("title", "No Title")
            desc = article.get("description", "")
            url = article.get("url", "")
            lines += [f"\n#{idx} {title}", desc, f"Read more: {url}", "-" * 50]

        lines += [
            "",
            "You're receiving this because you subscribed to AI News Digest.",
        ]
        if unsubscribe_url:
            lines.append(f"Unsubscribe: {unsubscribe_url}")

        return "\n".join(lines)
