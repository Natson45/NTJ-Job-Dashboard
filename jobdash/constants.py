"""Shared constants: statuses, labels, colors."""

# Pipeline order. The last three are end states.
STATUSES = [
    "applied",
    "screen",
    "assessment",
    "interview",
    "offer",
    "rejected",
    "withdrawn",
    "ghosted",
]
OPEN_STATUSES = ["applied", "screen", "assessment", "interview", "offer"]
FUNNEL_STAGES = ["applied", "screen", "assessment", "interview", "offer"]

STATUS_LABEL = {s: s.capitalize() for s in STATUSES}

EMAIL_LABELS = [
    "application_received",
    "screen_request",
    "assessment",
    "interview_invite",
    "scheduling_link",
    "rejection",
    "offer",
    "update_other",
    "not_job",
]
EMAIL_LABEL_TEXT = {
    "application_received": "Application received",
    "screen_request": "Screen request",
    "assessment": "Assessment",
    "interview_invite": "Interview invite",
    "scheduling_link": "Scheduling link",
    "rejection": "Rejection",
    "offer": "Offer",
    "update_other": "Other update",
    "not_job": "Not job-related",
}
# Which status an email label implies (used on the Review page).
LABEL_TO_STATUS = {
    "application_received": "applied",
    "screen_request": "screen",
    "assessment": "assessment",
    "interview_invite": "interview",
    "rejection": "rejected",
    "offer": "offer",
}

TRACKS = ["AI/ML", "Fintech", "Forward deployed", "AI security", "Quant", "Medtech", "Other"]
INTERVIEW_KINDS = ["Recruiter screen", "Hiring manager", "Technical", "Onsite", "Final", "Other"]

# Colors (validated reference palette): one series hue + status hues.
BLUE = "#2a78d6"
BLUE_LIGHT = "#86b6ef"
CRITICAL = "#d03b3b"
TEXT_PRIMARY = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
GRID = "#e4e3df"
