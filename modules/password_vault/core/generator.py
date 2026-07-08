"""
modules/password_vault/core/generator.py

Password generator for the Password Vault module.
"""

import secrets
import string
from dataclasses import dataclass


@dataclass
class GeneratorPolicy:
    """
    Password generation policy.

    Attributes:
        length:              Password length (8-128).
        use_uppercase:       Include A-Z.
        use_lowercase:       Include a-z.
        use_numbers:         Include 0-9.
        use_symbols:         Include special characters.
        exclude_ambiguous:   Exclude 0, O, I, l, 1.
    """
    length:            int  = 16
    use_uppercase:     bool = True
    use_lowercase:     bool = True
    use_numbers:       bool = True
    use_symbols:       bool = True
    exclude_ambiguous: bool = False


AMBIGUOUS_CHARS = "0O1Il|"
SYMBOL_CHARS    = "!@#$%^&*()_+-=[]{}|;:,.<>?"


def generate_password(policy: GeneratorPolicy) -> str:
    """
    Generate a secure random password based on the policy.

    Args:
        policy: The generation policy.

    Returns:
        A generated password string.
    """
    charset = ""

    if policy.use_uppercase:
        charset += string.ascii_uppercase
    if policy.use_lowercase:
        charset += string.ascii_lowercase
    if policy.use_numbers:
        charset += string.digits
    if policy.use_symbols:
        charset += SYMBOL_CHARS

    if policy.exclude_ambiguous:
        for char in AMBIGUOUS_CHARS:
            charset = charset.replace(char, "")

    if not charset:
        charset = string.ascii_letters + string.digits

    length = max(8, min(128, policy.length))

    password = "".join(secrets.choice(charset) for _ in range(length))
    return password


def generate_multiple(policy: GeneratorPolicy, count: int = 5) -> list[str]:
    """
    Generate multiple passwords.

    Args:
        policy: The generation policy.
        count:  Number of passwords to generate.

    Returns:
        A list of generated password strings.
    """
    return [generate_password(policy) for _ in range(count)]
