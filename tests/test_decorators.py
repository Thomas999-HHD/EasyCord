from easycord.decorators import slash, on


# ── slash ─────────────────────────────────────────────────────────────────────

def test_slash_marks_function():
    @slash()
    async def cmd(ctx):
        pass

    assert cmd._easycord_slash is True


def test_slash_uses_function_name_by_default():
    @slash()
    async def my_command(ctx):
        pass

    assert my_command._easycord_slash_name == "my_command"


def test_slash_custom_name():
    @slash(name="custom")
    async def cmd(ctx):
        pass

    assert cmd._easycord_slash_name == "custom"


def test_slash_default_description():
    @slash()
    async def cmd(ctx):
        pass

    assert cmd._easycord_slash_description == "No description provided."


def test_slash_custom_description():
    @slash(description="Does a thing")
    async def cmd(ctx):
        pass

    assert cmd._easycord_slash_description == "Does a thing"


def test_slash_no_guild_id_by_default():
    @slash()
    async def cmd(ctx):
        pass

    assert cmd._easycord_slash_guild_id is None


def test_slash_custom_guild_id():
    @slash(guild_id=12345)
    async def cmd(ctx):
        pass

    assert cmd._easycord_slash_guild_id == 12345


def test_slash_returns_original_function():
    async def original(ctx):
        pass

    wrapped = slash()(original)
    assert wrapped is original


# ── on ────────────────────────────────────────────────────────────────────────

def test_on_marks_function():
    @on("message")
    async def handler(msg):
        pass

    assert handler._easycord_event is True


def test_on_stores_event_name():
    @on("member_join")
    async def handler(member):
        pass

    assert handler._easycord_event_name == "member_join"


def test_on_returns_original_function():
    async def original(msg):
        pass

    wrapped = on("message")(original)
    assert wrapped is original


def test_on_different_event_names():
    @on("message_delete")
    async def h1(msg):
        pass

    @on("reaction_add")
    async def h2(reaction, user):
        pass

    assert h1._easycord_event_name == "message_delete"
    assert h2._easycord_event_name == "reaction_add"
