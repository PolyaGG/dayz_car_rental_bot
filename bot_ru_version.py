#Русская версия бота, все настройки указаны комментариями. Все вопросы и помощь с установкой - Discord @polyagg
import os
import json
import asyncio
import shutil
import uuid
import discord
from discord.ext import commands

# Пути к папкам
BANK_PATH = r"C:\\DayZServer1\\profiles\\KR_BANKING\\PlayerDataBase"
GARAGE_PATH = r"C:\\DayZServer1\\profiles\\RF\\GARAGE\\players"
CARS_CONFIG_FILE = "cars_config.json"
VEHICLE_TEMPLATES_PATH = "vehicles_templates"
USER_DATA_PATH = "user_data.json"
ALERT_CHANNEL_ID = 1352372071543607417  # <-- сюда вставь ID канала для стартового сообщения бота | Insert bot start message channel ID here

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

try:
    with open(CARS_CONFIG_FILE, "r", encoding="utf-8") as f:
        cars_raw = json.load(f)
        CARS_LIST = [car for car in cars_raw if os.path.isfile(os.path.join(VEHICLE_TEMPLATES_PATH, f"{car['classname']}.json"))]
except Exception as e:
    print(f"Ошибка загрузки конфигурации: {e}")
    CARS_LIST = []

def load_user_data():
    if os.path.exists(USER_DATA_PATH):
        with open(USER_DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_user_data(data):
    with open(USER_DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

active_rentals = {}

async def rent_deduct_loop(steam_id: str, price: int, user: discord.User):
    try:
        while True:
            await asyncio.sleep(600)  # Интервал списания средств указывается тут в секундах / money deduct interval set up here (time in seconds)

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

@bot.command(name="аренда") # <-- Тут устанавливается команда для аренды машины / command for car rent set-up here
async def rent(ctx: commands.Context):
    user_data = load_user_data()

    if str(ctx.author.id) not in user_data:
        await ctx.author.send("Введите ваш SteamID (64-bit):")

        def check(msg):
            return msg.author == ctx.author and msg.content.isdigit()

        try:
            message = await bot.wait_for('message', timeout=60.0, check=check)
            steam_id = message.content.strip()
            user_data[str(ctx.author.id)] = {"steam_id": steam_id}
            save_user_data(user_data)

            await ctx.author.send(f"Ваш SteamID сохранён: {steam_id}. Теперь выберите машину для аренды!")

        except asyncio.TimeoutError:
            await ctx.author.send("Время ожидания истекло, попробуйте снова.")
            return

    else:
        steam_id = user_data[str(ctx.author.id)]["steam_id"]

    account_file = os.path.join(BANK_PATH, f"{steam_id}.json")
    try:
        with open(account_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            balance = data.get("m_OwnedCurrency", 0)
    except Exception:
        await ctx.author.send("Ошибка чтения баланса или аккаунт не найден.")
        return

    if not CARS_LIST:
        await ctx.author.send("Нет доступных машин для аренды.")
        return

    min_price = min(car["price"] for car in CARS_LIST)
    if balance < min_price:
        await ctx.author.send("Недостаточно средств для аренды любой машины.")
        return

    class CarSelectView(discord.ui.View):
        def __init__(self, author_id):
            super().__init__(timeout=None)
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
    await ctx.author.send(f"Ваш баланс: {balance}₽. Выберите машину:", view=view)

@bot.command(name="возврат") # <-- Тут устанавливается команда для возврата машины / command for returning car set-up here
async def return_car(ctx: commands.Context):
    user_data = load_user_data()
    if str(ctx.author.id) not in user_data:
        await ctx.author.send("Вы не указали свой SteamID. Пожалуйста, используйте команду !аренда для его добавления.")
        return

    steam_id = user_data[str(ctx.author.id)]["steam_id"]

    rental = active_rentals.get(steam_id)
    if not rental:
        await ctx.author.send("У вас нет активной аренды.")
        return

    car_uuid = rental.get("uuid")
    car_file = os.path.join(GARAGE_PATH, steam_id, "garage", f"{car_uuid}.json")
    if os.path.isfile(car_file):
        os.remove(car_file)
        if rental.get("task"):
            rental["task"].cancel()
        active_rentals.pop(steam_id, None)
        await ctx.author.send("✅ Машина успешно возвращена. Спасибо!")
    else:
        await ctx.author.send("⚠️ Машина не найдена в гараже. Возврат невозможен.")
       
@bot.event
async def on_ready():
    # Получаем канал по ID для отправки сообщения
    channel = bot.get_channel(ALERT_CHANNEL_ID)  # Указываем свой канал, в который нужно отправить сообщение
    
    # Стартовое embed сообщение в выбранный канал с туториалом по использованию бота для пользователя / Start bot message in your dicord Channel with instruction for users
    embed = discord.Embed(title="💰🚗 Аренда машин", description="Все взаимодествие с ботом по аренде происходит в лс бота. В первый раз бот запросит ваш SteamID (PersonalID). После отправки SteamID ваш профиль сохранится и вы сможете арендовывать транспорт. Для получения подсказок команд - нажмите на кнопку ниже.", color=0x00ff00)
    
    rent_button = discord.ui.Button(label="Арендовать машину", style=discord.ButtonStyle.primary, custom_id="rent_button") # <-- Кнопка арендовать начального сообщения бота на сервере / Rent button name with command hint
    return_button = discord.ui.Button(label="Вернуть машину", style=discord.ButtonStyle.danger, custom_id="return_button") # <-- Кнопка вернуть начального сообщения бота на сервере / Return button name with command hint
    
    view = discord.ui.View()
    view.add_item(rent_button)
    view.add_item(return_button)

    await channel.send(embed=embed, view=view)

@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.data["custom_id"] == "rent_button":
        await interaction.response.send_message("Для аренды машины используйте команду !аренда в ЛС бота для продолжения.", ephemeral=True) # <-- Подсказка по команде аренды / Rent command hint
    
    elif interaction.data["custom_id"] == "return_button":
        await interaction.response.send_message("Для возврата машины используйте команду !возврат в ЛС бота для продолжения.", ephemeral=True) # <-- Подсказка по команде возврата / Return command hint

bot.run("BOT_TOKEN_HERE") # <-- Вставьте сюда токен вашего бота / Insert here your Discord Bot token
