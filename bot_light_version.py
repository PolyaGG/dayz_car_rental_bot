#THIS VERSION CANT SAVE USER'S STEAM ID
#IF YOU WANT FULL FUNCTIONALITY USE bot_en_version.py instead
#Эта версия бота не поддерживает сохранение SteamID
#Если нужен полный функционал используй bot_ru_version.py

import os
import json
import asyncio
import shutil
import uuid
import discord
from discord.ext import commands

# Пути к папкам
BANK_PATH = r"C:\\DayZServer1\\profiles\\KR_BANKING\\PlayerDataBase" # <-- Путь к папке с банковскими аккаунтами игроков
GARAGE_PATH = r"C:\\DayZServer1\\profiles\\RF\\GARAGE\\players"  # <-- Путь к папке с гаражами игроков
CARS_CONFIG_FILE = "cars_config.json"
VEHICLE_TEMPLATES_PATH = "vehicles_templates"
ALERT_CHANNEL_ID = 111111111111  # <-- сюда вставь ID канала для оповещений


# Инициализация бота
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Загружаем машины и фильтруем по наличию шаблонов
try:
    with open(CARS_CONFIG_FILE, "r", encoding="utf-8") as f:
        cars_raw = json.load(f)
        CARS_LIST = [car for car in cars_raw if os.path.isfile(os.path.join(VEHICLE_TEMPLATES_PATH, f"{car['classname']}.json"))]
except Exception as e:
    print(f"Ошибка загрузки конфигурации: {e}")
    CARS_LIST = []

active_rentals = {}

async def rent_deduct_loop(steam_id: str, price: int, user: discord.User):
    try:
        while True:
            await asyncio.sleep(600)  # 10 минут

            account_file = os.path.join(BANK_PATH, f"{steam_id}.json")
            try:
                with open(account_file, "r+", encoding="utf-8") as f:
                    data = json.load(f)
                    balance = data.get("m_OwnedCurrency", 0)
                    new_balance = balance - price
                    if new_balance < 0:
                        insufficient = True
                    else:
                        data["m_OwnedCurrency"] = new_balance
                        f.seek(0)
                        json.dump(data, f, ensure_ascii=False, indent=4)
                        f.truncate()
                        insufficient = False
            except Exception:
                insufficient = True

            if insufficient:
                channel = bot.get_channel(ALERT_CHANNEL_ID)
                if channel:
                    await channel.send(f"{user.mention}, недостаточно средств для аренды автомобиля! Аренда остановлена.")
                rental = active_rentals.pop(steam_id, None)
                if rental:
                    car_uuid = rental.get("uuid")
                    car_path = os.path.join(GARAGE_PATH, steam_id, "garage", f"{car_uuid}.json")
                    if os.path.isfile(car_path):
                        os.remove(car_path)
                break
    except asyncio.CancelledError:
        active_rentals.pop(steam_id, None)

@bot.command(name="rent")
async def rent(ctx: commands.Context, steam_id: str):
    if steam_id in active_rentals:
        await ctx.reply("У вас уже есть арендованный автомобиль!")
        return

    account_file = os.path.join(BANK_PATH, f"{steam_id}.json")
    try:
        with open(account_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            balance = data.get("m_OwnedCurrency", 0)
    except Exception:
        await ctx.reply("Ошибка чтения баланса или аккаунт не найден.")
        return

    if not CARS_LIST:
        await ctx.reply("Нет доступных машин для аренды.")
        return

    min_price = min(car["price"] for car in CARS_LIST)
    if balance < min_price:
        await ctx.reply("Недостаточно средств для аренды любой машины.")
        return

    class CarSelectView(discord.ui.View):
        def __init__(self, author_id):
            super().__init__(timeout=None)  # кнопки теперь бессрочные
            self.author_id = author_id
            for car in CARS_LIST:
                button = discord.ui.Button(label=f"{car['name']} - {car['price']}₽", style=discord.ButtonStyle.primary, custom_id=car['classname'])
                button.callback = self.make_callback(car)
                self.add_item(button)

        def make_callback(self, car):
            async def callback(interaction: discord.Interaction):
                try:
                    if interaction.user.id != self.author_id:
                        await interaction.response.send_message("Это не ваша сессия.", ephemeral=True)
                        return

                    car_class = car["classname"]
                    car_name = car["name"]
                    car_price = car["price"]

                    with open(account_file, "r+", encoding="utf-8") as f:
                        data = json.load(f)
                        if data.get("m_OwnedCurrency", 0) < car_price:
                            await interaction.response.send_message("Недостаточно средств.", ephemeral=True)
                            return
                        data["m_OwnedCurrency"] -= car_price
                        f.seek(0)
                        json.dump(data, f, ensure_ascii=False, indent=4)
                        f.truncate()

                    garage_dir = os.path.join(GARAGE_PATH, steam_id, "garage")
                    os.makedirs(garage_dir, exist_ok=True)
                    template_path = os.path.join(VEHICLE_TEMPLATES_PATH, f"{car_class}.json")
                    car_uuid = str(uuid.uuid4())
                    with open(template_path, "r", encoding="utf-8") as f:
                        car_data = json.load(f)
                    car_data["ownerId"] = steam_id
                    car_data["uuid"] = car_uuid
                    car_dest_path = os.path.join(garage_dir, f"{car_uuid}.json")
                    with open(car_dest_path, "w", encoding="utf-8") as f:
                        json.dump(car_data, f, ensure_ascii=False, indent=4)

                    active_rentals[steam_id] = {"user": ctx.author, "price": car_price, "uuid": car_uuid, "task": None}
                    task = asyncio.create_task(rent_deduct_loop(steam_id, car_price, ctx.author))
                    active_rentals[steam_id]["task"] = task

                    await interaction.response.edit_message(content=f"✅ Вы арендовали {car_name}!", view=None)
                except Exception as e:
                    print(f"[ERROR] Ошибка при обработке кнопки: {e}")
                    try:
                        await interaction.response.send_message("Произошла ошибка при аренде.", ephemeral=True)
                    except:
                        pass
            return callback

    view = CarSelectView(ctx.author.id)
    await ctx.reply(f"Ваш баланс: {balance}₽. Выберите машину:", view=view)

@bot.command(name="return")
async def return_car(ctx: commands.Context, steam_id: str):
    rental = active_rentals.get(steam_id)
    if not rental:
        await ctx.reply("У вас нет активной аренды.")
        return

    car_uuid = rental.get("uuid")
    car_file = os.path.join(GARAGE_PATH, steam_id, "garage", f"{car_uuid}.json")
    if os.path.isfile(car_file):
        os.remove(car_file)
        if rental.get("task"):
            rental["task"].cancel()
        active_rentals.pop(steam_id, None)
        await ctx.reply("✅ Машина успешно возвращена. Спасибо!")
    else:
        await ctx.reply("⚠️ Машина не найдена в гараже. Возврат невозможен.")

bot.run("YOUR_BOT_TOKEN") # <-- Токен вашего дискорд бота
