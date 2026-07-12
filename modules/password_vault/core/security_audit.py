"""
modules/password_vault/core/security_audit.py

Vault-wide security audit engine.

Analyzes all password entries for security issues.
Never persists plaintext passwords.
Never logs sensitive credential material.
"""

from datetime import datetime, timezone
from typing import Callable

from modules.password_vault.models.password_entry import PasswordEntry
from modules.password_vault.models.audit_result import AuditResult, AuditFinding
from modules.password_vault.core.strength import analyze_password, COMMON_PASSWORDS
from modules.password_vault.core.aging_engine import (
    analyze_entry as analyze_age,
    AGE_STATUS_AGING, AGE_STATUS_OLD, AGE_STATUS_CRITICAL
)
from modules.password_vault.core.reuse_detector import (
    detect_reused_passwords, count_reused_entries
)


def run_audit(
    entries: list[PasswordEntry],
    master_password: str,
    decrypt_fn: Callable
) -> AuditResult:
    """
    Run a complete security audit on the password vault.

    Args:
        entries:         All password entries to audit.
        master_password: Session master password for decryption.
        decrypt_fn:      Callable(encrypted_b64, password) -> plaintext.

    Returns:
        A populated AuditResult object.
    """
    result = AuditResult()
    result.total_credentials = len(entries)
    result.generated_at      = datetime.now(timezone.utc).isoformat()

    # Detect reuse first (needs decryption)
    reuse_groups = detect_reused_passwords(entries, master_password, decrypt_fn)
    reused_entry_ids = set()
    for ids in reuse_groups.values():
        reused_entry_ids.update(ids)

    result.reused_count = len(reused_entry_ids)

    # Analyze each entry
    for entry in entries:
        # Strength classification
        if entry.strength_score >= 60:
            result.strong_count += 1
        else:
            result.weak_count += 1
            result.findings.append(AuditFinding(
                entry_id     = entry.id,
                entry_title  = entry.title,
                finding_type = "weak",
                severity     = "warning",
                detail       = f"Password strength score: {entry.strength_score}/100"
            ))

        # Age classification
        aging = analyze_age(entry)
        if aging.status == AGE_STATUS_AGING:
            result.aging_count += 1
            result.findings.append(AuditFinding(
                entry_id     = entry.id,
                entry_title  = entry.title,
                finding_type = "aging",
                severity     = "info",
                detail       = f"Password is {aging.age_days} days old"
            ))
        elif aging.status == AGE_STATUS_OLD:
            result.old_count += 1
            result.findings.append(AuditFinding(
                entry_id     = entry.id,
                entry_title  = entry.title,
                finding_type = "old",
                severity     = "warning",
                detail       = f"Password is {aging.age_days} days old"
            ))
        elif aging.status == AGE_STATUS_CRITICAL:
            result.critical_age_count += 1
            result.findings.append(AuditFinding(
                entry_id     = entry.id,
                entry_title  = entry.title,
                finding_type = "critical_age",
                severity     = "critical",
                detail       = f"Password is {aging.age_days} days old"
            ))

        # Reuse finding
        if entry.id in reused_entry_ids:
            result.findings.append(AuditFinding(
                entry_id     = entry.id,
                entry_title  = entry.title,
                finding_type = "reused",
                severity     = "warning",
                detail       = "Password used across multiple entries"
            ))

        # Common password check (needs plaintext)
        try:
            plaintext = decrypt_fn(entry.password_encrypted, master_password)
            if plaintext and plaintext.lower() in COMMON_PASSWORDS:
                result.common_count += 1
                result.findings.append(AuditFinding(
                    entry_id     = entry.id,
                    entry_title  = entry.title,
                    finding_type = "common",
                    severity     = "critical",
                    detail       = "Password is on common password blacklist"
                ))
            plaintext = None
        except Exception:
            pass

    return result


def calculate_hygiene_score(result: AuditResult) -> int:
    """
    Calculate a vault hygiene score from 0 to 100.

    Args:
        result: The audit result.

    Returns:
        Score integer.
    """
    if result.total_credentials == 0:
        return 100

    total = result.total_credentials

    # Weighted penalties
    weak_ratio      = result.weak_count / total
    reuse_ratio     = result.reused_count / total
    old_ratio       = result.old_count / total
    critical_ratio  = result.critical_age_count / total
    common_ratio    = result.common_count / total

    # Base score
    score = 100

    # Apply penalties
    score -= int(weak_ratio     * 25)
    score -= int(reuse_ratio    * 25)
    score -= int(old_ratio      * 15)
    score -= int(critical_ratio * 25)
    score -= int(common_ratio   * 30)

    return max(0, min(100, score))
