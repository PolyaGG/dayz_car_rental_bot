import os
import json
import asyncio
import shutil
import uuid
import discord
import requests
from discord.ext import commands

# Пути к папкам
BANK_PATH = r"C:\\DayZServer1\\profiles\\KR_BANKING\\PlayerDataBase"
GARAGE_PATH = r"C:\\DayZServer1\\profiles\\RF\\GARAGE\\players"
CARS_CONFIG_FILE = "cars_config.json"
VEHICLE_TEMPLATES_PATH = "vehicles_templates"
USER_DATA_PATH = "user_data.json"
WEBHOOK_URL = " "  # Вставьте сюда URL вашего вебхука
ALERT_CHANNEL_ID = 111111111111  # <-- сюда вставь ID канала для cтартового сообщения


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

def send_log_to_webhook(message: str):
    embed = {
        "embeds": [
            {
                "title": "Аренда Авто",
                "description": message,
                "color": 0x00ff00,  # Зеленый цвет
                "footer": {
                    "text": "Car rent logger",
                }
            }
        ]
    }
    
    try:
        response = requests.post(WEBHOOK_URL, json=embed)
        if response.status_code != 200:
            print(f"Ошибка при отправке сообщения в вебхук: {response.status_code}")
    except Exception as e:
        print(f"Ошибка при отправке логов в вебхук: {e}")

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
        logged = False
        while True:
            await asyncio.sleep(600)  # 10 минутное ожидание

            account_file = os.path.join(BANK_PATH, f"{steam_id}.json")
            insufficient = False  # флаг для проверки недостаточности средств

            try:
                with open(account_file, "r+", encoding="utf-8") as f:
                    data = json.load(f)
                    balance = data.get("m_OwnedCurrency", 0)
                    new_balance = balance - price

                    if new_balance < 0:
                        await user.send(f"⚠️ У вас на счету недостаточно средств для оплаты поездки. Баланс уходит в долг. Верните автомобиль в гараж! Ваш долг: {new_balance}₽")
                        if logged == False:
                              send_log_to_webhook(f"❌ УГОН АВТО. Пользователь {user.name} не вернул машину!")
                        data["m_OwnedCurrency"] = new_balance
                        f.seek(0)
                        json.dump(data, f, ensure_ascii=False, indent=4)
                        f.truncate()
                        insufficient = True
                        logged = True
                        rental = active_rentals.get(steam_id)
                        if rental:
                            car_uuid = rental.get("uuid")
                            car_path = os.path.join(GARAGE_PATH, steam_id, "garage", f"{car_uuid}.json")
                            
                            if os.path.isfile(car_path):
                                await user.send("⚠️ У вас на счету недостаточно средств для оплаты поездки. Машина была изъята из гаража!")
                                os.remove(car_path) 
                                active_rentals.pop(steam_id, None)
                                send_log_to_webhook(f"❌ Машина изъята. Пользователь {user.name} не вернул машину, долг: {new_balance}₽")
                                break
                            else:
                                continue
                    else:
                        data["m_OwnedCurrency"] = new_balance
                        f.seek(0)
                        json.dump(data, f, ensure_ascii=False, indent=4)
                        f.truncate()
            except Exception as e:
               print(f"Ошибка при обновлении баланса: {e}")
               insufficient = True

    except asyncio.CancelledError:
        active_rentals.pop(steam_id, None)



@bot.command(name="аренда")
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

            try:
                await message.delete()
            except discord.errors.Forbidden:
                pass 

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

                    await interaction.response.edit_message(content=f"✅ Вы арендовали {car_name}! Приятной поездки. Для завершения аренды поставьте автомобиль в гараж и используйте команду !возврат", view=None)
                    send_log_to_webhook(f"✅ Аренда машины. Пользователь {ctx.author.name} арендовал машину: {car_name} с ценой {car_price}₽")
                except Exception as e:
                    print(f"[ERROR] Ошибка при обработке кнопки: {e}")
                    try:
                        await interaction.response.send_message("Произошла ошибка при аренде.", ephemeral=True)
                    except:
                        pass
            return callback

    view = CarSelectView(ctx.author.id)
    await ctx.author.send(f"Ваш баланс: {balance}₽. Цена указана за 10 минут аренды. Выберите машину:", view=view)

@bot.command(name="возврат")
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
        send_log_to_webhook(f"✅ Машина возвращена. Пользователь {ctx.author.name} вернул машину с UUID: {car_uuid}")
    else:
        await ctx.author.send("⚠️ Машина не найдена в гараже. Возврат невозможен.")
       
@bot.event
async def on_ready():
    channel = bot.get_channel(ALERT_CHANNEL_ID)
    
    embed = discord.Embed(title="💰🚗 Аренда машин", description="Все взаимодествие с ботом по аренде происходит в лс бота. В первый раз бот запросит ваш SteamID (PersonalID). После отправки SteamID ваш профиль сохранится и вы сможете арендовывать транспорт. Для получения подсказок команд - нажмите на кнопку ниже.", color=0x00ff00)

    rent_button = discord.ui.Button(label="Арендовать машину", style=discord.ButtonStyle.primary, custom_id="rent_button")
    return_button = discord.ui.Button(label="Вернуть машину", style=discord.ButtonStyle.danger, custom_id="return_button")
    
    view = discord.ui.View()
    view.add_item(rent_button)
    view.add_item(return_button)

    # Отправляем сообщение с кнопками
    await channel.send(embed=embed, view=view)

@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.data["custom_id"] == "rent_button":
        await interaction.response.send_message("Для аренды машины используйте команду !аренда в ЛС бота для продолжения.", ephemeral=True)
    
    elif interaction.data["custom_id"] == "return_button":
        await interaction.response.send_message("Для возврата машины используйте команду !возврат в ЛС бота для продолжения.", ephemeral=True)

bot.run("BOT_TOKEN_HERE")
