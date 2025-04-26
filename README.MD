# 📝 Описание проекта | Project Description

### Русский:

DayZ Rental Bot — это Discord-бот для управления арендой автомобилей на сервере DayZ. Игроки могут арендовать транспорт через Discord, оплачивая аренду каждые 10 минут. Бот автоматически создаёт файлы машин в виртуальном гараже, списывает деньги с банковского счёта игрока и удаляет машину в случае нехватки средств.

### English:

DayZ Rental Bot is a Discord bot for managing vehicle rentals on a DayZ server. Players can rent vehicles through Discord, with rental fees deducted every 10 minutes. The bot automatically creates vehicle files in a virtual garage, deducts money from the player's bank account, and removes the vehicle if funds run out.


#РУССКИЙ:

# 📖 Гайд по настройке и использованию DayZ Rental Bot by Polyagg

## ⚙️ Требуемые моды

1. RF Garage
2. Advanced Banking V2

## 📂 Структура проекта

```
dayz_rental_bot/
├── bot.py                        # Основной скрипт Discord-бота
├── cars_config.json              # Список машин для аренды
├── vehicles_templates/           # Шаблоны машин
│   ├── BMW_E28.json
│   ├── Mercedes_Sprinter.json
│   └── ...
```

## ⚙️ Установка и настройка

1. Установи Python (если нету), затем установи зависимости:
```bash
pip install discord.py
```

2. В файле `bot.py`:
- Замени `YOUR_BOT_TOKEN` на токен своего Discord-бота.
- Укажи ID канала для алертов в `ALERT_CHANNEL_ID`.

3. Проверь пути к папкам BANK_PATH и GARAGE_PATH, чтобы они совпадали с реальными на сервере DayZ.

## 📦 Настройка машин

1. В `cars_config.json` добавь машины для аренды в формате:
```json
[
  {
    "classname": "BMW_E28",    "В этой строке указывается класснейм самой машины, должен совпадать с названием файла в папке с шаблонами"
    "name": "BMW E28",         "В этой строке указывается название авто в боте (его увидят игроки)"
    "price": 100,              "В этой строке указывается цена аренды за 10 минут"
  },
  {
    "classname": "Mercedes_Sprinter",
    "name": "Mercedes Sprinter Пассажирский",
    "price": 500
  }
]
```

2. В папке `vehicles_templates/` создай файлы-шаблоны машин с именами `<classname>.json`.

**Важно:** Файл шаблона обязательно должен содержать поля `ownerId` и `uuid`, которые бот автоматически заменит при аренде.

## 🚀 Как пользоваться

1. Запусти бота:

Открой Powershell (Win+R -> powershell)

В powershell открой директорию с основным файлом bot.py
```bash
cd путь_к_папке_с_ботом
```

Затем введи эту команду:
```bash
python bot.py
```

2. В Discord используй команду аренды:
```
!rent <SteamID>
```
Пример:
```
!rent 76561198012345678
```

3. Выбери машину через кнопки.

4. Бот создаст машину в гараже игрока и будет списывать деньги каждые 10 минут.

5. Чтобы вернуть машину:
```
!return <SteamID>
```
Пример:
```
!return 76561198012345678
```

## 🔥 Особенности

- Если у игрока недостаточно денег для аренды — аренда не начнётся.
- Если деньги закончатся в процессе аренды — бот удалит машину и отправит алерт в канал.
- Кнопки выбора машины работают без ограничения по времени.
- Поддерживается несколько одновременных аренд.

## 🚨 Возможные проблемы

- **Кнопки не работают:** Бот перезапускался. Просто вызови `!rent` снова.
- **Нет шаблона машины:** Машина не появится в списке аренды, пока не добавишь шаблон JSON.

---

# ✅ Быстрая таблица команд

| Действие            | Команда                  |
|---------------------|---------------------------|
| Арендовать машину    | `!rent <SteamID>`         |
| Вернуть машину       | `!return <SteamID>`       |

---

Удачной аренды! 🚗💨

# ENGILISH:

# 📖 Guide to Setting Up and Using DayZ Rental Bot by Polyagg

## ⚙️ Required Mods
- RF Garage
- Advanced Banking V2

## 📂 Project Structure
```
dayz_rental_bot/
├── bot.py                        # Main Discord bot script
├── cars_config.json              # List of vehicles available for rent
├── vehicles_templates/           # Vehicle templates
│   ├── BMW_E28.json
│   ├── Mercedes_Sprinter.json
│   └── ...
```

## ⚙️ Installation and Setup

1. Install Python (if not installed yet), then install the required dependency:
```bash
pip install discord.py
```

2. In `bot.py`:
- Replace `YOUR_BOT_TOKEN` with your Discord bot token.
- Set your alert channel ID in `ALERT_CHANNEL_ID`.

3. Check the BANK_PATH and GARAGE_PATH variables to match your actual DayZ server directories.

## 📦 Configuring Vehicles

In `cars_config.json`, add the vehicles in the following format:
```json
[
  {
    "classname": "BMW_E28",    "This should match the vehicle classname and template filename."
    "name": "BMW E28",         "This is the display name that players will see in Discord."
    "price": 100               "This is the rental price per 10 minutes."
  },
  {
    "classname": "Mercedes_Sprinter",
    "name": "Mercedes Sprinter Passenger",
    "price": 500
  }
]
```

In the `vehicles_templates/` folder, create a JSON template file for each vehicle named `<classname>.json`.

**Important:** The template must include `ownerId` and `uuid` fields, which the bot will automatically replace during rental.

## 🚀 How to Use

1. Launch the bot:
Open PowerShell (Win+R -> powershell)

Navigate to the bot's folder:
```bash
cd path_to_your_bot_folder
```
Then run:
```bash
python bot.py
```

2. In Discord, use the rental command:
```
!rent <SteamID>
```
Example:
```
!rent 76561198012345678
```

3. Select a vehicle via the interactive buttons.

4. The bot will create the rented vehicle in the player's garage and deduct rental fees every 10 minutes.

5. To return a vehicle:
```
!return <SteamID>
```
Example:
```
!return 76561198012345678
```

## 🔥 Features

- If the player doesn't have enough money, the rental won't start.
- If funds run out during rental, the bot will remove the vehicle and send an alert.
- Vehicle selection buttons remain active indefinitely.
- Supports multiple simultaneous rentals.

## 🚨 Potential Issues

- **Buttons don't work:** The bot was restarted. Just use `!rent` again.
- **Missing vehicle template:** Vehicles without a matching template won't appear in the rental list.

---

# ✅ Quick Commands Table

| Action               | Command                  |
|----------------------|---------------------------|
| Rent a vehicle        | `!rent <SteamID>`         |
| Return a vehicle      | `!return <SteamID>`       |

---

Happy renting! 🚗💨


