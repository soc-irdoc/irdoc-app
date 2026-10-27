"""Final disposition of an investigation (#124).

Required when an incident is closed, so every closed incident records how the
investigation ended. Incidents closed before 0.1.8 have none (NULL).
"""
from typing import Literal

DISPOSITIONS = (
    "tp_remediated",
    "tp_accepted_risk",
    "tp_third_party",
    "fp_benign",
    "fp_tuning_required",
    "inconclusive",
)

DISPOSITION_LABELS = {
    "tp_remediated": "True Positive - Remediated / Contained",
    "tp_accepted_risk": "True Positive - Accepted Risk",
    "tp_third_party": "True Positive - Third Party Handled",
    "fp_benign": "False Positive - Benign",
    "fp_tuning_required": "False Positive - Tuning Required",
    "inconclusive": "Unknown - Inconclusive",
}

Disposition = Literal[
    "tp_remediated",
    "tp_accepted_risk",
    "tp_third_party",
    "fp_benign",
    "fp_tuning_required",
    "inconclusive",
]
