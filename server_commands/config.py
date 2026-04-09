"""
server_commands/config.py
~~~~~~~~~~~~~~~~~~~~~~~~~
Re-exports ServerConfig and ServerConfigStore from the easycord package.

Import directly from easycord instead::

    from easycord import ServerConfig, ServerConfigStore
"""

from easycord.server_config import ServerConfig, ServerConfigStore

__all__ = ["ServerConfig", "ServerConfigStore"]
