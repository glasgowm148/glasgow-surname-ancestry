"""Restore maintained reviewed collection views after generated branch rebuilds."""
from pathlib import Path

from tools import publish_opr_birth_review, publish_opr_death_review


def publish(web: Path) -> dict[str, int]:
    # These source publishers render reviewed index conclusions; finalization
    # must not reapply historical dossier qualifications or change identities.
    counts = publish_opr_birth_review.repair(web)
    counts.update(publish_opr_death_review.repair(web=web, qualify_person=False))
    return counts
