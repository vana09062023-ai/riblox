import discord
from discord.ext import commands
import os

BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')

# ============================================================
#  МОДУЛИ ПО ПАПКАМ
#  Просто дописывай имя файла (без .py) в нужную папку
# ============================================================

RIBLOX = [
    "tickets",
    "Partner",
    "passports",
    "daily",
]

RISHOP = [
    "Shoptickets",
    # "products",
]

RIALFA = [
    # "alfa",
    # "stats",
]

# ============================================================
#  Добавить новую папку — скопируй блок выше и добавь
#  её название в FOLDERS_MAP ниже
# ============================================================

FOLDERS_MAP = {
    "riblox": RIBLOX,
    "rishop": RISHOP,
    "rialfa": RIALFA,
    # "новая_папка": НОВАЯ_ПАПКА,
}

# ============================================================

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"\n{'='*45}")
    print(f"  Бот запущен: {bot.user}")
    print(f"{'='*45}")

    for folder, modules in FOLDERS_MAP.items():
        if not modules:
            print(f"\n  [{folder}] — нет модулей")
            continue

        print(f"\n  [{folder}]")
        for module in modules:
            ext = f"{folder}.{module}"
            try:
                await bot.load_extension(ext)
                print(f"    [+] {module}.py загружен")
            except Exception as e:
                print(f"    [!] {module}.py — ошибка: {e}")

    print(f"\n{'='*45}\n")


bot.run(BOT_TOKEN)
