# utils.py (you can create this file anywhere in your app)

from .models import IDTracker

def generate_custom_id(prefix: str, tracker_name: str, digits=3):
    """
    Generate an ID with a given prefix and number of digits using IDTracker.
    Example: generate_custom_id("D", "department", 3) -> 'D001'
             generate_custom_id("OFFD", "officer", 4) -> 'OFFD0001'
    """
    tracker, _ = IDTracker.objects.get_or_create(name=tracker_name)
    tracker.last_used += 1
    tracker.save()

    return f"{prefix}{tracker.last_used:0{digits}d}"
