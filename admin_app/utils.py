from django.db.models import F
from .models import IDTracker
from core_app.models import District
from district_officer.models import DistrictOfficerIDTracker

def generate_custom_id(prefix: str, tracker_name: str, digits=3):
    """
    Generate an ID with a given prefix and number of digits using IDTracker.
    Example: generate_custom_id("D", "Department", 3) -> 'D001'
             generate_custom_id("OFFD", "Officer", 4) -> 'OFFD0001'
    """
    tracker, _ = IDTracker.objects.get_or_create(name=tracker_name)
    tracker.last_used = F('last_used') + 1
    tracker.save()
    tracker.refresh_from_db()  # Reload to get the updated last_used value
    return f"{prefix}{tracker.last_used:0{digits}d}"
