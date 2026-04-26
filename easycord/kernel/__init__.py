"""EasyCord kernel — decoupled, swappable subsystems.

These are internal (easycord.kernel.*) and not part of the public API.
But they ARE replaceable via adapters and Protocol-based design.
"""

from .event_bus import Event, EventBus, EventHandler
from .capability import Capability, CapabilityRegistry, CapabilityError

__all__ = [
    "Event",
    "EventBus",
    "EventHandler",
    "Capability",
    "CapabilityRegistry",
    "CapabilityError",
]
