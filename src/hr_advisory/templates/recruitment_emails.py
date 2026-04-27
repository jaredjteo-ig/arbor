"""Recruitment email templates for candidate communication.

T-R017: Professional HTML email templates for recruitment workflow stages.

Each template is a dict with 'subject' and 'html' keys. Placeholders use
Python str.format() style: {candidate_name}, {job_title}, {company_name}, etc.

Templates:
    application_received — sent to candidate upon application
    interview_invitation — sent to candidate when interview is scheduled
    offer_sent           — sent to candidate with offer details
    rejection_notice     — sent to candidate when not selected
    feedback_reminder    — internal, sent to interviewer when feedback is overdue
"""

from __future__ import annotations

__all__ = ["RECRUITMENT_TEMPLATES"]


# ---------------------------------------------------------------------------
# Shared HTML styles (inline for email client compatibility)
# ---------------------------------------------------------------------------

_BASE_STYLE = (
    'font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; '
    "max-width: 600px; margin: 0 auto; padding: 20px; color: #333;"
)

_FOOTER_STYLE = (
    "border-top: 1px solid #eee; padding-top: 16px; margin-top: 16px; "
    "color: #999; font-size: 0.8em;"
)


# ---------------------------------------------------------------------------
# 1. Application Received
# ---------------------------------------------------------------------------

_APPLICATION_RECEIVED_SUBJECT = (
    "Application Received \u2014 {job_title} at {company_name}"
)

_APPLICATION_RECEIVED_HTML = """<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="{base_style}">
  <div style="background: #e8f5e9; border-radius: 8px; padding: 24px; margin-bottom: 16px;">
    <h2 style="margin: 0 0 8px; color: #2e7d32;">Application Received</h2>
    <p style="margin: 0; color: #2e7d32;">Hi {{candidate_name}},</p>
  </div>
  <div style="padding: 16px;">
    <p>Thank you for applying for the <strong>{{job_title}}</strong> position at <strong>{{company_name}}</strong>. We have received your application and it is now under review.</p>
    <p>Our hiring team will carefully evaluate your qualifications and experience. We aim to get back to you within the next few business days with an update on your application status.</p>
    <p>In the meantime, if you have any questions, please do not hesitate to reach out to our HR team.</p>
    <p style="color: #666; font-size: 0.9em;">We appreciate your interest in joining {{company_name}} and look forward to reviewing your application.</p>
  </div>
  <div style="{footer_style}">
    <p>This is an automated message from {{company_name}} via Arbor HR Platform. Please do not reply to this email.</p>
  </div>
</body>
</html>
""".format(
    base_style=_BASE_STYLE, footer_style=_FOOTER_STYLE
)


# ---------------------------------------------------------------------------
# 2. Interview Invitation
# ---------------------------------------------------------------------------

_INTERVIEW_INVITATION_SUBJECT = (
    "Interview Invitation \u2014 {job_title} at {company_name}"
)

_INTERVIEW_INVITATION_HTML = """<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="{base_style}">
  <div style="background: #e3f2fd; border-radius: 8px; padding: 24px; margin-bottom: 16px;">
    <h2 style="margin: 0 0 8px; color: #1565c0;">Interview Invitation</h2>
    <p style="margin: 0; color: #1565c0;">Hi {{candidate_name}},</p>
  </div>
  <div style="padding: 16px;">
    <p>We are pleased to invite you for an interview for the <strong>{{job_title}}</strong> position at <strong>{{company_name}}</strong>.</p>
    <table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
      <tr style="border-bottom: 1px solid #eee;">
        <td style="padding: 8px 0; color: #666;">Date</td>
        <td style="padding: 8px 0; text-align: right;">{{interview_date}}</td>
      </tr>
      <tr style="border-bottom: 1px solid #eee;">
        <td style="padding: 8px 0; color: #666;">Time</td>
        <td style="padding: 8px 0; text-align: right;">{{interview_time}}</td>
      </tr>
      <tr style="border-bottom: 1px solid #eee;">
        <td style="padding: 8px 0; color: #666;">Duration</td>
        <td style="padding: 8px 0; text-align: right;">{{duration}}</td>
      </tr>
      <tr style="border-bottom: 1px solid #eee;">
        <td style="padding: 8px 0; color: #666;">Format</td>
        <td style="padding: 8px 0; text-align: right;">{{interview_format}}</td>
      </tr>
      <tr style="border-bottom: 1px solid #eee;">
        <td style="padding: 8px 0; color: #666;">Location / Link</td>
        <td style="padding: 8px 0; text-align: right;">{{location_or_link}}</td>
      </tr>
      <tr>
        <td style="padding: 8px 0; color: #666;">Interviewer(s)</td>
        <td style="padding: 8px 0; text-align: right;">{{interviewer_names}}</td>
      </tr>
    </table>
    <div style="background: #f8f9fa; border-left: 4px solid #1565c0; padding: 12px 16px; margin: 16px 0;">
      <p style="margin: 0; font-weight: 600;">Preparation Tips</p>
      <ul style="margin: 8px 0 0; padding-left: 20px; color: #555;">
        <li>Review the job description and think about how your experience aligns with the role.</li>
        <li>Prepare examples that demonstrate your skills and achievements.</li>
        <li>Have questions ready about the team and company culture.</li>
      </ul>
    </div>
    <p style="color: #666; font-size: 0.9em;">If you need to reschedule, please let us know at your earliest convenience.</p>
  </div>
  <div style="{footer_style}">
    <p>This is an automated message from {{company_name}} via Arbor HR Platform. Please do not reply to this email.</p>
  </div>
</body>
</html>
""".format(
    base_style=_BASE_STYLE, footer_style=_FOOTER_STYLE
)


# ---------------------------------------------------------------------------
# 3. Offer Sent
# ---------------------------------------------------------------------------

_OFFER_SENT_SUBJECT = (
    "Job Offer \u2014 {position_title} at {company_name}"
)

_OFFER_SENT_HTML = """<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="{base_style}">
  <div style="background: #fff8e1; border-radius: 8px; padding: 24px; margin-bottom: 16px;">
    <h2 style="margin: 0 0 8px; color: #f57f17;">Congratulations!</h2>
    <p style="margin: 0; color: #f57f17;">Dear {{candidate_name}},</p>
  </div>
  <div style="padding: 16px;">
    <p>We are delighted to extend an offer of employment to you for the position of <strong>{{position_title}}</strong> at <strong>{{company_name}}</strong>.</p>
    <table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
      <tr style="border-bottom: 1px solid #eee;">
        <td style="padding: 8px 0; color: #666;">Position</td>
        <td style="padding: 8px 0; text-align: right; font-weight: 600;">{{position_title}}</td>
      </tr>
      <tr style="border-bottom: 1px solid #eee;">
        <td style="padding: 8px 0; color: #666;">Salary</td>
        <td style="padding: 8px 0; text-align: right; font-weight: 600;">{{salary}}</td>
      </tr>
      <tr style="border-bottom: 1px solid #eee;">
        <td style="padding: 8px 0; color: #666;">Proposed Start Date</td>
        <td style="padding: 8px 0; text-align: right;">{{start_date}}</td>
      </tr>
      <tr>
        <td style="padding: 8px 0; color: #666;">Offer Valid Until</td>
        <td style="padding: 8px 0; text-align: right; color: #e65100;">{{expiry_date}}</td>
      </tr>
    </table>
    <p>Please review the offer details carefully. To accept, kindly confirm your acceptance before the expiry date listed above.</p>
    <p>If you have any questions about the offer or would like to discuss the terms, please do not hesitate to reach out to our HR team.</p>
    <p style="color: #666; font-size: 0.9em;">We look forward to welcoming you to the {{company_name}} team.</p>
  </div>
  <div style="{footer_style}">
    <p>This is an automated message from {{company_name}} via Arbor HR Platform. Please do not reply to this email.</p>
  </div>
</body>
</html>
""".format(
    base_style=_BASE_STYLE, footer_style=_FOOTER_STYLE
)


# ---------------------------------------------------------------------------
# 4. Rejection Notice
# ---------------------------------------------------------------------------

_REJECTION_NOTICE_SUBJECT = (
    "Update on Your Application \u2014 {company_name}"
)

_REJECTION_NOTICE_HTML = """<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="{base_style}">
  <div style="background: #f5f5f5; border-radius: 8px; padding: 24px; margin-bottom: 16px;">
    <h2 style="margin: 0 0 8px; color: #616161;">Application Update</h2>
    <p style="margin: 0; color: #616161;">Dear {{candidate_name}},</p>
  </div>
  <div style="padding: 16px;">
    <p>Thank you for your interest in the <strong>{{job_title}}</strong> position at <strong>{{company_name}}</strong> and for taking the time to apply.</p>
    <p>After careful consideration, we have decided to move forward with other candidates whose qualifications more closely match our current requirements.</p>
    <p>This was not an easy decision, and we genuinely appreciate the effort you put into your application. We encourage you to apply for future openings that may be a better fit.</p>
    <p>We wish you all the best in your career journey.</p>
    <p style="color: #666; font-size: 0.9em;">Warm regards,<br>The {{company_name}} Hiring Team</p>
  </div>
  <div style="{footer_style}">
    <p>This is an automated message from {{company_name}} via Arbor HR Platform. Please do not reply to this email.</p>
  </div>
</body>
</html>
""".format(
    base_style=_BASE_STYLE, footer_style=_FOOTER_STYLE
)


# ---------------------------------------------------------------------------
# 5. Feedback Reminder (internal — sent to interviewer)
# ---------------------------------------------------------------------------

_FEEDBACK_REMINDER_SUBJECT = (
    "Feedback Reminder \u2014 {candidate_name} Interview"
)

_FEEDBACK_REMINDER_HTML = """<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="{base_style}">
  <div style="background: #fff3e0; border-radius: 8px; padding: 24px; margin-bottom: 16px;">
    <h2 style="margin: 0 0 8px; color: #e65100;">Interview Feedback Reminder</h2>
    <p style="margin: 0; color: #e65100;">Action required</p>
  </div>
  <div style="padding: 16px;">
    <p>You interviewed <strong>{{candidate_name}}</strong> for the <strong>{{job_title}}</strong> position on <strong>{{interview_date}}</strong>.</p>
    <p>We have not yet received your interview feedback. Timely feedback helps our hiring team make well-informed decisions and ensures a good experience for our candidates.</p>
    <p>Please submit your feedback as soon as possible through the recruitment module in Arbor.</p>
    <div style="background: #f8f9fa; border-left: 4px solid #e65100; padding: 12px 16px; margin: 16px 0;">
      <p style="margin: 0; font-weight: 600;">Your feedback should include:</p>
      <ul style="margin: 8px 0 0; padding-left: 20px; color: #555;">
        <li>Overall rating</li>
        <li>Key strengths observed</li>
        <li>Areas of concern</li>
        <li>Your recommendation (hire / no hire / further evaluation)</li>
      </ul>
    </div>
  </div>
  <div style="{footer_style}">
    <p>This is an internal reminder from Arbor HR Platform. Please do not forward this email externally.</p>
  </div>
</body>
</html>
""".format(
    base_style=_BASE_STYLE, footer_style=_FOOTER_STYLE
)


# ---------------------------------------------------------------------------
# 6. Data Retention Warning (T-R030: PDPA pre-purge notice)
# ---------------------------------------------------------------------------

_DATA_RETENTION_WARNING_SUBJECT = (
    "Action Required: Your application data with {company_name} will be deleted soon"
)

_DATA_RETENTION_WARNING_HTML = """<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="{base_style}">
  <div style="background: #fff3e0; border-radius: 8px; padding: 24px; margin-bottom: 16px;">
    <h2 style="margin: 0 0 8px; color: #e65100;">Your application data will be deleted soon</h2>
    <p style="margin: 0; color: #e65100;">Hi {{candidate_name}},</p>
  </div>
  <div style="padding: 16px;">
    <p>Under Singapore's Personal Data Protection Act (PDPA), <strong>{{company_name}}</strong> retains unsuccessful applicants' personal data for no longer than <strong>2 years</strong>.</p>
    <p>Your application for the <strong>{{job_title}}</strong> role was submitted on <strong>{{applied_date}}</strong>. Your record will be permanently deleted on or around <strong>{{purge_date}}</strong> (about 30 days from now).</p>
    <p>If you would like to remain in our talent pool for future roles, please reply to this email and we will renew your consent. If you do nothing, your data will be deleted automatically.</p>
    <p style="color: #666; font-size: 0.9em;">You may also exercise your PDPA rights to access, correct, or withdraw consent for your personal data at any time before the deletion date.</p>
  </div>
  <div style="{footer_style}">
    <p>This is an automated PDPA retention notice from {{company_name}} via Arbor HR Platform.</p>
  </div>
</body>
</html>
""".format(
    base_style=_BASE_STYLE, footer_style=_FOOTER_STYLE
)


# ---------------------------------------------------------------------------
# Public template registry
# ---------------------------------------------------------------------------

RECRUITMENT_TEMPLATES: dict[str, dict[str, str]] = {
    "application_received": {
        "subject": _APPLICATION_RECEIVED_SUBJECT,
        "html": _APPLICATION_RECEIVED_HTML,
    },
    "interview_invitation": {
        "subject": _INTERVIEW_INVITATION_SUBJECT,
        "html": _INTERVIEW_INVITATION_HTML,
    },
    "offer_sent": {
        "subject": _OFFER_SENT_SUBJECT,
        "html": _OFFER_SENT_HTML,
    },
    "rejection_notice": {
        "subject": _REJECTION_NOTICE_SUBJECT,
        "html": _REJECTION_NOTICE_HTML,
    },
    "feedback_reminder": {
        "subject": _FEEDBACK_REMINDER_SUBJECT,
        "html": _FEEDBACK_REMINDER_HTML,
    },
    "data_retention_warning": {
        "subject": _DATA_RETENTION_WARNING_SUBJECT,
        "html": _DATA_RETENTION_WARNING_HTML,
    },
}
