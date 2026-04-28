"""Optional first-party plugins."""
from .announcements import AnnouncementsPlugin
from .autoreply import AutoReplyPlugin
from .base import GuildPlugin, IntegrationPlugin, JsonConfigPlugin
from .levels import LevelsPlugin
from .polls import PollsPlugin
from .tags import TagsPlugin
from .welcome import WelcomePlugin

__all__ = [
    "AnnouncementsPlugin",
    "AutoReplyPlugin",
    "GuildPlugin",
    "IntegrationPlugin",
    "JsonConfigPlugin",
    "LevelsPlugin",
    "PollsPlugin",
    "TagsPlugin",
    "WelcomePlugin",
]
