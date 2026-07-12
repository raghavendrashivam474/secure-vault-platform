"""
modules/password_vault/models/audit_result.py

Security audit result data model.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AuditFinding:
    """
    Represents a single audit finding for one entry.

    Attributes:
        entry_id:      The password entry ID.
        entry_title:   Display title of the entry.
        finding_type:  Type of issue ('weak', 'reused', 'aging', 'old', etc).
        severity:      'critical', 'warning', 'info'.
        detail:        Description of the finding.
    """
    entry_id:     int
    entry_title:  str
    finding_type: str
    severity:     str
    detail:       str


@dataclass
class AuditResult:
    """
    Complete vault-wide security audit result.

    Attributes:
        total_credentials:    Total number of password entries.
        strong_count:         Passwords with strength >= 60.
        weak_count:           Passwords with strength < 60.
        reused_count:         Entries involved in password reuse.
        aging_count:          Passwords 90-179 days old.
        old_count:            Passwords 180-364 days old.
        critical_age_count:   Passwords 365+ days old.
        common_count:         Passwords matching common blacklist.
        findings:             List of all AuditFinding objects.
        generated_at:         ISO 8601 timestamp.
    """
    total_credentials:  int  = 0
    strong_count:       int  = 0
    weak_count:         int  = 0
    reused_count:       int  = 0
    aging_count:        int  = 0
    old_count:          int  = 0
    critical_age_count: int  = 0
    common_count:       int  = 0
    findings:           list[AuditFinding] = field(default_factory=list)
    generated_at:       str  = ""
