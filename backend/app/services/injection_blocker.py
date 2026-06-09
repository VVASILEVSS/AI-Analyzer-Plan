"""
AI Analyzer v2.1 — Prompt Injection Blocker
20+ regex patterns to detect and block prompt injection attempts.
Migrated from v1 Injection_blocker.py — no functional changes.
"""

import logging
import re
from typing import Optional

from app.core.config import logger

logger = logging.getLogger("ai_analyzer.injection")


class InjectionBlocker:
    """Detects and blocks prompt injection attempts in user input."""

    def __init__(self):
        self._patterns = self._build_patterns()
        self._block_count = 0

    @staticmethod
    def _build_patterns() -> list[dict]:
        """
        Build the list of regex patterns for injection detection.
        Each pattern has: regex, description, severity (low/medium/high).
        """
        patterns = [
            # System prompt manipulation
            {
                "regex": r"(?i)(ignore\s+(all\s+)?previous\s+(instructions|prompts|rules))",
                "desc": "System prompt override attempt",
                "severity": "high",
            },
            {
                "regex": r"(?i)(you\s+are\s+(now|no\s+longer|a)\s+(not|an?\s+)(ai|assistant|model))",
                "desc": "Role hijacking attempt",
                "severity": "high",
            },
            {
                "regex": r"(?i)(new\s+(instructions?|prompt|rules|system))",
                "desc": "Instruction replacement attempt",
                "severity": "high",
            },
            {
                "regex": r"(?i)(forget\s+(everything|all|your|the)\s+(instructions?|rules|training))",
                "desc": "Training memory wipe attempt",
                "severity": "high",
            },

            # Output manipulation
            {
                "regex": r"(?i)(output\s+(only|just|exactly)\s+(the|this|that)\s+(json|code|text|data|result))",
                "desc": "Output format manipulation",
                "severity": "medium",
            },
            {
                "regex": r"(?i)(respond\s+(with|using)\s+(only|just)\s+(json|code|text|data))",
                "desc": "Response format override",
                "severity": "medium",
            },
            {
                "regex": r"(?i)(print|echo|return|display|show)\s+(the|your|all)\s+(system|secret|hidden|internal|api)",
                "desc": "Internal info extraction",
                "severity": "high",
            },

            # Code injection
            {
                "regex": r"(?i)(execute|run|eval|exec)\s+(this|the|following)\s+(code|command|script|program)",
                "desc": "Code execution attempt",
                "severity": "high",
            },
            {
                "regex": r"(?i)(import\s+(os|subprocess|sys|shutil|pathlib)\s*[;,\n])",
                "desc": "Python module import attempt",
                "severity": "high",
            },
            {
                "regex": r"(?i)(rm\s+-rf|del\s+/s|format\s+[a-z]:|shutdown)",
                "desc": "Destructive command attempt",
                "severity": "high",
            },
            {
                "regex": r"(?i)(curl|wget|nc|ncat|netcat)\s+(https?://|-[a-z])",
                "desc": "Network request attempt",
                "severity": "high",
            },

            # Data exfiltration
            {
                "regex": r"(?i)(send|post|upload|transmit)\s+(this|the|data|to)\s+(https?://|to|at)",
                "desc": "Data exfiltration attempt",
                "severity": "high",
            },
            {
                "regex": r"(?i)(what\s+(is|are)\s+(your|the|my)\s+(api|secret|private|admin|system)\s*(key|token|password|credentials?))",
                "desc": "Credential extraction attempt",
                "severity": "high",
            },

            # Jailbreak patterns
            {
                "regex": r"(?i)(jailbreak|dan\s+\d+|developer\s+mode|god\s+mode)",
                "desc": "Known jailbreak pattern",
                "severity": "high",
            },
            {
                "regex": r"(?i)(act\s+as|pretend\s+(you're|to\s+be)|roleplay\s+as)\s+(a\s+)?(hacker|malicious|evil|unrestricted)",
                "desc": "Malicious roleplay attempt",
                "severity": "high",
            },
            {
                "regex": r"(?i)(bypass|circumvent|override|disable)\s+(the|your|all|safety|security|filter|restriction)",
                "desc": "Safety bypass attempt",
                "severity": "high",
            },

            # Markdown/formatting abuse
            {
                "regex": r"(?i)```(system|admin|hidden|secret)\s*\n",
                "desc": "Hidden code block injection",
                "severity": "medium",
            },
            {
                "regex": r"(?i)<(system|admin|hidden|secret|instruction)[^>]*>",
                "desc": "HTML tag injection attempt",
                "severity": "medium",
            },

            # Encoding tricks
            {
                "regex": r"(?i)(base64|hex|unicode|url)\s*(encode|decode|of|for)",
                "desc": "Encoding obfuscation attempt",
                "severity": "medium",
            },
            {
                "regex": r"\\x[0-9a-f]{2}.*\\x[0-9a-f]{2}",
                "desc": "Hex-encoded string detected",
                "severity": "medium",
            },

            # Multi-turn manipulation
            {
                "regex": r"(?i)(in\s+the\s+(next|previous|following)\s+(turn|message|response))",
                "desc": "Multi-turn manipulation attempt",
                "severity": "low",
            },
            {
                "regex": r"(?i)(when\s+i\s+(say|type|write|tell\s+you)\s+(to|that))",
                "desc": "Trigger word injection",
                "severity": "low",
            },
            {
                "regex": r"(?i)(from\s+now\s+on|going\s+forward|henceforth|hereafter)",
                "desc": "Persistent instruction attempt",
                "severity": "medium",
            },

            # Misc
            {
                "regex": r"(?i)(sudo|admin|root|privilege)\s+(access|mode|command|exec)",
                "desc": "Privilege escalation attempt",
                "severity": "high",
            },
            {
                "regex": r"(?i)\b(SET\s|GET\s|POST\s|PUT\s|DELETE\s)(?:[A-Z_]+\s*=|http)",
                "desc": "HTTP method injection",
                "severity": "medium",
            },
        ]

        return patterns

    def check(self, text: str) -> dict:
        """
        Check text for injection patterns.
        Returns: {"safe": bool, "threats": list, "severity": str}
        """
        if not text:
            return {"safe": True, "threats": [], "severity": "none"}

        threats = []
        max_severity = 0
        severity_map = {"low": 1, "medium": 2, "high": 3}

        for pattern in self._patterns:
            match = re.search(pattern["regex"], text)
            if match:
                threats.append({
                    "pattern": pattern["regex"][:50],
                    "description": pattern["desc"],
                    "severity": pattern["severity"],
                    "matched_text": match.group()[:100],
                })
                sev = severity_map.get(pattern["severity"], 0)
                max_severity = max(max_severity, sev)

        if threats:
            self._block_count += 1
            severity_str = {1: "low", 2: "medium", 3: "high"}.get(max_severity, "unknown")
            logger.warning(
                f"Injection detected: {len(threats)} threat(s), "
                f"max severity: {severity_str}, total blocks: {self._block_count}"
            )

        return {
            "safe": len(threats) == 0,
            "threats": threats,
            "severity": {1: "low", 2: "medium", 3: "high"}.get(max_severity, "none"),
        }

    def sanitize(self, text: str) -> str:
        """
        Remove detected injection patterns from text.
        Returns cleaned text.
        """
        cleaned = text
        for pattern in self._patterns:
            cleaned = re.sub(pattern["regex"], "[FILTERED]", cleaned)
        return cleaned

    @property
    def block_count(self) -> int:
        return self._block_count

    def get_patterns_count(self) -> int:
        return len(self._patterns)


# Singleton instance
injection_blocker = InjectionBlocker()
