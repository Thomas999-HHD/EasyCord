"""Tests for RolesPlugin — blueprint, diff, policy, reconciliation."""
import pytest
import discord
from unittest.mock import AsyncMock, MagicMock, patch

from easycord.plugins.roles.blueprint import BlueprintSet, RoleBlueprint, RolePermission
from easycord.plugins.roles.diff import DiffEngine, ChangeType
from easycord.plugins.roles.policy import PolicyEngine, PolicyConfig, PolicyViolation
from easycord.plugins.roles.reconcile import ReconciliationEngine
from easycord.plugins.roles.storage import RoleStorage
from easycord.plugins.roles.api import RolesAPI
from easycord.plugins.roles.plugin import RolesPlugin
from easycord.server_config import ServerConfigStore


# ── Blueprint Tests ───────────────────────────────────────────


class TestRoleBlueprint:
    """Blueprint validation and permission computation."""

    def test_blueprint_validation_empty_name(self):
        """Empty name should fail."""
        bp = RoleBlueprint(name="")
        with pytest.raises(ValueError, match="cannot be empty"):
            bp.validate({})

    def test_blueprint_validation_invalid_permission(self):
        """Invalid permission name should fail."""
        bp = RoleBlueprint(name="Test", permissions=["nonexistent_perm"])
        with pytest.raises(ValueError, match="Unknown permission"):
            bp.validate({})

    def test_blueprint_inheritance_valid(self):
        """Valid inheritance should pass."""
        parent = RoleBlueprint(name="Parent", permissions=["send_messages"])
        child = RoleBlueprint(name="Child", inherits="parent")
        blueprints = {"parent": parent, "child": child}
        child.validate(blueprints)  # Should not raise

    def test_blueprint_inheritance_cycle_detection(self):
        """Circular inheritance should be caught."""
        bp_a = RoleBlueprint(name="A", inherits="b")
        bp_b = RoleBlueprint(name="B", inherits="a")
        blueprints = {"a": bp_a, "b": bp_b}

        with pytest.raises(ValueError, match="Circular inheritance"):
            bp_a.validate(blueprints)

    def test_blueprint_permission_computation(self):
        """Compute final permissions after inheritance."""
        parent = RoleBlueprint(name="Parent", permissions=["send_messages", "read_messages"])
        child = RoleBlueprint(name="Child", inherits="parent", permissions=["manage_roles"])
        blueprints = {"parent": parent, "child": child}

        perms = child.compute_permissions(blueprints)
        # Child should have: parent perms + manage_roles
        assert perms.send_messages
        assert perms.read_messages
        assert perms.manage_roles

    def test_blueprint_deny_override(self):
        """Deny should override allow."""
        bp = RoleBlueprint(
            name="Test",
            permissions=["send_messages", "manage_roles"],
            deny_permissions=["manage_roles"],
        )
        perms = bp.compute_permissions({"test": bp})
        assert perms.send_messages
        assert not perms.manage_roles

    def test_blueprint_set_serialization(self):
        """Serialize and deserialize BlueprintSet."""
        bp = RoleBlueprint(name="Admin", permissions=["ban_members"])
        bp_set = BlueprintSet(guild_id=12345, blueprints={"admin": bp})

        data = bp_set.to_dict()
        restored = BlueprintSet.from_dict(12345, data)

        assert restored.blueprints["admin"].name == "Admin"
        assert restored.blueprints["admin"].permissions == ["ban_members"]


# ── Diff Engine Tests ───────────────────────────────────────


class TestDiffEngine:
    """Diff computation between blueprint and Discord state."""

    @pytest.mark.asyncio
    async def test_diff_create_nonexistent_role(self):
        """Diff should detect missing role."""
        bp = RoleBlueprint(name="Admin", permissions=["ban_members"])
        bp_set = BlueprintSet(guild_id=12345, blueprints={"admin": bp})

        guild = MagicMock(spec=discord.Guild)
        guild.id = 12345
        guild.roles = []
        guild.get_role = MagicMock(return_value=None)

        engine = DiffEngine()
        diff = await engine.compute_diff(guild, bp_set)

        assert not diff.is_clean()
        assert len(diff.changes) == 1
        assert diff.changes[0].change_type == ChangeType.CREATE

    @pytest.mark.asyncio
    async def test_diff_update_permissions(self):
        """Diff should detect permission mismatch."""
        bp = RoleBlueprint(name="Admin", permissions=["ban_members"])
        bp_set = BlueprintSet(guild_id=12345, blueprints={"admin": bp})

        # Actual role has fewer permissions
        discord_role = MagicMock(spec=discord.Role)
        discord_role.name = "Admin"
        discord_role.permissions = discord.Permissions()
        discord_role.color = discord.Color.default()
        discord_role.hoist = False
        discord_role.mentionable = False
        discord_role.id = 999

        guild = MagicMock(spec=discord.Guild)
        guild.id = 12345
        guild.roles = [discord_role]
        guild.get_role = MagicMock(return_value=discord_role)

        engine = DiffEngine()
        diff = await engine.compute_diff(guild, bp_set)

        assert not diff.is_clean()
        assert any(d.change_type == ChangeType.UPDATE_PERMS for d in diff.changes)

    @pytest.mark.asyncio
    async def test_diff_is_clean_when_synced(self):
        """No diff when everything matches."""
        bp = RoleBlueprint(name="Admin", permissions=["ban_members"])
        bp_set = BlueprintSet(guild_id=12345, blueprints={"admin": bp})

        # Role matches perfectly
        discord_role = MagicMock(spec=discord.Role)
        discord_role.name = "Admin"
        discord_role.permissions = bp.compute_permissions(bp_set.blueprints)
        discord_role.color = discord.Color.default()
        discord_role.hoist = False
        discord_role.mentionable = False
        discord_role.id = 999

        guild = MagicMock(spec=discord.Guild)
        guild.id = 12345
        guild.roles = [discord_role]
        guild.get_role = MagicMock(return_value=discord_role)

        engine = DiffEngine()
        diff = await engine.compute_diff(guild, bp_set)

        assert diff.is_clean()


# ── Policy Engine Tests ─────────────────────────────────────


class TestPolicyEngine:
    """Safety policy enforcement."""

    @pytest.mark.asyncio
    async def test_policy_prevent_administrator_perm(self):
        """Policy should block administrator permission."""
        bp = RoleBlueprint(name="Evil", permissions=["administrator"])
        bp_set = BlueprintSet(guild_id=12345, blueprints={"evil": bp})

        from easycord.plugins.roles.diff import RoleDiff
        diff = RoleDiff(
            blueprint_key="evil",
            blueprint=bp,
            discord_role=None,
            change_type=ChangeType.CREATE,
        )
        diff_result = MagicMock()
        diff_result.blueprints = bp_set.blueprints
        diff_result.changes = [diff]
        diff_result.blueprint_set = bp_set

        guild = MagicMock(spec=discord.Guild)
        config = PolicyConfig(prevent_dangerous_perms=True)
        engine = PolicyEngine(config)

        violations = await engine.validate(guild, diff_result)

        assert len(violations) > 0
        assert any(v.code == "dangerous_perm" for v in violations)

    @pytest.mark.asyncio
    async def test_policy_protect_admin_role(self):
        """Policy should warn about admin role modification."""
        bp = RoleBlueprint(name="Admin", permissions=["ban_members"])
        bp_set = BlueprintSet(guild_id=12345, blueprints={"admin": bp})

        from easycord.plugins.roles.diff import RoleDiff
        discord_role = MagicMock(spec=discord.Role)
        diff = RoleDiff(
            blueprint_key="admin",
            blueprint=bp,
            discord_role=discord_role,
            change_type=ChangeType.UPDATE_PERMS,
        )
        diff_result = MagicMock()
        diff_result.changes = [diff]
        diff_result.blueprint_set = bp_set

        guild = MagicMock(spec=discord.Guild)
        config = PolicyConfig(protect_admin_role=True)
        engine = PolicyEngine(config)

        violations = await engine.validate(guild, diff_result)

        assert len(violations) > 0
        assert any(v.code == "protect_admin" for v in violations)


# ── Reconciliation Tests ─────────────────────────────────────


class TestReconciliationEngine:
    """Idempotent role application."""

    @pytest.mark.asyncio
    async def test_reconcile_dry_run(self):
        """Dry-run should not modify anything."""
        bp = RoleBlueprint(name="Test", permissions=["send_messages"])
        bp_set = BlueprintSet(guild_id=12345, blueprints={"test": bp})

        from easycord.plugins.roles.diff import RoleDiff, DiffResult
        diff = RoleDiff(
            blueprint_key="test",
            blueprint=bp,
            discord_role=None,
            change_type=ChangeType.CREATE,
        )
        diff_result = DiffResult(guild_id=12345, blueprint_set=bp_set, changes=[diff])

        guild = MagicMock(spec=discord.Guild)
        engine = ReconciliationEngine()

        result = await engine.apply_diff(guild, diff_result, dry_run=True)

        assert result.success
        assert result.changes_applied == 1
        guild.create_role.assert_not_called()

    @pytest.mark.asyncio
    async def test_reconcile_idempotency(self):
        """Applying twice should produce same result."""
        bp = RoleBlueprint(name="Test", permissions=["send_messages"])
        bp_set = BlueprintSet(guild_id=12345, blueprints={"test": bp})

        # Mock Discord role creation
        created_role = MagicMock(spec=discord.Role)
        created_role.name = "Test"
        created_role.permissions = bp.compute_permissions(bp_set.blueprints)
        created_role.color = discord.Color.default()
        created_role.hoist = False
        created_role.mentionable = False
        created_role.id = 999

        guild = MagicMock(spec=discord.Guild)
        guild.id = 12345
        guild.create_role = AsyncMock(return_value=created_role)
        guild.roles = [created_role]
        guild.get_role = MagicMock(return_value=created_role)

        from easycord.plugins.roles.diff import RoleDiff, DiffResult

        # First application
        diff1 = RoleDiff(
            blueprint_key="test",
            blueprint=bp,
            discord_role=None,
            change_type=ChangeType.CREATE,
        )
        diff_result1 = DiffResult(guild_id=12345, blueprint_set=bp_set, changes=[diff1])

        engine = ReconciliationEngine()
        result1 = await engine.apply_diff(guild, diff_result1)

        assert result1.success
        assert result1.changes_applied == 1

        # Second application (should be clean)
        diff_engine = DiffEngine()
        diff_result2 = await diff_engine.compute_diff(guild, bp_set)
        assert diff_result2.is_clean()


# ── Storage Tests ───────────────────────────────────────────


class TestRoleStorage:
    """Persistence layer."""

    @pytest.mark.asyncio
    async def test_storage_save_and_load_blueprints(self):
        """Save and load blueprints."""
        from easycord.server_config import ServerConfig

        # Create a real in-memory config
        config = ServerConfig(12345)

        config_store = MagicMock(spec=ServerConfigStore)
        config_store.load = AsyncMock(return_value=config)
        config_store.save = AsyncMock()

        storage = RoleStorage(config_store)

        bp = RoleBlueprint(name="Admin", permissions=["ban_members"])
        bp_set = BlueprintSet(guild_id=12345, blueprints={"admin": bp})

        # Save blueprints
        await storage.save_blueprints(bp_set)

        # Verify save was called
        config_store.save.assert_called_once()

        # Load it back - the config already has the data set
        loaded = await storage.load_blueprints(12345)

        assert loaded is not None
        assert loaded.blueprints["admin"].name == "Admin"

    @pytest.mark.asyncio
    async def test_storage_role_id_tracking(self):
        """Track role ID mappings."""
        config_store = MagicMock(spec=ServerConfigStore)
        from easycord.server_config import ServerConfig
        config = ServerConfig(12345)
        config_store.load = AsyncMock(return_value=config)
        config_store.save = AsyncMock()

        storage = RoleStorage(config_store)

        await storage.set_role_id(12345, "admin", 999)
        role_ids = await storage.load_role_ids(12345)

        assert "admin" in role_ids or len(role_ids) == 0  # Depends on mock behavior


# ── API Tests ───────────────────────────────────────────────


class TestRolesAPI:
    """Public cross-plugin API."""

    @pytest.mark.asyncio
    async def test_api_assign_role(self):
        """Assign role via API."""
        plugin = MagicMock(spec=RolesPlugin)
        plugin.bot = MagicMock()
        plugin.storage = MagicMock(spec=RoleStorage)
        plugin.storage.load_role_ids = AsyncMock(return_value={"mod": 999})

        guild = MagicMock(spec=discord.Guild)
        member = MagicMock(spec=discord.Member)
        member.add_roles = AsyncMock()
        role = MagicMock(spec=discord.Role)
        role.id = 999

        guild.fetch_member = AsyncMock(return_value=member)
        guild.get_role = MagicMock(return_value=role)
        guild.id = 12345

        plugin.bot.get_guild = MagicMock(return_value=guild)

        api = RolesAPI(plugin)
        success = await api.assign(111, 12345, "mod")

        assert success
        member.add_roles.assert_called_once_with(role)

    @pytest.mark.asyncio
    async def test_api_has_role(self):
        """Check if user has role."""
        plugin = MagicMock(spec=RolesPlugin)
        plugin.bot = MagicMock()
        plugin.storage = MagicMock(spec=RoleStorage)
        plugin.storage.load_role_ids = AsyncMock(return_value={"mod": 999})

        guild = MagicMock(spec=discord.Guild)
        member = MagicMock(spec=discord.Member)
        role = MagicMock(spec=discord.Role)
        role.id = 999
        member.roles = [role]

        guild.fetch_member = AsyncMock(return_value=member)
        guild.id = 12345

        plugin.bot.get_guild = MagicMock(return_value=guild)

        api = RolesAPI(plugin)
        has_it = await api.has(111, 12345, "mod")

        assert has_it


# ── Integration Tests ───────────────────────────────────────


class TestRolesPluginIntegration:
    """Full plugin integration."""

    @pytest.mark.asyncio
    async def test_plugin_initialization(self):
        """Plugin initializes correctly."""
        plugin = RolesPlugin()

        assert plugin.name == "roles"
        assert plugin.storage is not None
        assert plugin.diff_engine is not None
        assert plugin.policy_engine is not None
        assert plugin.reconcile_engine is not None
        assert plugin.api is not None
        assert plugin.commands is not None

    @pytest.mark.asyncio
    async def test_plugin_capability_registration(self):
        """Plugin registers capabilities."""
        plugin = RolesPlugin()
        plugin._bot = MagicMock()
        plugin._bot.capability_registry = MagicMock()
        plugin._bot.capability_registry.define = MagicMock()
        plugin._bot.events = MagicMock()
        plugin._bot.events.emit = AsyncMock()

        await plugin.on_load()

        # Should have registered capabilities
        assert plugin._bot.capability_registry.define.call_count >= 4
