REPORT_FIELDS = ("overview", "process", "evidenceDescription", "preliminaryConclusion")
LEGACY_FIELDS = {"evidenceDescription": "evidence", "preliminaryConclusion": "conclusion"}


def normalize_report_content(value) -> dict[str, str]:
    """Safely present legacy JSON as the fixed M8.3 report contract."""
    raw = value if isinstance(value, dict) else {}
    result = {}
    for field in REPORT_FIELDS:
        candidate = raw.get(field)
        if not isinstance(candidate, str):
            candidate = raw.get(LEGACY_FIELDS[field]) if field in LEGACY_FIELDS else ""
        result[field] = candidate if isinstance(candidate, str) else ""
    return result
