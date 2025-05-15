"""Utility functions for working with time and durations"""

def format_time(seconds):
    """Format seconds into human readable time

    Args:
        seconds (float): Number of seconds

    Returns:
        str: Formatted time string like "1h 30m 45s" or "45.5s"
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        seconds = seconds % 60
        return f"{minutes}m {seconds:.1f}s"
    else:
        hours = int(seconds / 3600)
        minutes = int((seconds % 3600) / 60)
        seconds = seconds % 60
        return f"{hours}h {minutes}m {seconds:.1f}s"
