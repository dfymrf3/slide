import asyncio
import json
import os
import random
import re
import math
from datetime import datetime, date, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# ================= КОНФИГУРАЦИЯ =================
BOT_TOKEN = "8055773278:AAG62fan_MG8xoVcPAI7Dm2fSCIGiVwiJ6c"
ADMIN_ID = 1387706327  # Твой ID
DATA_FILE = "stats.json"
PENDING_FILE = "pending.json"  # Заявки на модерацию
IMAGES_FOLDER = "images"

PENALTY_PERCENT = 2
WARNING_HOUR = 22

# Упражнения, требующие видео (можно настроить)
REQUIRE_VIDEO = True  # True = все упражнения требуют видео

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
scheduler = AsyncIOScheduler()

# ================= СИСТЕМА УРОВНЕЙ =================

def generate_levels(max_level=80):
    levels = {}
    base_xp = 50
    titles = {
        1: "Новобранец", 5: "Ученик", 10: "Адепт", 15: "Боец", 20: "Воин",
        25: "Ветеран", 30: "Элита", 35: "Мастер", 40: "Эксперт", 45: "Чемпион",
        50: "Герой", 55: "Легенда", 60: "Мифический", 65: "Эпический",
        70: "Бессмертный", 75: "Полубог", 80: "Титан"
    }
    for level in range(1, max_level + 1):
        xp = int(base_xp * (level ** 1.8))
        title = "Воин"
        for lvl, t in sorted(titles.items()):
            if level >= lvl:
                title = t
        levels[level] = {"xp": xp, "title": title}
    return levels

LEVELS = generate_levels(80)

# ================= ДОСТИЖЕНИЯ =================

ACHIEVEMENTS = {
    "squats_100": {"name": "🦵 Первые шаги", "description": "100 приседаний", "category": "repetitions", "exercise": "Приседания", "required": 100, "xp_reward": 50, "icon": "🥉"},
    "squats_500": {"name": "🦵 Крепкие ноги", "description": "500 приседаний", "category": "repetitions", "exercise": "Приседания", "required": 500, "xp_reward": 150, "icon": "🥈"},
    "squats_1000": {"name": "🦵 Стальные ноги", "description": "1000 приседаний", "category": "repetitions", "exercise": "Приседания", "required": 1000, "xp_reward": 300, "icon": "🥇"},
    "pullups_50": {"name": "💪 Первое подтягивание", "description": "50 подтягиваний", "category": "repetitions", "exercise": "Подтягивания", "required": 50, "xp_reward": 75, "icon": "🥉"},
    "pullups_200": {"name": "💪 Сильные руки", "description": "200 подтягиваний", "category": "repetitions", "exercise": "Подтягивания", "required": 200, "xp_reward": 200, "icon": "🥈"},
    "pullups_500": {"name": "💪 Железный хват", "description": "500 подтягиваний", "category": "repetitions", "exercise": "Подтягивания", "required": 500, "xp_reward": 400, "icon": "🥇"},
    "abs_100": {"name": "🔥 Пресс новичка", "description": "100 на пресс", "category": "repetitions", "exercise": "Пресс", "required": 100, "xp_reward": 30, "icon": "🥉"},
    "abs_500": {"name": "🔥 Крепкий кор", "description": "500 на пресс", "category": "repetitions", "exercise": "Пресс", "required": 500, "xp_reward": 100, "icon": "🥈"},
    "days_7": {"name": "📅 Неделя силы", "description": "7 дней тренировок", "category": "days", "required": 7, "xp_reward": 100, "icon": "🌿"},
    "days_30": {"name": "📅 Месяц дисциплины", "description": "30 дней тренировок", "category": "days", "required": 30, "xp_reward": 500, "icon": "⭐"},
    "streak_7": {"name": "🔥 Неделя без пропусков", "description": "7 дней подряд", "category": "streak", "required": 7, "xp_reward": 200, "icon": "🔥"},
    "streak_30": {"name": "🔥 Месяц подряд!", "description": "30 дней подряд", "category": "streak", "required": 30, "xp_reward": 1500, "icon": "💎"},
    "level_10": {"name": "🎮 Уровень 10", "description": "Достигни 10 уровня", "category": "level", "required": 10, "xp_reward": 100, "icon": "🎮"},
    "level_50": {"name": "🎮 Полпути", "description": "Достигни 50 уровня", "category": "level", "required": 50, "xp_reward": 1000, "icon": "⭐"},
    "total_1000": {"name": "🏋️ Тысяча!", "description": "1000 повторений", "category": "total", "required": 1000, "xp_reward": 200, "icon": "🏋️"},
}

# ================= RPG СИСТЕМА =================

RACES = {
    "human": {"name": "👨 Человек", "emoji": "👨", "bonus": "Приседания", "bonus_percent": 10, "description": "+10% XP за приседания"},
    "orc": {"name": "👹 Орк", "emoji": "👹", "bonus": "Подтягивания", "bonus_percent": 15, "description": "+15% XP за подтягивания"},
    "elf": {"name": "🧝 Эльф", "emoji": "🧝", "bonus": "Пресс", "bonus_percent": 15, "description": "+15% XP за пресс"},
    "dwarf": {"name": "🧔 Гном", "emoji": "🧔", "bonus": "Приседания", "bonus_percent": 20, "description": "+20% XP за приседания"},
    "undead": {"name": "💀 Нежить", "emoji": "💀", "bonus": "all", "bonus_percent": 5, "description": "+5% XP за ВСЁ"},
    "tauren": {"name": "🐂 Таурен", "emoji": "🐂", "bonus": "Подтягивания", "bonus_percent": 20, "description": "+20% XP за подтягивания"}
}

CLASSES = {
    "warrior": {"name": "⚔️ Воин", "emoji": "⚔️", "description": "+10% ко всему XP", "multiplier": 1.1},
    "mage": {"name": "🔮 Маг", "emoji": "🔮", "description": "+15% XP за пресс", "multiplier": 1.0, "exercise_bonus": {"Пресс": 0.15}},
    "rogue": {"name": "🗡️ Разбойник", "emoji": "🗡️", "description": "+10% XP", "multiplier": 1.1},
    "paladin": {"name": "🛡️ Паладин", "emoji": "🛡️", "description": "+5% XP, +20% за подтягивания", "multiplier": 1.05, "exercise_bonus": {"Подтягивания": 0.20}}
}

GENDERS = {
    "male": {"name": "♂️ Мужской", "emoji": "♂️"},
    "female": {"name": "♀️ Женский", "emoji": "♀️"}
}

BASE_XP = {"Приседания": 2, "Подтягивания": 5, "Пресс": 1}

# ================= СОСТОЯНИЯ =================

class CharacterCreation(StatesGroup):
    choosing_race = State()
    choosing_class = State()
    choosing_gender = State()
    choosing_name = State()

class ReminderStates(StatesGroup):
    waiting_for_custom_time = State()

class ExerciseStates(StatesGroup):
    waiting_for_video = State()

class AdminStates(StatesGroup):
    viewing_user = State()
    editing_xp = State()
    editing_level = State()
    editing_streak = State()
    adding_achievement = State()
    removing_achievement = State()
    sending_message = State()
    broadcast_message = State()
    confirming_delete = State()
    reject_reason = State()

# ================= РАБОТА С ДАННЫМИ =================

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"users": {}, "stats": {}, "characters": {}, "banned": []}
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
        for key in ["users", "stats", "characters", "banned"]:
            if key not in data:
                data[key] = [] if key == "banned" else {}
        return data

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def load_pending():
    """Загрузить ожидающие заявки"""
    if not os.path.exists(PENDING_FILE):
        return {}
    with open(PENDING_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_pending(data):
    """Сохранить ожидающие заявки"""
    with open(PENDING_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def add_pending_request(user_id: str, exercise: str, count: int, video_file_id: str) -> str:
    """Добавить заявку на модерацию, вернуть ID заявки"""
    pending = load_pending()
    request_id = f"{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    pending[request_id] = {
        "user_id": user_id,
        "exercise": exercise,
        "count": count,
        "video_file_id": video_file_id,
        "created_at": str(datetime.now()),
        "status": "pending"  # pending, approved, rejected
    }
    save_pending(pending)
    return request_id

def get_pending_request(request_id: str) -> dict | None:
    """Получить заявку по ID"""
    pending = load_pending()
    return pending.get(request_id)

def update_pending_request(request_id: str, status: str, admin_comment: str = None):
    """Обновить статус заявки"""
    pending = load_pending()
    if request_id in pending:
        pending[request_id]["status"] = status
        pending[request_id]["processed_at"] = str(datetime.now())
        if admin_comment:
            pending[request_id]["admin_comment"] = admin_comment
        save_pending(pending)

def get_all_pending_requests() -> dict:
    """Получить все ожидающие заявки"""
    pending = load_pending()
    return {k: v for k, v in pending.items() if v["status"] == "pending"}

def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID

def is_banned(user_id: str) -> bool:
    data = load_data()
    return user_id in data.get("banned", [])

def get_character(user_id: str) -> dict | None:
    data = load_data()
    return data["characters"].get(user_id)

def create_character(user_id: str, race: str, char_class: str, gender: str, name: str):
    data = load_data()
    today = str(date.today())
    data["characters"][user_id] = {
        "race": race, "class": char_class, "gender": gender, "name": name,
        "xp": 0, "level": 1, "achievements": [], "combo_count": 0,
        "current_streak": 0, "best_streak": 0, "last_training_date": None,
        "last_penalty_check": today, "total_penalty_xp": 0, "warnings_sent": [],
        "created_at": str(datetime.now())
    }
    save_data(data)

def delete_character(user_id: str):
    data = load_data()
    if user_id in data["characters"]:
        del data["characters"][user_id]
    if user_id in data["stats"]:
        del data["stats"][user_id]
    save_data(data)

def calculate_level(xp: int) -> int:
    level = 1
    for lvl, lvl_data in LEVELS.items():
        if xp >= lvl_data["xp"]:
            level = lvl
    return min(level, 80)

def get_title(level: int) -> str:
    return LEVELS.get(level, {}).get("title", "Воин")

def get_xp_for_next_level(current_level: int) -> int:
    next_level = current_level + 1
    return LEVELS.get(next_level, LEVELS[80])["xp"]

def check_and_apply_penalties(user_id: str) -> dict:
    data = load_data()
    char = data["characters"].get(user_id)
    if not char:
        return {"penalties": 0, "xp_lost": 0, "level_lost": False}
    
    today = date.today()
    today_str = str(today)
    last_check_str = char.get("last_penalty_check")
    
    if not last_check_str:
        char["last_penalty_check"] = today_str
        data["characters"][user_id] = char
        save_data(data)
        return {"penalties": 0, "xp_lost": 0, "level_lost": False}
    
    last_check = datetime.strptime(last_check_str, "%Y-%m-%d").date()
    user_stats = data["stats"].get(user_id, {})
    
    penalties = 0
    total_xp_lost = 0
    old_level = char["level"]
    
    current_date = last_check + timedelta(days=1)
    while current_date < today:
        if str(current_date) not in user_stats:
            penalty_xp = int(char["xp"] * PENALTY_PERCENT / 100)
            if penalty_xp > 0:
                char["xp"] = max(0, char["xp"] - penalty_xp)
                char["level"] = calculate_level(char["xp"])
                total_xp_lost += penalty_xp
                penalties += 1
                char["current_streak"] = 0
        current_date += timedelta(days=1)
    
    char["last_penalty_check"] = today_str
    char["total_penalty_xp"] = char.get("total_penalty_xp", 0) + total_xp_lost
    data["characters"][user_id] = char
    save_data(data)
    
    return {"penalties": penalties, "xp_lost": total_xp_lost, "level_lost": char["level"] < old_level,
            "new_level": char["level"], "old_level": old_level}

def update_streak(user_id: str):
    data = load_data()
    char = data["characters"].get(user_id)
    if not char:
        return
    
    today = date.today()
    today_str = str(today)
    yesterday_str = str(today - timedelta(days=1))
    last_training = char.get("last_training_date")
    
    if last_training == today_str:
        return
    elif last_training == yesterday_str:
        char["current_streak"] = char.get("current_streak", 0) + 1
    else:
        char["current_streak"] = 1
    
    if char["current_streak"] > char.get("best_streak", 0):
        char["best_streak"] = char["current_streak"]
    
    char["last_training_date"] = today_str
    data["characters"][user_id] = char
    save_data(data)

def has_trained_today(user_id: str) -> bool:
    data = load_data()
    return str(date.today()) in data.get("stats", {}).get(user_id, {})

def check_achievements(user_id: str) -> list:
    data = load_data()
    char = data["characters"].get(user_id)
    if not char:
        return []
    
    user_stats = data["stats"].get(user_id, {})
    current_achievements = char.get("achievements", [])
    new_achievements = []
    
    totals = {"Приседания": 0, "Подтягивания": 0, "Пресс": 0}
    for day_stats in user_stats.values():
        for ex, val in day_stats.items():
            if ex in totals:
                totals[ex] += val
    
    total_all = sum(totals.values())
    days_count = len(user_stats)
    streak = char.get("current_streak", 0)
    
    for ach_id, ach in ACHIEVEMENTS.items():
        if ach_id in current_achievements:
            continue
        earned = False
        if ach["category"] == "repetitions" and totals.get(ach["exercise"], 0) >= ach["required"]:
            earned = True
        elif ach["category"] == "days" and days_count >= ach["required"]:
            earned = True
        elif ach["category"] == "streak" and streak >= ach["required"]:
            earned = True
        elif ach["category"] == "level" and char["level"] >= ach["required"]:
            earned = True
        elif ach["category"] == "total" and total_all >= ach["required"]:
            earned = True
        
        if earned:
            new_achievements.append(ach_id)
            current_achievements.append(ach_id)
            char["xp"] += ach["xp_reward"]
            char["level"] = calculate_level(char["xp"])
    
    if new_achievements:
        char["achievements"] = current_achievements
        data["characters"][user_id] = char
        save_data(data)
    return new_achievements

def add_exercise_to_stats(user_id: str, exercise: str, count: int) -> tuple:
    """Добавить упражнение в статистику и начислить XP"""
    data = load_data()
    char = data["characters"].get(user_id)
    if not char:
        return 0, None, []
    
    today = str(date.today())
    
    # Добавляем в статистику
    if user_id not in data["stats"]:
        data["stats"][user_id] = {}
    if today not in data["stats"][user_id]:
        data["stats"][user_id][today] = {"Приседания": 0, "Подтягивания": 0, "Пресс": 0}
    data["stats"][user_id][today][exercise] += count
    save_data(data)
    
    # Считаем XP
    base_xp = BASE_XP.get(exercise, 1) * count
    race_data = RACES.get(char["race"], {})
    race_bonus = 1.0
    if race_data.get("bonus") == "all":
        race_bonus = 1 + race_data.get("bonus_percent", 0) / 100
    elif race_data.get("bonus") == exercise:
        race_bonus = 1 + race_data.get("bonus_percent", 0) / 100
    
    class_data = CLASSES.get(char["class"], {})
    class_bonus = class_data.get("multiplier", 1.0)
    if exercise in class_data.get("exercise_bonus", {}):
        class_bonus += class_data["exercise_bonus"][exercise]
    
    total_xp = int(base_xp * race_bonus * class_bonus)
    old_level = char["level"]
    
    # Обновляем персонажа
    data = load_data()
    char = data["characters"][user_id]
    char["xp"] += total_xp
    char["level"] = calculate_level(char["xp"])
    
    # Обновляем серию
    today_str = str(date.today())
    yesterday_str = str(date.today() - timedelta(days=1))
    last_training = char.get("last_training_date")
    
    if last_training != today_str:
        if last_training == yesterday_str:
            char["current_streak"] = char.get("current_streak", 0) + 1
        else:
            char["current_streak"] = 1
        
        if char["current_streak"] > char.get("best_streak", 0):
            char["best_streak"] = char["current_streak"]
        char["last_training_date"] = today_str
    
    # Комбо
    today_stats = data["stats"][user_id][today]
    if all(today_stats.get(ex, 0) > 0 for ex in ["Приседания", "Подтягивания", "Пресс"]):
        if char.get("last_combo_date") != today:
            char["combo_count"] = char.get("combo_count", 0) + 1
            char["last_combo_date"] = today
    
    data["characters"][user_id] = char
    save_data(data)
    
    level_up = char["level"] if char["level"] > old_level else None
    new_achievements = check_achievements(user_id)
    
    return total_xp, level_up, new_achievements

def save_user_info(user: types.User):
    data = load_data()
    user_id = str(user.id)
    existing = data["users"].get(user_id, {})
    name = user.first_name or ""
    if user.last_name:
        name += f" {user.last_name}"
    data["users"][user_id] = {
        "name": name or user.username or f"User_{user.id}",
        "username": user.username,
        "last_seen": str(datetime.now()),
        "reminder_time": existing.get("reminder_time")
    }
    save_data(data)

def set_reminder_time(user_id: str, time_str: str | None):
    data = load_data()
    if user_id in data["users"]:
        data["users"][user_id]["reminder_time"] = time_str
        save_data(data)

def get_reminder_time(user_id: str) -> str | None:
    data = load_data()
    return data["users"].get(user_id, {}).get("reminder_time")

def get_today_stats(user_id: str) -> dict:
    data = load_data()
    return data.get("stats", {}).get(user_id, {}).get(str(date.today()), {"Приседания": 0, "Подтягивания": 0, "Пресс": 0})

def get_user_total_stats(user_id: str) -> tuple:
    data = load_data()
    totals = {"Приседания": 0, "Подтягивания": 0, "Пресс": 0}
    days_count = 0
    for day_stats in data.get("stats", {}).get(user_id, {}).values():
        days_count += 1
        for ex, val in day_stats.items():
            if ex in totals:
                totals[ex] += val
    return totals, days_count

# ================= КЛАВИАТУРЫ =================

def get_main_keyboard():
    kb = [
        [KeyboardButton(text="Присед 30"), KeyboardButton(text="Подтягивание 10")],
        [KeyboardButton(text="Пресс 50"), KeyboardButton(text="👤 Мой персонаж")],
        [KeyboardButton(text="🏆 Достижения"), KeyboardButton(text="📊 Статистика")],
        [KeyboardButton(text="👥 Рейтинг"), KeyboardButton(text="📖 Техника")],
        [KeyboardButton(text="⏰ Напоминания"), KeyboardButton(text="⚙️ Настройки")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_cancel_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отменить")]],
        resize_keyboard=True
    )

def get_admin_keyboard():
    kb = [
        [KeyboardButton(text="👥 Все пользователи")],
        [KeyboardButton(text="📋 Заявки на модерацию")],
        [KeyboardButton(text="📢 Рассылка всем")],
        [KeyboardButton(text="📊 Статистика бота")],
        [KeyboardButton(text="🔙 Выйти из админки")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_moderation_keyboard(request_id: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Одобрить", callback_data=f"mod_approve_{request_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"mod_reject_{request_id}")
        ]
    ])

def get_user_edit_keyboard(user_id: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Изменить XP", callback_data=f"admin_edit_xp_{user_id}")],
        [InlineKeyboardButton(text="📊 Изменить уровень", callback_data=f"admin_edit_level_{user_id}")],
        [InlineKeyboardButton(text="🔥 Изменить серию", callback_data=f"admin_edit_streak_{user_id}")],
        [InlineKeyboardButton(text="🎖️ Добавить достижение", callback_data=f"admin_add_ach_{user_id}")],
        [InlineKeyboardButton(text="💸 Сбросить штрафы", callback_data=f"admin_reset_penalty_{user_id}")],
        [InlineKeyboardButton(text="📨 Отправить сообщение", callback_data=f"admin_send_msg_{user_id}")],
        [InlineKeyboardButton(text="🚫 Бан/Разбан", callback_data=f"admin_ban_{user_id}")],
        [InlineKeyboardButton(text="🗑️ Удалить персонажа", callback_data=f"admin_delete_{user_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back_list")]
    ])

def get_race_keyboard():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=r["name"])] for r in RACES.values()], resize_keyboard=True)

def get_class_keyboard():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=c["name"])] for c in CLASSES.values()], resize_keyboard=True)

def get_gender_keyboard():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="♂️ Мужской"), KeyboardButton(text="♀️ Женский")]], resize_keyboard=True)

def get_settings_keyboard():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🗑️ Удалить персонажа")], [KeyboardButton(text="🔙 Главное меню")]], resize_keyboard=True)

def get_technique_keyboard():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🦵 Техника приседаний")], [KeyboardButton(text="💪 Техника подтягиваний")],
        [KeyboardButton(text="🔥 Техника пресса")], [KeyboardButton(text="🔙 Главное меню")]
    ], resize_keyboard=True)

def get_reminder_keyboard():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🕐 08:00"), KeyboardButton(text="🕐 12:00"), KeyboardButton(text="🕐 18:00")],
        [KeyboardButton(text="🕐 20:00"), KeyboardButton(text="🕐 21:00"), KeyboardButton(text="🕐 22:00")],
        [KeyboardButton(text="✏️ Своё время"), KeyboardButton(text="🔕 Выключить")],
        [KeyboardButton(text="🔙 Главное меню")]
    ], resize_keyboard=True)

def get_confirm_delete_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, удалить", callback_data="confirm_delete")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_delete")]
    ])

# ================= МОДЕРАЦИЯ УПРАЖНЕНИЙ =================

@dp.message(F.text.regexp(r'^(присед|подтягивание|пресс)\s*:?\s*(\d+)$', flags=2))
async def exercise_request(message: types.Message, state: FSMContext):
    """Пользователь хочет записать упражнение"""
    await state.clear()
    user_id = str(message.from_user.id)
    
    if is_banned(user_id):
        await message.answer("🚫 Ты заблокирован!")
        return
    
    save_user_info(message.from_user)
    char = get_character(user_id)
    
    if not char:
        await message.answer("❌ Сначала создай персонажа! /start")
        return
    
    # Проверяем штрафы
    check_and_apply_penalties(user_id)
    
    # Парсим упражнение
    match = re.match(r'(присед|подтягивание|пресс)\s*:?\s*(\d+)', message.text, re.IGNORECASE)
    names = {"присед": "Приседания", "подтягивание": "Подтягивания", "пресс": "Пресс"}
    exercise = names[match.group(1).lower()]
    count = int(match.group(2))
    
    if count <= 0:
        await message.answer("❌ Количество должно быть больше 0!")
        return
    
    if count > 1000:
        await message.answer("❌ Слишком много! Максимум 1000 за раз.")
        return
    
    # Сохраняем данные для ожидания видео
    await state.set_state(ExerciseStates.waiting_for_video)
    await state.update_data(exercise=exercise, count=count)
    
    await message.answer(
        f"📹 **Отправь видео подтверждение!**\n\n"
        f"Упражнение: **{exercise}**\n"
        f"Количество: **{count}**\n\n"
        f"Запиши видео выполнения упражнения и отправь его сюда.\n"
        f"После проверки администратором результат будет засчитан! ✅\n\n"
        f"Или нажми «❌ Отменить»",
        parse_mode="Markdown",
        reply_markup=get_cancel_keyboard()
    )

@dp.message(ExerciseStates.waiting_for_video, F.text == "❌ Отменить")
async def cancel_video(message: types.Message, state: FSMContext):
    """Отмена отправки видео"""
    await state.clear()
    await message.answer("❌ Отменено", reply_markup=get_main_keyboard())

@dp.message(ExerciseStates.waiting_for_video, F.video)
async def process_video(message: types.Message, state: FSMContext):
    """Получено видео от пользователя"""
    user_id = str(message.from_user.id)
    data = await state.get_data()
    exercise = data.get("exercise")
    count = data.get("count")
    
    char = get_character(user_id)
    user_data = load_data()["users"].get(user_id, {})
    
    # Создаём заявку на модерацию
    request_id = add_pending_request(
        user_id=user_id,
        exercise=exercise,
        count=count,
        video_file_id=message.video.file_id
    )
    
    await state.clear()
    
    # Уведомляем пользователя
    await message.answer(
        f"✅ **Заявка отправлена на проверку!**\n\n"
        f"📋 Упражнение: {exercise}\n"
        f"🔢 Количество: {count}\n\n"
        f"Администратор проверит твоё видео и примет решение.\n"
        f"Ты получишь уведомление! 🔔",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )
    
    # Отправляем админу
    try:
        await bot.send_video(
            ADMIN_ID,
            video=message.video.file_id,
            caption=(
                f"📋 **Новая заявка на модерацию!**\n\n"
                f"👤 Игрок: **{char['name']}**\n"
                f"🆔 ID: `{user_id}`\n"
                f"📱 Username: @{user_data.get('username', 'нет')}\n"
                f"⭐ Уровень: {char['level']}\n\n"
                f"🏋️ Упражнение: **{exercise}**\n"
                f"🔢 Количество: **{count}**\n\n"
                f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}"
            ),
            parse_mode="Markdown",
            reply_markup=get_moderation_keyboard(request_id)
        )
    except Exception as e:
        print(f"Ошибка отправки админу: {e}")

@dp.message(ExerciseStates.waiting_for_video, F.video_note)
async def process_video_note(message: types.Message, state: FSMContext):
    """Получен кружок (видео-сообщение)"""
    user_id = str(message.from_user.id)
    data = await state.get_data()
    exercise = data.get("exercise")
    count = data.get("count")
    
    char = get_character(user_id)
    user_data = load_data()["users"].get(user_id, {})
    
    request_id = add_pending_request(
        user_id=user_id,
        exercise=exercise,
        count=count,
        video_file_id=message.video_note.file_id
    )
    
    await state.clear()
    
    await message.answer(
        f"✅ **Заявка отправлена!**\n\n"
        f"📋 {exercise}: {count}\n"
        f"Ожидай проверки! 🔔",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )
    
    try:
        await bot.send_video_note(
            ADMIN_ID,
            video_note=message.video_note.file_id
        )
        await bot.send_message(
            ADMIN_ID,
            f"📋 **Заявка от {char['name']}**\n\n"
            f"🆔 ID: `{user_id}`\n"
            f"📱 @{user_data.get('username', 'нет')}\n"
            f"⭐ Уровень: {char['level']}\n\n"
            f"🏋️ **{exercise}**: {count}\n\n"
            f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}",
            parse_mode="Markdown",
            reply_markup=get_moderation_keyboard(request_id)
        )
    except Exception as e:
        print(f"Ошибка: {e}")

@dp.message(ExerciseStates.waiting_for_video)
async def wrong_content(message: types.Message):
    """Пользователь отправил что-то другое вместо видео"""
    await message.answer(
        "❌ **Нужно отправить видео!**\n\n"
        "Отправь видео или видео-кружок с выполнением упражнения.\n"
        "Или нажми «❌ Отменить»",
        parse_mode="Markdown"
    )

# === Обработка решения админа ===

@dp.callback_query(F.data.startswith("mod_approve_"))
async def approve_request(callback: types.CallbackQuery):
    """Админ одобрил заявку"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!")
        return
    
    request_id = callback.data.replace("mod_approve_", "")
    request = get_pending_request(request_id)
    
    if not request:
        await callback.answer("Заявка не найдена!")
        return
    
    if request["status"] != "pending":
        await callback.answer("Заявка уже обработана!")
        return
    
    user_id = request["user_id"]
    exercise = request["exercise"]
    count = request["count"]
    
    # Добавляем упражнение в статистику
    xp, level_up, new_achs = add_exercise_to_stats(user_id, exercise, count)
    char = get_character(user_id)
    
    # Обновляем статус заявки
    update_pending_request(request_id, "approved")
    
    # Формируем сообщение для пользователя
    user_msg = (
        f"✅ **Заявка одобрена!**\n\n"
        f"🏋️ {exercise}: +{count}\n"
        f"⭐ +{xp} XP\n"
    )
    
    if level_up:
        user_msg += f"\n🎊 **LEVEL UP!** Уровень: {level_up}!\n"
    
    for ach_id in new_achs:
        ach = ACHIEVEMENTS[ach_id]
        user_msg += f"\n🏆 Достижение: {ach['icon']} {ach['name']}!"
    
    user_msg += f"\n\n👤 {char['name']} | Ур.{char['level']} | 🔥{char.get('current_streak', 0)}"
    
    # Уведомляем пользователя
    try:
        await bot.send_message(int(user_id), user_msg, parse_mode="Markdown", reply_markup=get_main_keyboard())
    except:
        pass
    
    # Обновляем сообщение админа
    await callback.message.edit_caption(
        caption=callback.message.caption + f"\n\n✅ **ОДОБРЕНО**\n+{xp} XP",
        parse_mode="Markdown"
    )
    await callback.answer("✅ Одобрено!")

@dp.callback_query(F.data.startswith("mod_reject_"))
async def reject_request_start(callback: types.CallbackQuery, state: FSMContext):
    """Админ хочет отклонить заявку"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!")
        return
    
    request_id = callback.data.replace("mod_reject_", "")
    request = get_pending_request(request_id)
    
    if not request:
        await callback.answer("Заявка не найдена!")
        return
    
    if request["status"] != "pending":
        await callback.answer("Заявка уже обработана!")
        return
    
    await state.set_state(AdminStates.reject_reason)
    await state.update_data(reject_request_id=request_id, reject_message_id=callback.message.message_id)
    
    # Кнопки для быстрого отказа
    quick_reasons = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📹 Плохое качество видео", callback_data="reject_reason_quality")],
        [InlineKeyboardButton(text="❌ Неправильная техника", callback_data="reject_reason_technique")],
        [InlineKeyboardButton(text="🔢 Не соответствует количество", callback_data="reject_reason_count")],
        [InlineKeyboardButton(text="🚫 Видео не соответствует", callback_data="reject_reason_wrong")],
        [InlineKeyboardButton(text="✏️ Своя причина", callback_data="reject_reason_custom")],
        [InlineKeyboardButton(text="🔙 Отмена", callback_data="reject_cancel")]
    ])
    
    await callback.message.answer(
        "❌ **Выбери причину отказа:**",
        parse_mode="Markdown",
        reply_markup=quick_reasons
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("reject_reason_"))
async def process_reject_reason(callback: types.CallbackQuery, state: FSMContext):
    """Обработка причины отказа"""
    if not is_admin(callback.from_user.id):
        return
    
    reason_type = callback.data.replace("reject_reason_", "")
    
    if reason_type == "cancel":
        await state.clear()
        await callback.message.delete()
        await callback.answer("Отменено")
        return
    
    if reason_type == "custom":
        await callback.message.edit_text(
            "✏️ **Напиши причину отказа:**\n\nИли напиши `отмена`",
            parse_mode="Markdown"
        )
        await callback.answer()
        return
    
    # Быстрые причины
    reasons = {
        "quality": "📹 Плохое качество видео. Пожалуйста, запиши видео с лучшим освещением и качеством.",
        "technique": "❌ Неправильная техника выполнения. Посмотри раздел «Техника» и попробуй снова.",
        "count": "🔢 Количество повторений на видео не соответствует заявленному.",
        "wrong": "🚫 Видео не соответствует упражнению."
    }
    
    reason = reasons.get(reason_type, "Заявка отклонена.")
    
    data = await state.get_data()
    request_id = data.get("reject_request_id")
    
    await finish_rejection(callback, state, request_id, reason)

@dp.message(AdminStates.reject_reason)
async def custom_reject_reason(message: types.Message, state: FSMContext):
    """Своя причина отказа"""
    if not is_admin(message.from_user.id):
        return
    
    if message.text.lower() == "отмена":
        await state.clear()
        await message.answer("Отменено", reply_markup=get_admin_keyboard())
        return
    
    data = await state.get_data()
    request_id = data.get("reject_request_id")
    
    await finish_rejection(message, state, request_id, message.text)

async def finish_rejection(event, state: FSMContext, request_id: str, reason: str):
    """Завершить отклонение заявки"""
    request = get_pending_request(request_id)
    
    if not request:
        if isinstance(event, types.CallbackQuery):
            await event.answer("Заявка не найдена!")
        return
    
    user_id = request["user_id"]
    exercise = request["exercise"]
    count = request["count"]
    char = get_character(user_id)
    
    # Обновляем статус
    update_pending_request(request_id, "rejected", reason)
    
    # Уведомляем пользователя
    try:
        await bot.send_message(
            int(user_id),
            f"❌ **Заявка отклонена**\n\n"
            f"🏋️ {exercise}: {count}\n\n"
            f"📝 **Причина:**\n{reason}\n\n"
            f"Попробуй отправить заявку снова! 💪",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
    except:
        pass
    
    await state.clear()
    
    if isinstance(event, types.CallbackQuery):
        await event.message.edit_text(f"❌ **Отклонено**\n\nПричина: {reason}", parse_mode="Markdown")
        await event.answer("❌ Отклонено")
    else:
        await event.answer(f"❌ Заявка {char['name']} отклонена", reply_markup=get_admin_keyboard())

# ================= АДМИН-ПАНЕЛЬ =================

@dp.message(Command("admin"))
async def cmd_admin(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет доступа!")
        return
    
    await state.clear()
    data = load_data()
    pending = get_all_pending_requests()
    
    await message.answer(
        f"🔐 **АДМИН-ПАНЕЛЬ**\n\n"
        f"👥 Пользователей: {len(data['characters'])}\n"
        f"📋 Заявок на модерации: {len(pending)}\n"
        f"🚫 Забанено: {len(data.get('banned', []))}",
        parse_mode="Markdown",
        reply_markup=get_admin_keyboard()
    )

@dp.message(F.text == "📋 Заявки на модерацию")
async def show_pending_requests(message: types.Message):
    """Показать все ожидающие заявки"""
    if not is_admin(message.from_user.id):
        return
    
    pending = get_all_pending_requests()
    
    if not pending:
        await message.answer("✅ Нет заявок на модерации!", reply_markup=get_admin_keyboard())
        return
    
    await message.answer(f"📋 **Заявки на модерации: {len(pending)}**", parse_mode="Markdown")
    
    for request_id, request in list(pending.items())[:10]:  # Показываем последние 10
        char = get_character(request["user_id"])
        if not char:
            continue
        
        try:
            # Отправляем видео с кнопками
            await bot.send_video(
                message.chat.id,
                video=request["video_file_id"],
                caption=(
                    f"👤 {char['name']} (Ур.{char['level']})\n"
                    f"🏋️ {request['exercise']}: {request['count']}\n"
                    f"📅 {request['created_at'][:16]}"
                ),
                reply_markup=get_moderation_keyboard(request_id)
            )
        except:
            # Если это был video_note
            try:
                await bot.send_video_note(message.chat.id, video_note=request["video_file_id"])
                await bot.send_message(
                    message.chat.id,
                    f"👤 {char['name']} | {request['exercise']}: {request['count']}",
                    reply_markup=get_moderation_keyboard(request_id)
                )
            except:
                pass

@dp.message(F.text == "🔙 Выйти из админки")
async def exit_admin(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer("👋 Вышел из админки", reply_markup=get_main_keyboard())

@dp.message(F.text == "👥 Все пользователи")
async def admin_list_users(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    
    data = load_data()
    characters = data.get("characters", {})
    
    if not characters:
        await message.answer("📭 Нет пользователей", reply_markup=get_admin_keyboard())
        return
    
    buttons = []
    for user_id, char in characters.items():
        status = "🚫" if user_id in data.get("banned", []) else "✅"
        buttons.append([InlineKeyboardButton(text=f"{status} {char['name']} (Ур.{char['level']})", callback_data=f"admin_view_{user_id}")])
    
    await message.answer(f"👥 **Пользователи** ({len(characters)})", parse_mode="Markdown", 
                         reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons[:20]))

@dp.callback_query(F.data.startswith("admin_view_"))
async def admin_view_user(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    
    user_id = callback.data.replace("admin_view_", "")
    data = load_data()
    char = data["characters"].get(user_id)
    user_info = data["users"].get(user_id, {})
    
    if not char:
        await callback.answer("Не найден!")
        return
    
    totals, days = get_user_total_stats(user_id)
    
    await callback.message.edit_text(
        f"👤 **{char['name']}**\n\n"
        f"🆔 `{user_id}`\n"
        f"📱 @{user_info.get('username', 'нет')}\n"
        f"🚫 Бан: {'Да' if user_id in data.get('banned', []) else 'Нет'}\n\n"
        f"⭐ Уровень: {char['level']} | XP: {char['xp']}\n"
        f"🔥 Серия: {char.get('current_streak', 0)}\n"
        f"💸 Штрафов: {char.get('total_penalty_xp', 0)} XP\n\n"
        f"📊 Всего: 🦵{totals['Приседания']} 💪{totals['Подтягивания']} 🔥{totals['Пресс']}",
        parse_mode="Markdown",
        reply_markup=get_user_edit_keyboard(user_id)
    )

@dp.callback_query(F.data == "admin_back_list")
async def admin_back(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    
    data = load_data()
    buttons = [[InlineKeyboardButton(text=f"{c['name']} (Ур.{c['level']})", callback_data=f"admin_view_{uid}")] 
               for uid, c in data["characters"].items()][:20]
    
    await callback.message.edit_text(f"👥 **Пользователи**", parse_mode="Markdown",
                                     reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

# === Редактирование пользователя ===

@dp.callback_query(F.data.startswith("admin_edit_xp_"))
async def admin_edit_xp(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    user_id = callback.data.replace("admin_edit_xp_", "")
    char = get_character(user_id)
    await state.set_state(AdminStates.editing_xp)
    await state.update_data(editing_user_id=user_id)
    await callback.message.answer(f"✏️ XP для {char['name']} (сейчас {char['xp']})\n\nВведи: `5000` или `+500` или `-200`\nИли `отмена`", parse_mode="Markdown")
    await callback.answer()

@dp.message(AdminStates.editing_xp)
async def process_edit_xp(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    if message.text.lower() == "отмена":
        await state.clear()
        await message.answer("Отменено", reply_markup=get_admin_keyboard())
        return
    
    data = await state.get_data()
    user_id = data["editing_user_id"]
    all_data = load_data()
    char = all_data["characters"][user_id]
    old_xp = char["xp"]
    
    try:
        if message.text.startswith("+"):
            new_xp = old_xp + int(message.text[1:])
        elif message.text.startswith("-"):
            new_xp = max(0, old_xp - int(message.text[1:]))
        else:
            new_xp = max(0, int(message.text))
        
        char["xp"] = new_xp
        char["level"] = calculate_level(new_xp)
        all_data["characters"][user_id] = char
        save_data(all_data)
        
        await message.answer(f"✅ {char['name']}: {old_xp} → {new_xp} XP (Ур.{char['level']})", reply_markup=get_admin_keyboard())
        await state.clear()
    except:
        await message.answer("❌ Ошибка! Введи число")

@dp.callback_query(F.data.startswith("admin_edit_level_"))
async def admin_edit_level(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    user_id = callback.data.replace("admin_edit_level_", "")
    char = get_character(user_id)
    await state.set_state(AdminStates.editing_level)
    await state.update_data(editing_user_id=user_id)
    await callback.message.answer(f"📊 Уровень {char['name']} (сейчас {char['level']})\n\nВведи 1-80 или `отмена`", parse_mode="Markdown")
    await callback.answer()

@dp.message(AdminStates.editing_level)
async def process_edit_level(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    if message.text.lower() == "отмена":
        await state.clear()
        await message.answer("Отменено", reply_markup=get_admin_keyboard())
        return
    
    data = await state.get_data()
    user_id = data["editing_user_id"]
    
    try:
        new_level = int(message.text)
        if not 1 <= new_level <= 80:
            raise ValueError()
        
        all_data = load_data()
        char = all_data["characters"][user_id]
        char["level"] = new_level
        char["xp"] = LEVELS[new_level]["xp"]
        all_data["characters"][user_id] = char
        save_data(all_data)
        
        await message.answer(f"✅ {char['name']}: Уровень {new_level}", reply_markup=get_admin_keyboard())
        await state.clear()
    except:
        await message.answer("❌ Введи 1-80")

@dp.callback_query(F.data.startswith("admin_edit_streak_"))
async def admin_edit_streak(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    user_id = callback.data.replace("admin_edit_streak_", "")
    char = get_character(user_id)
    await state.set_state(AdminStates.editing_streak)
    await state.update_data(editing_user_id=user_id)
    await callback.message.answer(f"🔥 Серия {char['name']} (сейчас {char.get('current_streak', 0)})\n\nВведи число или `отмена`")
    await callback.answer()

@dp.message(AdminStates.editing_streak)
async def process_edit_streak(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    if message.text.lower() == "отмена":
        await state.clear()
        await message.answer("Отменено", reply_markup=get_admin_keyboard())
        return
    
    data = await state.get_data()
    user_id = data["editing_user_id"]
    
    try:
        new_streak = max(0, int(message.text))
        all_data = load_data()
        char = all_data["characters"][user_id]
        char["current_streak"] = new_streak
        if new_streak > char.get("best_streak", 0):
            char["best_streak"] = new_streak
        char["last_training_date"] = str(date.today())
        all_data["characters"][user_id] = char
        save_data(all_data)
        
        await message.answer(f"✅ {char['name']}: Серия {new_streak}", reply_markup=get_admin_keyboard())
        await state.clear()
    except:
        await message.answer("❌ Введи число")

@dp.callback_query(F.data.startswith("admin_reset_penalty_"))
async def admin_reset_penalty(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    user_id = callback.data.replace("admin_reset_penalty_", "")
    
    all_data = load_data()
    char = all_data["characters"][user_id]
    old = char.get("total_penalty_xp", 0)
    char["total_penalty_xp"] = 0
    char["last_penalty_check"] = str(date.today())
    all_data["characters"][user_id] = char
    save_data(all_data)
    
    await callback.answer(f"✅ Штрафы сброшены (было {old} XP)")

@dp.callback_query(F.data.startswith("admin_send_msg_"))
async def admin_send_msg(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    user_id = callback.data.replace("admin_send_msg_", "")
    char = get_character(user_id)
    await state.set_state(AdminStates.sending_message)
    await state.update_data(editing_user_id=user_id)
    await callback.message.answer(f"📨 Сообщение для {char['name']}:\n\nВведи текст или `отмена`")
    await callback.answer()

@dp.message(AdminStates.sending_message)
async def process_send_msg(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    if message.text.lower() == "отмена":
        await state.clear()
        await message.answer("Отменено", reply_markup=get_admin_keyboard())
        return
    
    data = await state.get_data()
    user_id = data["editing_user_id"]
    
    try:
        await bot.send_message(int(user_id), f"📬 **От администратора:**\n\n{message.text}", parse_mode="Markdown")
        await message.answer("✅ Отправлено!", reply_markup=get_admin_keyboard())
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}", reply_markup=get_admin_keyboard())
    await state.clear()

@dp.callback_query(F.data.startswith("admin_ban_"))
async def admin_ban(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    user_id = callback.data.replace("admin_ban_", "")
    
    all_data = load_data()
    if user_id in all_data.get("banned", []):
        all_data["banned"].remove(user_id)
        await callback.answer("✅ Разбанен")
    else:
        all_data["banned"] = all_data.get("banned", []) + [user_id]
        await callback.answer("🚫 Забанен")
    save_data(all_data)

@dp.callback_query(F.data.startswith("admin_delete_"))
async def admin_delete(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    user_id = callback.data.replace("admin_delete_", "")
    char = get_character(user_id)
    await state.set_state(AdminStates.confirming_delete)
    await state.update_data(editing_user_id=user_id)
    await callback.message.answer(f"🗑️ Удалить {char['name']}? Напиши `да` или `отмена`")
    await callback.answer()

@dp.message(AdminStates.confirming_delete)
async def confirm_admin_delete(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    if message.text.lower() == "да":
        data = await state.get_data()
        user_id = data["editing_user_id"]
        char = get_character(user_id)
        delete_character(user_id)
        await message.answer(f"🗑️ {char['name']} удалён", reply_markup=get_admin_keyboard())
    else:
        await message.answer("Отменено", reply_markup=get_admin_keyboard())
    await state.clear()

@dp.message(F.text == "📢 Рассылка всем")
async def broadcast_start(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    data = load_data()
    await state.set_state(AdminStates.broadcast_message)
    await message.answer(f"📢 Рассылка ({len(data['characters'])} чел.)\n\nВведи текст или `отмена`")

@dp.message(AdminStates.broadcast_message)
async def broadcast_send(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    if message.text.lower() == "отмена":
        await state.clear()
        await message.answer("Отменено", reply_markup=get_admin_keyboard())
        return
    
    data = load_data()
    sent, failed = 0, 0
    for user_id in data["characters"]:
        if user_id not in data.get("banned", []):
            try:
                await bot.send_message(int(user_id), f"📢 **Объявление:**\n\n{message.text}", parse_mode="Markdown")
                sent += 1
            except:
                failed += 1
            await asyncio.sleep(0.05)
    
    await message.answer(f"✅ Отправлено: {sent}, ошибок: {failed}", reply_markup=get_admin_keyboard())
    await state.clear()

@dp.message(F.text == "📊 Статистика бота")
async def bot_stats(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    
    data = load_data()
    pending = get_all_pending_requests()
    chars = data["characters"]
    
    total = {"Приседания": 0, "Подтягивания": 0, "Пресс": 0}
    for user_stats in data["stats"].values():
        for day_stats in user_stats.values():
            for ex, val in day_stats.items():
                if ex in total:
                    total[ex] += val
    
    await message.answer(
        f"📊 **Статистика**\n\n"
        f"👥 Пользователей: {len(chars)}\n"
        f"📋 Заявок: {len(pending)}\n"
        f"✨ Всего XP: {sum(c.get('xp', 0) for c in chars.values())}\n\n"
        f"🦵 Приседания: {total['Приседания']}\n"
        f"💪 Подтягивания: {total['Подтягивания']}\n"
        f"🔥 Пресс: {total['Пресс']}",
        parse_mode="Markdown",
        reply_markup=get_admin_keyboard()
    )

# ================= ОСНОВНЫЕ ХЕНДЛЕРЫ =================

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    user_id = str(message.from_user.id)
    
    if is_banned(user_id):
        await message.answer("🚫 Заблокирован!")
        return
    
    save_user_info(message.from_user)
    char = get_character(user_id)
    
    if char:
        penalty = check_and_apply_penalties(user_id)
        msg = f"С возвращением, **{char['name']}**! ⚔️\n"
        if penalty["penalties"] > 0:
            msg += f"⚠️ Штраф: -{penalty['xp_lost']} XP\n"
        char = get_character(user_id)
        if char.get("current_streak", 0) > 0:
            msg += f"🔥 Серия: {char['current_streak']}"
        await message.answer(msg, parse_mode="Markdown", reply_markup=get_main_keyboard())
    else:
        await message.answer("⚔️ **Добро пожаловать!**\n\n🎭 Выбери расу:", parse_mode="Markdown", reply_markup=get_race_keyboard())
        await state.set_state(CharacterCreation.choosing_race)

@dp.message(CharacterCreation.choosing_race)
async def choose_race(message: types.Message, state: FSMContext):
    for rid, r in RACES.items():
        if r["name"] == message.text:
            await state.update_data(race=rid)
            await message.answer(f"✅ {r['name']}\n\n⚔️ Выбери класс:", parse_mode="Markdown", reply_markup=get_class_keyboard())
            await state.set_state(CharacterCreation.choosing_class)
            return
    await message.answer("❌ Выбери из кнопок!")

@dp.message(CharacterCreation.choosing_class)
async def choose_class(message: types.Message, state: FSMContext):
    for cid, c in CLASSES.items():
        if c["name"] == message.text:
            await state.update_data(char_class=cid)
            await message.answer(f"✅ {c['name']}\n\n👤 Выбери пол:", parse_mode="Markdown", reply_markup=get_gender_keyboard())
            await state.set_state(CharacterCreation.choosing_gender)
            return
    await message.answer("❌ Выбери из кнопок!")

@dp.message(CharacterCreation.choosing_gender)
async def choose_gender(message: types.Message, state: FSMContext):
    for gid, g in GENDERS.items():
        if g["name"] == message.text:
            await state.update_data(gender=gid)
            await message.answer("✅\n\n✍️ Придумай имя:", reply_markup=types.ReplyKeyboardRemove())
            await state.set_state(CharacterCreation.choosing_name)
            return
    await message.answer("❌ Выбери из кнопок!")

@dp.message(CharacterCreation.choosing_name)
async def choose_name(message: types.Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 2 or len(name) > 20:
        await message.answer("❌ 2-20 символов!")
        return
    
    data = await state.get_data()
    create_character(str(message.from_user.id), data["race"], data["char_class"], data["gender"], name)
    await state.clear()
    await message.answer(f"🎉 **{name}** создан!\n\n📹 Для записи упражнений нужно видео!", parse_mode="Markdown", reply_markup=get_main_keyboard())

# === Остальные команды ===

@dp.message(F.text == "👤 Мой персонаж")
async def my_character(message: types.Message, state: FSMContext):
    await state.clear()
    char = get_character(str(message.from_user.id))
    if not char:
        await message.answer("❌ /start", reply_markup=get_main_keyboard())
        return
    
    race = RACES.get(char["race"], {})
    cls = CLASSES.get(char["class"], {})
    
    await message.answer(
        f"👤 **{char['name']}**\n\n"
        f"🎭 {race.get('name')} | ⚔️ {cls.get('name')}\n"
        f"⭐ Уровень: {char['level']}/80\n"
        f"✨ XP: {char['xp']}\n"
        f"🔥 Серия: {char.get('current_streak', 0)}",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

@dp.message(F.text == "🏆 Достижения")
async def achievements(message: types.Message, state: FSMContext):
    await state.clear()
    char = get_character(str(message.from_user.id))
    if not char:
        await message.answer("❌ /start", reply_markup=get_main_keyboard())
        return
    
    earned = char.get("achievements", [])
    msg = f"🏆 **Достижения** ({len(earned)}/{len(ACHIEVEMENTS)})\n\n"
    for aid, a in ACHIEVEMENTS.items():
        msg += f"{'✅' if aid in earned else '🔒'} {a['icon']} {a['name']}\n"
    
    await message.answer(msg[:4000], parse_mode="Markdown", reply_markup=get_main_keyboard())

@dp.message(F.text == "📊 Статистика")
async def stats(message: types.Message, state: FSMContext):
    await state.clear()
    user_id = str(message.from_user.id)
    char = get_character(user_id)
    if not char:
        await message.answer("❌ /start", reply_markup=get_main_keyboard())
        return
    
    today = get_today_stats(user_id)
    total, days = get_user_total_stats(user_id)
    
    # Считаем ожидающие заявки
    pending = load_pending()
    user_pending = [r for r in pending.values() if r["user_id"] == user_id and r["status"] == "pending"]
    
    pending_info = ""
    if user_pending:
        pending_info = f"\n\n⏳ На модерации: {len(user_pending)} заявок"
    
    await message.answer(
        f"📊 **{char['name']}**\n\n"
        f"📅 Сегодня: 🦵{today['Приседания']} 💪{today['Подтягивания']} 🔥{today['Пресс']}\n\n"
        f"🏆 Всего ({days} дн.):\n"
        f"🦵 {total['Приседания']} | 💪 {total['Подтягивания']} | 🔥 {total['Пресс']}"
        f"{pending_info}",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

@dp.message(F.text == "👥 Рейтинг")
async def rating(message: types.Message, state: FSMContext):
    await state.clear()
    data = load_data()
    players = sorted(data["characters"].items(), key=lambda x: (x[1]["level"], x[1]["xp"]), reverse=True)[:10]
    
    msg = "👥 **Рейтинг**\n\n"
    for i, (_, c) in enumerate(players):
        medal = {0: "🥇", 1: "🥈", 2: "🥉"}.get(i, f"{i+1}.")
        msg += f"{medal} {c['name']} — Ур.{c['level']}\n"
    
    await message.answer(msg, parse_mode="Markdown", reply_markup=get_main_keyboard())

@dp.message(F.text == "⏰ Напоминания")
async def reminders(message: types.Message, state: FSMContext):
    await state.clear()
    current = get_reminder_time(str(message.from_user.id))
    await message.answer(f"⏰ Сейчас: {current or 'выкл'}", reply_markup=get_reminder_keyboard())

@dp.message(F.text.regexp(r'^🕐 (\d{2}:\d{2})$'))
async def set_time(message: types.Message):
    time = re.match(r'^🕐 (\d{2}:\d{2})$', message.text).group(1)
    set_reminder_time(str(message.from_user.id), time)
    await message.answer(f"✅ {time}", reply_markup=get_main_keyboard())

@dp.message(F.text == "✏️ Своё время")
async def custom_time(message: types.Message, state: FSMContext):
    await state.set_state(ReminderStates.waiting_for_custom_time)
    await message.answer("Введи ЧЧ:ММ:")

@dp.message(ReminderStates.waiting_for_custom_time)
async def process_custom_time(message: types.Message, state: FSMContext):
    match = re.match(r'^(\d{1,2}):(\d{2})$', message.text)
    if match and 0 <= int(match.group(1)) <= 23:
        time = f"{int(match.group(1)):02d}:{match.group(2)}"
        set_reminder_time(str(message.from_user.id), time)
        await state.clear()
        await message.answer(f"✅ {time}", reply_markup=get_main_keyboard())
    else:
        await message.answer("❌ ЧЧ:ММ")

@dp.message(F.text == "🔕 Выключить")
async def disable_reminder(message: types.Message, state: FSMContext):
    await state.clear()
    set_reminder_time(str(message.from_user.id), None)
    await message.answer("🔕", reply_markup=get_main_keyboard())

@dp.message(F.text == "📖 Техника")
async def technique(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("📖 Выбери:", reply_markup=get_technique_keyboard())

@dp.message(F.text == "🔙 Главное меню")
async def back_main(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("🏠", reply_markup=get_main_keyboard())

@dp.message(F.text == "⚙️ Настройки")
async def settings(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("⚙️", reply_markup=get_settings_keyboard())

@dp.message(F.text == "🗑️ Удалить персонажа")
async def ask_delete(message: types.Message):
    char = get_character(str(message.from_user.id))
    if char:
        await message.answer(f"⚠️ Удалить **{char['name']}**?", parse_mode="Markdown", reply_markup=get_confirm_delete_keyboard())

@dp.callback_query(F.data == "confirm_delete")
async def confirm_del(callback: types.CallbackQuery):
    delete_character(str(callback.from_user.id))
    await callback.message.edit_text("🗑️ Удалено. /start")
    await callback.answer()

@dp.callback_query(F.data == "cancel_delete")
async def cancel_del(callback: types.CallbackQuery):
    await callback.message.edit_text("✅ Отменено")
    await callback.answer()

@dp.message(F.text.in_(["🦵 Техника приседаний", "💪 Техника подтягиваний", "🔥 Техника пресса"]))
async def tech_detail(message: types.Message):
    tips = {
        "🦵 Техника приседаний": "🦵 Спина прямая, колени за носки не выходят",
        "💪 Техника подтягиваний": "💪 Без рывков, подбородок выше перекладины",
        "🔥 Техника пресса": "🔥 Поясница прижата, не тяни голову"
    }
    await message.answer(tips[message.text], reply_markup=get_technique_keyboard())

@dp.message()
async def unknown(message: types.Message, state: FSMContext):
    await state.clear()
    if not get_character(str(message.from_user.id)):
        await message.answer("/start")
    else:
        await message.answer("📹 Для записи упражнений отправь:\nПрисед 30, Подтягивание 10, Пресс 50", reply_markup=get_main_keyboard())

# ================= SCHEDULER =================

async def send_reminders():
    now = datetime.now()
    current_time = now.strftime("%H:%M")
    data = load_data()
    
    for user_id, user_info in data.get("users", {}).items():
        if user_info.get("reminder_time") == current_time:
            char = data["characters"].get(user_id)
            if char and not has_trained_today(user_id) and user_id not in data.get("banned", []):
                try:
                    await bot.send_message(int(user_id), f"⚔️ {char['name']}, тренировка!", reply_markup=get_main_keyboard())
                except:
                    pass

async def penalty_warnings():
    data = load_data()
    today = str(date.today())
    
    for user_id, char in data.get("characters", {}).items():
        if not has_trained_today(user_id) and user_id not in data.get("banned", []):
            warnings = char.get("warnings_sent", [])
            if today not in warnings:
                penalty = int(char["xp"] * PENALTY_PERCENT / 100)
                try:
                    await bot.send_message(int(user_id), f"⚠️ **{char['name']}!** Через 2 часа: -{penalty} XP!", parse_mode="Markdown")
                    warnings.append(today)
                    char["warnings_sent"] = warnings[-30:]
                    data["characters"][user_id] = char
                    save_data(data)
                except:
                    pass

async def apply_penalties():
    data = load_data()
    yesterday = str(date.today() - timedelta(days=1))
    
    for user_id, char in data.get("characters", {}).items():
        if yesterday not in data.get("stats", {}).get(user_id, {}):
            penalty = int(char["xp"] * PENALTY_PERCENT / 100)
            if penalty > 0:
                char["xp"] = max(0, char["xp"] - penalty)
                char["level"] = calculate_level(char["xp"])
                char["current_streak"] = 0
                char["total_penalty_xp"] = char.get("total_penalty_xp", 0) + penalty
                data["characters"][user_id] = char
                save_data(data)
                try:
                    await bot.send_message(int(user_id), f"💸 Штраф: -{penalty} XP")
                except:
                    pass

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    
    if not os.path.exists(IMAGES_FOLDER):
        os.makedirs(IMAGES_FOLDER)
    
    scheduler.add_job(send_reminders, 'cron', minute='*')
    scheduler.add_job(penalty_warnings, 'cron', hour=WARNING_HOUR, minute=0)
    scheduler.add_job(apply_penalties, 'cron', hour=0, minute=5)
    scheduler.start()
    
    print(f"🤖 Бот запущен!")
    print(f"👑 Админ: {ADMIN_ID}")
    print(f"📹 Модерация видео: {'ВКЛ' if REQUIRE_VIDEO else 'ВЫКЛ'}")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен")