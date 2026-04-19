"""Tests for easycord.builders.embed — EmbedBuilder."""
import discord
import pytest

from easycord.builders.embed import EmbedBuilder


def test_build_requires_title():
    with pytest.raises(ValueError, match="requires a title"):
        EmbedBuilder().build()


def test_build_returns_discord_embed():
    embed = EmbedBuilder().title("Hello").build()
    assert isinstance(embed, discord.Embed)


def test_title_set():
    embed = EmbedBuilder().title("My Title").build()
    assert embed.title == "My Title"


def test_description_set():
    embed = EmbedBuilder().title("T").description("My Desc").build()
    assert embed.description == "My Desc"


def test_no_description_is_none():
    embed = EmbedBuilder().title("T").build()
    assert embed.description is None


def test_field_added():
    embed = EmbedBuilder().title("T").field("Name", "Value").build()
    assert len(embed.fields) == 1
    assert embed.fields[0].name == "Name"
    assert embed.fields[0].value == "Value"
    assert embed.fields[0].inline is True


def test_field_inline_false():
    embed = EmbedBuilder().title("T").field("N", "V", inline=False).build()
    assert embed.fields[0].inline is False


def test_multiple_fields():
    embed = EmbedBuilder().title("T").field("A", "1").field("B", "2").build()
    assert len(embed.fields) == 2
    assert embed.fields[0].name == "A"
    assert embed.fields[1].name == "B"


def test_footer_set():
    embed = EmbedBuilder().title("T").footer("Footer text").build()
    assert embed.footer.text == "Footer text"


def test_no_footer_is_empty():
    embed = EmbedBuilder().title("T").build()
    assert embed.footer.text is None


def test_empty_string_footer_preserved():
    embed = EmbedBuilder().title("T").footer("").build()
    # Empty string footer should be preserved, not silently dropped
    assert embed.footer.text == ""


def test_color_set():
    color = discord.Color.red()
    embed = EmbedBuilder().title("T").color(color).build()
    assert embed.color == color


def test_default_color_is_blue():
    embed = EmbedBuilder().title("T").build()
    assert embed.color == discord.Color.blue()


def test_chaining_returns_self():
    b = EmbedBuilder()
    assert b.title("T") is b
    assert b.description("D") is b
    assert b.field("N", "V") is b
    assert b.footer("F") is b
    assert b.color(discord.Color.blue()) is b
