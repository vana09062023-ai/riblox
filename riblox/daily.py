import discord
from discord.ext import commands, tasks
from datetime import datetime, time
import pytz

# ============================================================
#  НАСТРОЙКИ
# ============================================================
CHANNEL_ID = 1411388192027967508
MESSAGE    = "!рптайм"
SEND_TIME  = time(hour=17, minute=0, second=0)  # 20:00 МСК = 17:00 UTC
# ============================================================

MSK = pytz.timezone("Europe/Moscow")


class DailyMessage(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.daily_task.start()

    def cog_unload(self):
        self.daily_task.cancel()

    @tasks.loop(time=SEND_TIME)
    async def daily_task(self):
        channel = self.bot.get_channel(CHANNEL_ID)
        if channel:
            await channel.send(MESSAGE)
            print(f"[DailyMessage] Отправлено '{MESSAGE}' в канал {CHANNEL_ID}")
        else:
            print(f"[DailyMessage] Канал {CHANNEL_ID} не найден!")

    @daily_task.before_loop
    async def before_daily_task(self):
        await self.bot.wait_until_ready()
        now = datetime.now(MSK)
        print(f"[DailyMessage] Планировщик запущен. Сейчас {now.strftime('%H:%M')} МСК, сообщение в 20:00 МСК")


async def setup(bot: commands.Bot):
    await bot.add_cog(DailyMessage(bot))
