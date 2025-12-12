"""
Registry Versioning System

Tracks changes to the agent capability registry for versioning and change tracking.
"""

from typing import Dict
from datetime import datetime


class RegistryVersion:
    """
    Version tracking for the agent capability registry.
    
    Follows semantic versioning:
    - MAJOR: Backward incompatible changes (agent removal, schema changes)
    - MINOR: New agents added
    - PATCH: Agent updates, clarifications
    """
    
    def __init__(self, major: int = 1, minor: int = 0, patch: int = 0):
        """
        Initialize registry version.
        
        Args:
            major: Major version number
            minor: Minor version number
            patch: Patch version number
        """
        self.major = major
        self.minor = minor
        self.patch = patch
        self.created_at = datetime.utcnow()
        self.last_updated = datetime.utcnow()
    
    def increment_major(self) -> None:
        """Increment major version (backward incompatible changes)."""
        self.major += 1
        self.minor = 0
        self.patch = 0
        self.last_updated = datetime.utcnow()
    
    def increment_minor(self) -> None:
        """Increment minor version (new agents added)."""
        self.minor += 1
        self.patch = 0
        self.last_updated = datetime.utcnow()
    
    def increment_patch(self) -> None:
        """Increment patch version (agent updates)."""
        self.patch += 1
        self.last_updated = datetime.utcnow()
    
    def __str__(self) -> str:
        """String representation of version."""
        return f"{self.major}.{self.minor}.{self.patch}"
    
    def __repr__(self) -> str:
        """Representation of version."""
        return f"RegistryVersion(major={self.major}, minor={self.minor}, patch={self.patch})"
    
    def to_dict(self) -> Dict:
        """Convert version to dictionary."""
        return {
            "version": str(self),
            "major": self.major,
            "minor": self.minor,
            "patch": self.patch,
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat()
        }

