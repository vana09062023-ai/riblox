import discord
from discord.ext import commands
import random
import io
from datetime import datetime

# ============================================================
#  НАСТРОЙКИ
# ============================================================
SHOP_TICKET_CHANNEL_ID  = 1381189702258003978   # канал где стоит кнопка
SHOP_TICKET_CATEGORY_ID = 1381189678371307600   # категория для тикетов
SHOP_LOG_CHANNEL_ID     = 1381189717453967412   # канал логов

SUPPORT_ROLE_IDS = [
    1381190006487384105,
    1469797092909125723,
]
# ============================================================

open_shop_tickets: dict[int, int] = {}


# ========= HELPERS =========

def is_support(member: discord.Member) -> bool:
    if member.guild_permissions.administrator:
        return True
    return any(role.id in SUPPORT_ROLE_IDS for role in member.roles)


def get_support_overwrites(guild: discord.Guild, user: discord.Member) -> dict:
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

class ShopTicketModal(discord.ui.Modal, title="🛒 Оформление заказа"):
    roblox_nick = discord.ui.TextInput(
        label="Ваш ник в Roblox",
        placeholder="Например: CoolPlayer123",
        max_length=50,
        required=True
    )
    item = discord.ui.TextInput(
        label="Что хотите купить?",
        placeholder="Название товара / услуги из магазина",
        max_length=100,
        required=True
    )
    quantity = discord.ui.TextInput(
        label="Количество / сумма",
        placeholder="Например: 1 шт. или 500 монет",
        max_length=50,
        required=True
    )
    comment = discord.ui.TextInput(
        label="Дополнительный комментарий",
        style=discord.TextStyle.paragraph,
        placeholder="Любые пожелания, уточнения к заказу...",
        max_length=500,
        required=False
    )

    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id in open_shop_tickets:
            await interaction.response.send_message(
                "⛔ У вас уже есть открытый заказ! Дождитесь его завершения.",
                ephemeral=True
            )
            return

        guild      = interaction.guild
        category   = guild.get_channel(SHOP_TICKET_CATEGORY_ID)
        log_ch     = self.bot.get_channel(SHOP_LOG_CHANNEL_ID)
        order_id   = random.randint(10000, 99999)
        overwrites = get_support_overwrites(guild, interaction.user)

        channel = await guild.create_text_channel(
            name=f"заказ-{order_id}",
            category=category,
            overwrites=overwrites,
            topic=f"Заказ #{order_id} | {interaction.user} | {self.item.value}"
        )
        open_shop_tickets[interaction.user.id] = channel.id

        embed = discord.Embed(
            title=f"🛍️ Заказ #{order_id}",
            color=0xF5A623,
            timestamp=datetime.utcnow()
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)

        embed.add_field(name="", value=(
            "```\n"
            "  RI BLOX SHOP\n"
            "  Новый заказ\n"
            "```"
        ), inline=False)

        embed.add_field(name="👤 Покупатель",   value=interaction.user.mention,        inline=True)
        embed.add_field(name="🎮 Ник в Roblox", value=f"`{self.roblox_nick.value}`",   inline=True)
        embed.add_field(name="",                value="",                              inline=False)
        embed.add_field(name="🛒 Товар",        value=f"`{self.item.value}`",          inline=True)
        embed.add_field(name="🔢 Кол-во/Сумма", value=f"`{self.quantity.value}`",      inline=True)

        if self.comment.value:
            embed.add_field(name="💬 Комментарий", value=self.comment.value, inline=False)

        embed.add_field(name="", value=(
            "> ⏳ Ожидайте — продавец свяжется с вами в ближайшее время\n"
            "> ❌ Не покидайте канал до завершения сделки"
        ), inline=False)

        embed.set_footer(text=f"Заказ #{order_id} • Ri Blox Shop")

        mentions = " ".join(f"<@&{rid}>" for rid in SUPPORT_ROLE_IDS)
        await channel.send(
            content=f"{interaction.user.mention} {mentions}",
            embed=embed,
            view=CloseOrderView(self.bot)
        )

        if log_ch:
            log = discord.Embed(
                title="📦 Новый заказ",
                color=0xF5A623,
                timestamp=datetime.utcnow()
            )
            log.set_author(
                name=str(interaction.user),
                icon_url=interaction.user.display_avatar.url
            )
            log.add_field(name="Покупатель",   value=interaction.user.mention,      inline=True)
            log.add_field(name="Roblox-ник",   value=self.roblox_nick.value,        inline=True)
            log.add_field(name="Канал",        value=channel.mention,               inline=True)
            log.add_field(name="Товар",        value=self.item.value,               inline=True)
            log.add_field(name="Кол-во/Сумма", value=self.quantity.value,           inline=True)
            await log_ch.send(embed=log)

        await interaction.response.send_message(
            f"✅ Заказ оформлен: {channel.mention}", ephemeral=True
        )


class CloseOrderModal(discord.ui.Modal, title="✅ Завершение заказа"):
    result = discord.ui.TextInput(
        label="Статус завершения",
        placeholder="Выполнен / Отменён / Возврат...",
        max_length=100,
        required=True
    )
    comment = discord.ui.TextInput(
        label="Комментарий",
        style=discord.TextStyle.paragraph,
        placeholder="Подробности завершения заказа...",
        max_length=500,
        required=False
    )

    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        if not is_support(interaction.user):
            await interaction.response.send_message(
                "⛔ Только сотрудники магазина могут закрывать заказы.",
                ephemeral=True
            )
            return

        await interaction.response.defer()
        log_ch = self.bot.get_channel(SHOP_LOG_CHANNEL_ID)

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
                title="📕 Заказ закрыт",
                color=0xED4245,
                timestamp=datetime.utcnow()
            )
            embed.set_author(
                name=str(interaction.user),
                icon_url=interaction.user.display_avatar.url
            )
            embed.add_field(name="Закрыл",  value=interaction.user.mention,    inline=True)
            embed.add_field(name="Канал",   value=interaction.channel.name,    inline=True)
            embed.add_field(name="Статус",  value=self.result.value,           inline=True)
            if self.comment.value:
                embed.add_field(name="Комментарий", value=self.comment.value,  inline=False)
            await log_ch.send(embed=embed, file=file)

        for uid, cid in list(open_shop_tickets.items()):
            if cid == interaction.channel.id:
                del open_shop_tickets[uid]

        await interaction.channel.delete(reason="Заказ завершён")


# ========= VIEWS =========

class ShopTicketView(discord.ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(
        label="Оформить заказ",
        style=discord.ButtonStyle.success,
        emoji="🛒",
        custom_id="open_shop_ticket_btn"
    )
    async def open_order(self, interaction: discord.Interaction, _):
        await interaction.response.send_modal(ShopTicketModal(self.bot))


class CloseOrderView(discord.ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(
        label="Завершить заказ",
        style=discord.ButtonStyle.danger,
        emoji="✅",
        custom_id="close_shop_ticket_btn"
    )
    async def close_order(self, interaction: discord.Interaction, _):
        if not is_support(interaction.user):
            await interaction.response.send_message(
                "⛔ Только сотрудники магазина могут закрывать заказы.",
                ephemeral=True
            )
            return
        await interaction.response.send_modal(CloseOrderModal(self.bot))


# ========= COG =========

class ShopTickets(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="tiketshop")
    @commands.has_permissions(administrator=True)
    async def shop_panel(self, ctx: commands.Context):
        if ctx.channel.id != SHOP_TICKET_CHANNEL_ID:
            await ctx.send("⛔ Эту команду можно использовать только в канале магазина.", delete_after=5)
            return

        embed = discord.Embed(
            title="🛍️ Ri Blox Shop",
            description=(
                "Добро пожаловать в магазин **Ri Blox Studios**!\n\n"
                "**Как совершить покупку:**\n"
                "› Нажмите кнопку **Оформить заказ** ниже\n"
                "› Укажите ник в Roblox и название товара\n"
                "› Дождитесь ответа продавца в вашем канале\n\n"
                "**Правила магазина:**\n"
                "› Не создавайте лишние заказы\n"
                "› Оплата только через официальные методы\n"
                "› По вопросам возврата — обратитесь в поддержку\n\n"
                "⏱️ Среднее время обработки: **до 24 часов**"
            ),
            color=0xF5A623
        )
        embed.set_footer(text="Ri Blox Shop • Официальный магазин")

        await ctx.message.delete()
        await ctx.send(embed=embed, view=ShopTicketView(self.bot))


async def setup(bot: commands.Bot):
    await bot.add_cog(ShopTickets(bot))
