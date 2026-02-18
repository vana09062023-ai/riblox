import discord
from discord.ext import commands
import random
import json
import os
from datetime import datetime

# ============================================================
#  НАСТРОЙКИ
# ============================================================
PASSPORT_ROLE_ID = 1377688783230861412   # роль которая может выдавать паспорта
PASSPORTS_FILE   = "passports.json"      # файл где хранятся все паспорта
# ============================================================


def load_passports() -> dict:
    if not os.path.exists(PASSPORTS_FILE):
        return {}
    with open(PASSPORTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_passports(data: dict):
    with open(PASSPORTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def generate_passport_number() -> str:
    """Генерирует уникальный номер паспорта: XX-XXXXXX"""
    part1 = random.randint(10, 99)
    part2 = random.randint(100000, 999999)
    return f"{part1}-{part2}"


def can_issue(member: discord.Member) -> bool:
    """Может ли участник выдавать паспорта."""
    if member.guild_permissions.administrator:
        return True
    return any(r.id == PASSPORT_ROLE_ID for r in member.roles)


def passport_embed(user: discord.Member, passport: dict) -> discord.Embed:
    """Красивый embed паспорта."""
    embed = discord.Embed(
        title="🪪 Паспорт гражданина",
        color=0x2B2D31,
        timestamp=datetime.utcnow()
    )
    embed.set_thumbnail(url=user.display_avatar.url)

    embed.add_field(
        name="",
        value=(
            "```\n"
            f"  REPUBLIC OF RI BLOX\n"
            f"  ГРАЖДАНСКИЙ ПАСПОРТ\n"
            "```"
        ),
        inline=False
    )

    embed.add_field(name="👤 Владелец",       value=user.mention,                  inline=True)
    embed.add_field(name="🔢 Номер паспорта", value=f"`{passport['number']}`",     inline=True)
    embed.add_field(name="",                  value="",                             inline=False)
    embed.add_field(name="📅 Дата выдачи",    value=passport['issued_at'],         inline=True)
    embed.add_field(name="🖊️ Выдан",          value=f"<@{passport['issued_by']}>", inline=True)

    embed.set_footer(text=f"ID: {user.id}")
    return embed


class Passports(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── !паспорт @user ──────────────────────────────────────
    @commands.command(name="паспорт")
    async def issue_passport(self, ctx: commands.Context, member: discord.Member):
        if not can_issue(ctx.author):
            await ctx.send("⛔ У вас нет прав для выдачи паспортов.", delete_after=5)
            return

        passports = load_passports()
        uid = str(member.id)

        if uid in passports:
            await ctx.send(
                f"⚠️ У {member.mention} уже есть паспорт `{passports[uid]['number']}`.\n"
                f"Используй `!паспортчек @{member.display_name}` чтобы посмотреть его.",
                delete_after=8
            )
            return

        # Генерируем уникальный номер
        existing_numbers = {p["number"] for p in passports.values()}
        number = generate_passport_number()
        while number in existing_numbers:
            number = generate_passport_number()

        passports[uid] = {
            "number":    number,
            "issued_at": datetime.utcnow().strftime("%d.%m.%Y"),
            "issued_by": str(ctx.author.id)
        }
        save_passports(passports)

        embed = passport_embed(member, passports[uid])
        await ctx.send(embed=embed)
        await ctx.message.delete()

    # ── !паспортчек @user ───────────────────────────────────
    @commands.command(name="паспортчек")
    async def check_passport(self, ctx: commands.Context, member: discord.Member):
        passports = load_passports()
        uid = str(member.id)

        if uid not in passports:
            await ctx.send(f"❌ У {member.mention} нет паспорта.", delete_after=5)
            return

        embed = passport_embed(member, passports[uid])
        await ctx.send(embed=embed)
        await ctx.message.delete()

    # ── !кастомпасс @user НОМЕР ─────────────────────────────
    @commands.command(name="кастомпасс")
    @commands.has_permissions(administrator=True)
    async def custom_passport(self, ctx: commands.Context, member: discord.Member, number: str):
        passports = load_passports()
        uid = str(member.id)

        # Проверяем уникальность
        existing = {p["number"]: mid for mid, p in passports.items()}
        if number in existing and existing[number] != uid:
            owner = ctx.guild.get_member(int(existing[number]))
            owner_name = owner.mention if owner else f"ID {existing[number]}"
            await ctx.send(
                f"⛔ Номер `{number}` уже занят — он принадлежит {owner_name}.",
                delete_after=6
            )
            return

        passports[uid] = {
            "number":    number,
            "issued_at": datetime.utcnow().strftime("%d.%m.%Y"),
            "issued_by": str(ctx.author.id)
        }
        save_passports(passports)

        embed = passport_embed(member, passports[uid])
        await ctx.send(embed=embed)
        await ctx.message.delete()

    # ── !паспортудалить @user (только админ) ────────────────
    @commands.command(name="паспортудалить")
    @commands.has_permissions(administrator=True)
    async def delete_passport(self, ctx: commands.Context, member: discord.Member):
        passports = load_passports()
        uid = str(member.id)

        if uid not in passports:
            await ctx.send(f"❌ У {member.mention} нет паспорта.", delete_after=5)
            return

        number = passports[uid]["number"]
        del passports[uid]
        save_passports(passports)

        await ctx.send(f"🗑️ Паспорт `{number}` пользователя {member.mention} удалён.", delete_after=6)
        await ctx.message.delete()


async def setup(bot: commands.Bot):
    await bot.add_cog(Passports(bot))
