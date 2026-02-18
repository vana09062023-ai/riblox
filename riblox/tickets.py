import discord
from discord.ext import commands
import random
import io
from datetime import datetime

# ============================================================
#  НАСТРОЙКИ
# ============================================================
TICKET_CHANNEL_ID   = 1457644231362609290   # канал где стоит кнопка
TICKET_CATEGORY_ID  = 1457464401673322770   # категория для тикетов
LOG_CHANNEL_ID      = 1457468349326954539   # канал логов

# ID ролей службы поддержки (можно добавлять сколько угодно)
SUPPORT_ROLE_IDS = [
    123456789012345678,   # ← замени на свои ID ролей
    # 987654321098765432, # можно добавить ещё
]
# ============================================================

open_tickets: dict[int, int] = {}  # user_id: channel_id


# ========= HELPERS =========

def is_support(member: discord.Member) -> bool:
    """Проверяет, является ли участник поддержкой или администратором."""
    if member.guild_permissions.administrator:
        return True
    return any(role.id in SUPPORT_ROLE_IDS for role in member.roles)


def get_support_overwrites(guild: discord.Guild, user: discord.Member) -> dict:
    """Права: пользователь + поддержка видят канал, остальные нет."""
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        guild.me: discord.PermissionOverwrite(
            view_channel=True, send_messages=True, read_message_history=True
        ),
        user: discord.PermissionOverwrite(
            view_channel=True, send_messages=True, read_message_history=True
        ),
    }
    for role in guild.roles:
        if role.id in SUPPORT_ROLE_IDS:
            overwrites[role] = discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True
            )
    for member in guild.members:
        if member.guild_permissions.administrator:
            overwrites[member] = discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True
            )
    return overwrites


# ========= MODALS =========

class TicketModal(discord.ui.Modal, title="📋 Открытие тикета"):
    roblox_nick = discord.ui.TextInput(
        label="Ваш ник в Roblox",
        placeholder="Например: CoolPlayer123",
        max_length=50,
        required=True
    )
    category = discord.ui.TextInput(
        label="Тема обращения",
        placeholder="Баг / Жалоба / Вопрос / Покупка / Другое",
        max_length=50,
        required=True
    )
    reason = discord.ui.TextInput(
        label="Подробное описание проблемы",
        style=discord.TextStyle.paragraph,
        placeholder="Опишите ситуацию как можно подробнее...",
        max_length=1000,
        required=True
    )
    proof = discord.ui.TextInput(
        label="Ссылка на доказательства (если есть)",
        placeholder="https://... или напишите 'нет'",
        max_length=300,
        required=False
    )

    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id in open_tickets:
            await interaction.response.send_message(
                "⛔ У вас уже есть открытый тикет!", ephemeral=True
            )
            return

        guild      = interaction.guild
        category   = guild.get_channel(TICKET_CATEGORY_ID)
        log_ch     = self.bot.get_channel(LOG_CHANNEL_ID)
        ticket_id  = random.randint(1000, 9999)
        overwrites = get_support_overwrites(guild, interaction.user)

        channel = await guild.create_text_channel(
            name=f"тикет-{ticket_id}",
            category=category,
            overwrites=overwrites,
            topic=f"Тикет пользователя {interaction.user} | Roblox: {self.roblox_nick.value}"
        )
        open_tickets[interaction.user.id] = channel.id

        # Красивый embed в тикет-канале
        embed = discord.Embed(
            title=f"🎫 Тикет #{ticket_id}",
            color=0x5865F2,
            timestamp=datetime.utcnow()
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.add_field(name="👤 Пользователь",   value=interaction.user.mention,    inline=True)
        embed.add_field(name="🎮 Ник в Roblox",   value=f"`{self.roblox_nick.value}`", inline=True)
        embed.add_field(name="📂 Тема",            value=f"`{self.category.value}`",   inline=True)
        embed.add_field(name="📝 Описание",        value=self.reason.value,            inline=False)
        if self.proof.value and self.proof.value.lower() != "нет":
            embed.add_field(name="🔗 Доказательства", value=self.proof.value, inline=False)
        embed.set_footer(text="Служба поддержки ответит вам как можно скорее")

        # Пинг ролей поддержки
        mentions = " ".join(
            f"<@&{rid}>" for rid in SUPPORT_ROLE_IDS
        ) or ""

        await channel.send(
            content=f"{interaction.user.mention} {mentions}",
            embed=embed,
            view=CloseTicketView(self.bot)
        )

        # Лог
        if log_ch:
            log = discord.Embed(
                title="📥 Тикет открыт",
                color=0x57F287,
                timestamp=datetime.utcnow()
            )
            log.set_author(
                name=str(interaction.user),
                icon_url=interaction.user.display_avatar.url
            )
            log.add_field(name="Пользователь", value=interaction.user.mention, inline=True)
            log.add_field(name="Roblox-ник",   value=self.roblox_nick.value,   inline=True)
            log.add_field(name="Канал",         value=channel.mention,          inline=True)
            log.add_field(name="Тема",          value=self.category.value,      inline=True)
            await log_ch.send(embed=log)

        await interaction.response.send_message(
            f"✅ Тикет создан: {channel.mention}", ephemeral=True
        )


class CloseReasonModal(discord.ui.Modal, title="🔒 Закрытие тикета"):
    reason = discord.ui.TextInput(
        label="Причина закрытия",
        style=discord.TextStyle.paragraph,
        placeholder="Вопрос решён / Нарушение правил / Спам...",
        max_length=500,
        required=True
    )

    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        if not is_support(interaction.user):
            await interaction.response.send_message(
                "⛔ Только сотрудники поддержки могут закрывать тикеты.",
                ephemeral=True
            )
            return

        await interaction.response.defer()

        log_ch = self.bot.get_channel(LOG_CHANNEL_ID)

        # Сохраняем историю
        lines = []
        async for msg in interaction.channel.history(limit=None, oldest_first=True):
            if msg.author.bot and not msg.content:
                continue
            lines.append(
                f"[{msg.created_at.strftime('%d.%m.%Y %H:%M')}] "
                f"{msg.author.display_name}: {msg.content}"
            )
        transcript = "\n".join(lines)
        file = discord.File(
            fp=io.BytesIO(transcript.encode("utf-8")),
            filename=f"{interaction.channel.name}.txt"
        )

        if log_ch:
            embed = discord.Embed(
                title="📕 Тикет закрыт",
                color=0xED4245,
                timestamp=datetime.utcnow()
            )
            embed.set_author(
                name=str(interaction.user),
                icon_url=interaction.user.display_avatar.url
            )
            embed.add_field(name="Закрыл",  value=interaction.user.mention,     inline=True)
            embed.add_field(name="Канал",   value=interaction.channel.name,     inline=True)
            embed.add_field(name="Причина", value=self.reason.value,            inline=False)
            await log_ch.send(embed=embed, file=file)

        # Чистим словарь
        for uid, cid in list(open_tickets.items()):
            if cid == interaction.channel.id:
                del open_tickets[uid]

        await interaction.channel.delete(reason="Тикет закрыт")


# ========= VIEWS =========

class TicketView(discord.ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(
        label="Открыть тикет",
        style=discord.ButtonStyle.primary,
        emoji="🎫",
        custom_id="open_ticket_btn"
    )
    async def open_ticket(self, interaction: discord.Interaction, _):
        await interaction.response.send_modal(TicketModal(self.bot))


class CloseTicketView(discord.ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(
        label="Закрыть тикет",
        style=discord.ButtonStyle.danger,
        emoji="🔒",
        custom_id="close_ticket_btn"
    )
    async def close_ticket(self, interaction: discord.Interaction, _):
        if not is_support(interaction.user):
            await interaction.response.send_message(
                "⛔ Только сотрудники поддержки могут закрывать тикеты.",
                ephemeral=True
            )
            return
        await interaction.response.send_modal(CloseReasonModal(self.bot))


# ========= COMMANDS =========

class Tickets(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="tiket")
    @commands.has_permissions(administrator=True)
    async def ticket_panel(self, ctx: commands.Context):
        """Отправить панель тикетов в текущий канал."""
        if ctx.channel.id != TICKET_CHANNEL_ID:
            await ctx.send("⛔ Эту команду можно использовать только в канале тикетов.")
            return

        embed = discord.Embed(
            title="🎫 Служба поддержки",
            description=(
                "Если у вас возникли вопросы или проблемы — нажмите кнопку ниже.\n\n"
                "**Перед открытием тикета:**\n"
                "› Подготовьте описание проблемы\n"
                "› Приложите скриншоты если есть\n"
                "› Укажите свой ник в Roblox\n\n"
                "Среднее время ответа: **до 24 часов**"
            ),
            color=0x5865F2
        )
        embed.set_footer(text="Не злоупотребляйте системой тикетов")

        await ctx.message.delete()
        await ctx.send(embed=embed, view=TicketView(self.bot))

    @commands.command(name="addsuprole")
    @commands.has_permissions(administrator=True)
    async def add_support_role(self, ctx: commands.Context, role: discord.Role):
        """Добавить роль в список поддержки: !addsuprole @Роль"""
        if role.id not in SUPPORT_ROLE_IDS:
            SUPPORT_ROLE_IDS.append(role.id)
            await ctx.send(f"✅ Роль {role.mention} добавлена в службу поддержки.")
        else:
            await ctx.send(f"ℹ️ Роль {role.mention} уже есть в списке поддержки.")

    @commands.command(name="removesuprole")
    @commands.has_permissions(administrator=True)
    async def remove_support_role(self, ctx: commands.Context, role: discord.Role):
        """Убрать роль из списка поддержки: !removesuprole @Роль"""
        if role.id in SUPPORT_ROLE_IDS:
            SUPPORT_ROLE_IDS.remove(role.id)
            await ctx.send(f"✅ Роль {role.mention} убрана из службы поддержки.")
        else:
            await ctx.send(f"ℹ️ Роль {role.mention} не найдена в списке поддержки.")

    @commands.command(name="suproles")
    @commands.has_permissions(administrator=True)
    async def list_support_roles(self, ctx: commands.Context):
        """Посмотреть список ролей поддержки: !suproles"""
        if not SUPPORT_ROLE_IDS:
            await ctx.send("ℹ️ Список ролей поддержки пуст.")
            return
        roles_text = "\n".join(f"• <@&{rid}>" for rid in SUPPORT_ROLE_IDS)
        embed = discord.Embed(
            title="🛡️ Роли службы поддержки",
            description=roles_text,
            color=0x5865F2
        )
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Tickets(bot))
