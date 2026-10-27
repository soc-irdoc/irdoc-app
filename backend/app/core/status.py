"""Incident statuses, in workflow order (the order the incidents list sorts by, #128)."""
from typing import Literal

STATUSES = ("open", "contained", "monitoring", "closed")

IncidentStatus = Literal["open", "contained", "monitoring", "closed"]
