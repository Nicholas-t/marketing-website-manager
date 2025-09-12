import datetime

def format_date(date_string):
    """Format date string for display"""
    try:
        if date_string:
            dt = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
            return dt.strftime("%Y-%m-%d %H:%M")
    except (ValueError, AttributeError, TypeError):
        return str(date_string) if date_string else "N/A"
    return "N/A"
