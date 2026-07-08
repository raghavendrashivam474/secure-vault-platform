"""
modules/password_vault/core/strength.py

Password strength analyzer for the Password Vault module.
"""

import re
from dataclasses import dataclass, field


COMMON_PASSWORDS = {
    "password", "123456", "qwerty", "admin", "letmein",
    "welcome", "monkey", "dragon", "master", "abc123",
    "iloveyou", "111111", "password1", "test123"
}


@dataclass
class StrengthResult:
    """
    Password strength analysis result.

    Attributes:
        score:           0-100 numerical score.
        label:           Weak, Fair, Strong, Very Strong.
        suggestions:     List of improvement recommendations.
    """
    score:       int
    label:       str
    suggestions: list[str] = field(default_factory=list)


def analyze_password(password: str) -> StrengthResult:
    """
    Analyze a password and return strength assessment.

    Args:
        password: The password to analyze.

    Returns:
        A StrengthResult with score, label, and suggestions.
    """
    if not password:
        return StrengthResult(0, "Weak", ["Password is empty."])

    score       = 0
    suggestions = []

    # Length scoring
    length = len(password)
    if length >= 16:
        score += 30
    elif length >= 12:
        score += 22
    elif length >= 8:
        score += 12
    else:
        score += 5
        suggestions.append("Use at least 12 characters.")

    # Character diversity
    has_upper   = bool(re.search(r"[A-Z]", password))
    has_lower   = bool(re.search(r"[a-z]", password))
    has_digit   = bool(re.search(r"\d",    password))
    has_symbol  = bool(re.search(r"[^A-Za-z0-9]", password))

    diversity = sum([has_upper, has_lower, has_digit, has_symbol])
    score += diversity * 15

    if not has_upper:
        suggestions.append("Add uppercase letters.")
    if not has_lower:
        suggestions.append("Add lowercase letters.")
    if not has_digit:
        suggestions.append("Add numbers.")
    if not has_symbol:
        suggestions.append("Add special characters.")

    # Repetition penalty
    if re.search(r"(.)\1{2,}", password):
        score -= 10
        suggestions.append("Avoid repeated characters.")

    # Sequential pattern penalty
    if _has_sequential(password):
        score -= 10
        suggestions.append("Avoid sequential patterns like 'abc' or '123'.")

    # Common password check
    if password.lower() in COMMON_PASSWORDS:
        score = min(score, 20)
        suggestions.append("This is a commonly used password.")

    score = max(0, min(100, score))

    if score >= 80:
        label = "Very Strong"
    elif score >= 60:
        label = "Strong"
    elif score >= 40:
        label = "Fair"
    else:
        label = "Weak"

    return StrengthResult(score=score, label=label, suggestions=suggestions)


def _has_sequential(password: str) -> bool:
    """Check for sequential character patterns."""
    sequences = ["abcdefghijklmnopqrstuvwxyz", "0123456789", "qwertyuiop"]
    lower = password.lower()

    for seq in sequences:
        for i in range(len(seq) - 2):
            if seq[i:i+3] in lower:
                return True
    return False
