import random  # only if you want random fallbacks, otherwise not needed
from django.db import transaction
from .models import DistrictOfficerIDTracker

@transaction.atomic
def generate_do_id(district) -> str:
    """
    Generate a unique officer_id like DO6IDK where:
    - 6 is an auto‑incrementing integer per district
    - IDK is district.code
    """
    tracker, _ = (
        DistrictOfficerIDTracker.objects
        .select_for_update()
        .get_or_create(district=district)
    )
    tracker.last_number += 1
    tracker.save(update_fields=["last_number"])

    return f"DO{tracker.last_number}{district.code.upper()}"
