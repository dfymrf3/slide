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
BACKUP_FOLDER = "backups"
SUGGESTIONS_FILE = "suggestions.json"
BACKUP_KEEP_DAYS = 7  # Сколько дней хранить бэкапы

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
    # ============ ПРИСЕДАНИЯ ============
    "squats_50": {"name": "🦵 Разминка ног", "description": "Сделай 50 приседаний суммарно. Каждый путь начинается с первого шага!", "category": "repetitions", "exercise": "Приседания", "required": 50, "xp_reward": 25, "icon": "🥉"},
    "squats_100": {"name": "🦵 Первые шаги", "description": "100 приседаний суммарно. Ноги начинают привыкать к нагрузке!", "category": "repetitions", "exercise": "Приседания", "required": 100, "xp_reward": 50, "icon": "🥉"},
    "squats_250": {"name": "🦵 Уверенный шаг", "description": "250 приседаний. Ты уже не новичок!", "category": "repetitions", "exercise": "Приседания", "required": 250, "xp_reward": 100, "icon": "🥈"},
    "squats_500": {"name": "🦵 Крепкие ноги", "description": "500 приседаний суммарно. Твои ноги становятся сильнее с каждым днём!", "category": "repetitions", "exercise": "Приседания", "required": 500, "xp_reward": 150, "icon": "🥈"},
    "squats_1000": {"name": "🦵 Стальные ноги", "description": "1000 приседаний! Ты машина для приседаний!", "category": "repetitions", "exercise": "Приседания", "required": 1000, "xp_reward": 300, "icon": "🥇"},
    "squats_2000": {"name": "🦵 Неутомимый", "description": "2000 приседаний. Твои ноги не знают усталости!", "category": "repetitions", "exercise": "Приседания", "required": 2000, "xp_reward": 500, "icon": "🏅"},
    "squats_3000": {"name": "🦵 Титан ног", "description": "3000 приседаний. Легендарная выносливость!", "category": "repetitions", "exercise": "Приседания", "required": 3000, "xp_reward": 750, "icon": "💎"},
    "squats_5000": {"name": "🦵 Бог приседаний", "description": "5000 приседаний! Ты достиг вершины мастерства ног!", "category": "repetitions", "exercise": "Приседания", "required": 5000, "xp_reward": 1000, "icon": "👑"},
    "squats_7500": {"name": "🦵 За пределами", "description": "7500 приседаний. Это уже за гранью понимания!", "category": "repetitions", "exercise": "Приседания", "required": 7500, "xp_reward": 1500, "icon": "🌟"},
    "squats_10000": {"name": "🦵 Легенда приседаний", "description": "10000 приседаний! Абсолютный рекорд!", "category": "repetitions", "exercise": "Приседания", "required": 10000, "xp_reward": 2500, "icon": "⚡"},

    # ============ ПОДТЯГИВАНИЯ ============
    "pullups_25": {"name": "💪 Первый хват", "description": "25 подтягиваний суммарно. Начало пути к сильным рукам!", "category": "repetitions", "exercise": "Подтягивания", "required": 25, "xp_reward": 40, "icon": "🥉"},
    "pullups_50": {"name": "💪 Крепкий хват", "description": "50 подтягиваний. Руки становятся сильнее!", "category": "repetitions", "exercise": "Подтягивания", "required": 50, "xp_reward": 75, "icon": "🥉"},
    "pullups_100": {"name": "💪 Стальные руки", "description": "100 подтягиваний. Серьёзный результат!", "category": "repetitions", "exercise": "Подтягивания", "required": 100, "xp_reward": 150, "icon": "🥈"},
    "pullups_200": {"name": "💪 Сильные руки", "description": "200 подтягиваний суммарно. Мышцы растут!", "category": "repetitions", "exercise": "Подтягивания", "required": 200, "xp_reward": 200, "icon": "🥈"},
    "pullups_350": {"name": "💪 Мощь", "description": "350 подтягиваний. Ты сильнее большинства!", "category": "repetitions", "exercise": "Подтягивания", "required": 350, "xp_reward": 300, "icon": "🥇"},
    "pullups_500": {"name": "💪 Железный хват", "description": "500 подтягиваний! Невероятная сила!", "category": "repetitions", "exercise": "Подтягивания", "required": 500, "xp_reward": 400, "icon": "🥇"},
    "pullups_750": {"name": "💪 Гравитация не указ", "description": "750 подтягиваний. Ты побеждаешь гравитацию!", "category": "repetitions", "exercise": "Подтягивания", "required": 750, "xp_reward": 600, "icon": "🏅"},
    "pullups_1000": {"name": "💪 Тысяча подъёмов", "description": "1000 подтягиваний! Элитный уровень!", "category": "repetitions", "exercise": "Подтягивания", "required": 1000, "xp_reward": 800, "icon": "💎"},
    "pullups_2000": {"name": "💪 Мастер турника", "description": "2000 подтягиваний. Турник — твой лучший друг!", "category": "repetitions", "exercise": "Подтягивания", "required": 2000, "xp_reward": 1200, "icon": "👑"},
    "pullups_3000": {"name": "💪 Бог турника", "description": "3000 подтягиваний! Абсолютное превосходство!", "category": "repetitions", "exercise": "Подтягивания", "required": 3000, "xp_reward": 2000, "icon": "⚡"},
    "pullups_5000": {"name": "💪 Легенда подтягиваний", "description": "5000 подтягиваний! Ты вошёл в историю!", "category": "repetitions", "exercise": "Подтягивания", "required": 5000, "xp_reward": 3000, "icon": "🌟"},

    # ============ ОТЖИМАНИЯ ============
    "pushups_50": {"name": "✊ Первый жим", "description": "50 отжиманий суммарно. Руки начинают крепнуть!", "category": "repetitions", "exercise": "Отжимания", "required": 50, "xp_reward": 30, "icon": "🥉"},
    "pushups_100": {"name": "✊ Сотня отжиманий", "description": "100 отжиманий. Грудь и трицепс растут!", "category": "repetitions", "exercise": "Отжимания", "required": 100, "xp_reward": 60, "icon": "🥉"},
    "pushups_250": {"name": "✊ Уверенный жим", "description": "250 отжиманий. Ты уже силён!", "category": "repetitions", "exercise": "Отжимания", "required": 250, "xp_reward": 120, "icon": "🥈"},
    "pushups_500": {"name": "✊ Стальная грудь", "description": "500 отжиманий. Твоя грудь — броня!", "category": "repetitions", "exercise": "Отжимания", "required": 500, "xp_reward": 200, "icon": "🥈"},
    "pushups_1000": {"name": "✊ Тысяча жимов", "description": "1000 отжиманий! Впечатляющий результат!", "category": "repetitions", "exercise": "Отжимания", "required": 1000, "xp_reward": 350, "icon": "🥇"},
    "pushups_2000": {"name": "✊ Несокрушимый", "description": "2000 отжиманий. Твои руки — оружие!", "category": "repetitions", "exercise": "Отжимания", "required": 2000, "xp_reward": 600, "icon": "🏅"},
    "pushups_3000": {"name": "✊ Титан отжиманий", "description": "3000 отжиманий. Легендарная мощь!", "category": "repetitions", "exercise": "Отжимания", "required": 3000, "xp_reward": 800, "icon": "💎"},
    "pushups_5000": {"name": "✊ Бог отжиманий", "description": "5000 отжиманий! Абсолютная сила верха тела!", "category": "repetitions", "exercise": "Отжимания", "required": 5000, "xp_reward": 1200, "icon": "👑"},
    "pushups_7500": {"name": "✊ За гранью жима", "description": "7500 отжиманий. Это невероятно!", "category": "repetitions", "exercise": "Отжимания", "required": 7500, "xp_reward": 1800, "icon": "🌟"},
    "pushups_10000": {"name": "✊ Легенда отжиманий", "description": "10000 отжиманий! Ты вошёл в историю!", "category": "repetitions", "exercise": "Отжимания", "required": 10000, "xp_reward": 2500, "icon": "⚡"},

    # ============ ПРЕСС ============
    "abs_50": {"name": "🔥 Первое жжение", "description": "50 повторений на пресс. Чувствуешь огонь в мышцах?", "category": "repetitions", "exercise": "Пресс", "required": 50, "xp_reward": 20, "icon": "🥉"},
    "abs_100": {"name": "🔥 Пресс новичка", "description": "100 на пресс. Кор начинает укрепляться!", "category": "repetitions", "exercise": "Пресс", "required": 100, "xp_reward": 30, "icon": "🥉"},
    "abs_250": {"name": "🔥 Крепкий кор", "description": "250 на пресс. Мышцы живота становятся рельефными!", "category": "repetitions", "exercise": "Пресс", "required": 250, "xp_reward": 60, "icon": "🥈"},
    "abs_500": {"name": "🔥 Стальной пресс", "description": "500 на пресс. Твой кор — броня!", "category": "repetitions", "exercise": "Пресс", "required": 500, "xp_reward": 100, "icon": "🥈"},
    "abs_1000": {"name": "🔥 Железный живот", "description": "1000 на пресс! Кубики проступают!", "category": "repetitions", "exercise": "Пресс", "required": 1000, "xp_reward": 200, "icon": "🥇"},
    "abs_2000": {"name": "🔥 Несгибаемый", "description": "2000 на пресс. Стальной корпус!", "category": "repetitions", "exercise": "Пресс", "required": 2000, "xp_reward": 350, "icon": "🥇"},
    "abs_3000": {"name": "🔥 Адамантиевый кор", "description": "3000 на пресс. Прочнее стали!", "category": "repetitions", "exercise": "Пресс", "required": 3000, "xp_reward": 500, "icon": "🏅"},
    "abs_5000": {"name": "🔥 Пресс титана", "description": "5000 на пресс! Невероятная выносливость!", "category": "repetitions", "exercise": "Пресс", "required": 5000, "xp_reward": 800, "icon": "💎"},
    "abs_7500": {"name": "🔥 Бог пресса", "description": "7500 на пресс! Абсолютное совершенство!", "category": "repetitions", "exercise": "Пресс", "required": 7500, "xp_reward": 1200, "icon": "👑"},
    "abs_10000": {"name": "🔥 Легенда пресса", "description": "10000 на пресс! Ты — живая легенда!", "category": "repetitions", "exercise": "Пресс", "required": 10000, "xp_reward": 2000, "icon": "⚡"},

    # ============ ОБЩЕЕ КОЛИЧЕСТВО ============
    "total_100": {"name": "🏋️ Сотня!", "description": "Сделай 100 повторений любых упражнений суммарно", "category": "total", "required": 100, "xp_reward": 30, "icon": "🥉"},
    "total_500": {"name": "🏋️ Полтысячи!", "description": "500 повторений суммарно. Ты набираешь обороты!", "category": "total", "required": 500, "xp_reward": 100, "icon": "🥈"},
    "total_1000": {"name": "🏋️ Тысяча!", "description": "1000 повторений суммарно. Серьёзная цифра!", "category": "total", "required": 1000, "xp_reward": 200, "icon": "🥇"},
    "total_2500": {"name": "🏋️ Машина", "description": "2500 повторений. Ты не останавливаешься!", "category": "total", "required": 2500, "xp_reward": 400, "icon": "🏅"},
    "total_5000": {"name": "🏋️ Неудержимый", "description": "5000 повторений! Ничто тебя не остановит!", "category": "total", "required": 5000, "xp_reward": 700, "icon": "💎"},
    "total_10000": {"name": "🏋️ Десять тысяч", "description": "10000 повторений. Путь в десять тысяч повторений!", "category": "total", "required": 10000, "xp_reward": 1500, "icon": "👑"},
    "total_15000": {"name": "🏋️ Полубог спорта", "description": "15000 повторений. Почти божественная выносливость!", "category": "total", "required": 15000, "xp_reward": 2500, "icon": "🌟"},
    "total_20000": {"name": "🏋️ Бог фитнеса", "description": "20000 повторений! Ты — абсолютный бог!", "category": "total", "required": 20000, "xp_reward": 4000, "icon": "⚡"},
    "total_30000": {"name": "🏋️ За гранью", "description": "30000 повторений. Это невозможно... но ты сделал!", "category": "total", "required": 30000, "xp_reward": 6000, "icon": "🔱"},
    "total_50000": {"name": "🏋️ Бессмертная легенда", "description": "50000 повторений! Твоё имя будет жить вечно!", "category": "total", "required": 50000, "xp_reward": 10000, "icon": "🌌"},

    # ============ ДНИ ТРЕНИРОВОК ============
    "days_1": {"name": "📅 Первый день", "description": "Проведи свою первую тренировку. Путь начинается!", "category": "days", "required": 1, "xp_reward": 10, "icon": "🌱"},
    "days_3": {"name": "📅 Три дня", "description": "3 дня тренировок. Привычка формируется!", "category": "days", "required": 3, "xp_reward": 30, "icon": "🌿"},
    "days_7": {"name": "📅 Неделя силы", "description": "7 дней тренировок. Целая неделя!", "category": "days", "required": 7, "xp_reward": 100, "icon": "🌿"},
    "days_14": {"name": "📅 Две недели", "description": "14 дней тренировок. Дисциплина крепнет!", "category": "days", "required": 14, "xp_reward": 200, "icon": "🌳"},
    "days_30": {"name": "📅 Месяц дисциплины", "description": "30 дней тренировок. Целый месяц!", "category": "days", "required": 30, "xp_reward": 500, "icon": "⭐"},
    "days_60": {"name": "📅 Два месяца", "description": "60 дней тренировок. Это уже образ жизни!", "category": "days", "required": 60, "xp_reward": 1000, "icon": "🌟"},
    "days_90": {"name": "📅 Квартал силы", "description": "90 дней тренировок. 3 месяца дисциплины!", "category": "days", "required": 90, "xp_reward": 1500, "icon": "💫"},
    "days_180": {"name": "📅 Полгода", "description": "180 дней тренировок. Полгода без остановки!", "category": "days", "required": 180, "xp_reward": 3000, "icon": "💎"},
    "days_270": {"name": "📅 Девять месяцев", "description": "270 дней. Скоро год!", "category": "days", "required": 270, "xp_reward": 4500, "icon": "👑"},
    "days_365": {"name": "📅 Год тренировок!", "description": "365 дней тренировок! Целый год! Невероятно!", "category": "days", "required": 365, "xp_reward": 7000, "icon": "🏆"},

    # ============ СЕРИЯ ДНЕЙ ПОДРЯД ============
    "streak_3": {"name": "🔥 Тройка", "description": "3 дня подряд без пропусков. Хорошее начало!", "category": "streak", "required": 3, "xp_reward": 50, "icon": "🔥"},
    "streak_5": {"name": "🔥 Пятидневка", "description": "5 дней подряд. Рабочая неделя тренировок!", "category": "streak", "required": 5, "xp_reward": 100, "icon": "🔥"},
    "streak_7": {"name": "🔥 Неделя огня", "description": "7 дней подряд без единого пропуска!", "category": "streak", "required": 7, "xp_reward": 200, "icon": "🔥"},
    "streak_14": {"name": "🔥 Двухнедельный марафон", "description": "14 дней подряд! Железная воля!", "category": "streak", "required": 14, "xp_reward": 500, "icon": "💥"},
    "streak_21": {"name": "🔥 Привычка", "description": "21 день подряд. Говорят, за 21 день формируется привычка!", "category": "streak", "required": 21, "xp_reward": 800, "icon": "💥"},
    "streak_30": {"name": "🔥 Месяц подряд!", "description": "30 дней подряд! Ты — машина!", "category": "streak", "required": 30, "xp_reward": 1500, "icon": "💎"},
    "streak_45": {"name": "🔥 Полтора месяца", "description": "45 дней подряд. Невероятная дисциплина!", "category": "streak", "required": 45, "xp_reward": 2500, "icon": "💎"},
    "streak_60": {"name": "🔥 Два месяца подряд", "description": "60 дней подряд! Ты непобедим!", "category": "streak", "required": 60, "xp_reward": 4000, "icon": "👑"},
    "streak_90": {"name": "🔥 Квартал без пропусков", "description": "90 дней подряд! 3 месяца! Легендарно!", "category": "streak", "required": 90, "xp_reward": 6000, "icon": "🌟"},
    "streak_180": {"name": "🔥 Полгода подряд!", "description": "180 дней подряд! Это просто невероятно!", "category": "streak", "required": 180, "xp_reward": 10000, "icon": "⚡"},
    "streak_365": {"name": "🔥 ГОД ПОДРЯД!", "description": "365 дней подряд! Ты — живая легенда! Ни одного пропуска за год!", "category": "streak", "required": 365, "xp_reward": 20000, "icon": "🌌"},

    # ============ УРОВНИ ============
    "level_5": {"name": "🎮 Уровень 5", "description": "Достигни 5 уровня. Ты освоился!", "category": "level", "required": 5, "xp_reward": 50, "icon": "🎮"},
    "level_10": {"name": "🎮 Уровень 10", "description": "Достигни 10 уровня. Двузначный!", "category": "level", "required": 10, "xp_reward": 100, "icon": "🎮"},
    "level_15": {"name": "🎮 Уровень 15", "description": "Достигни 15 уровня. Боец!", "category": "level", "required": 15, "xp_reward": 150, "icon": "⭐"},
    "level_20": {"name": "🎮 Уровень 20", "description": "Достигни 20 уровня. Воин!", "category": "level", "required": 20, "xp_reward": 250, "icon": "⭐"},
    "level_25": {"name": "🎮 Уровень 25", "description": "Достигни 25 уровня. Четверть пути!", "category": "level", "required": 25, "xp_reward": 350, "icon": "🌟"},
    "level_30": {"name": "🎮 Уровень 30", "description": "Достигни 30 уровня. Элита!", "category": "level", "required": 30, "xp_reward": 500, "icon": "🌟"},
    "level_35": {"name": "🎮 Уровень 35", "description": "Достигни 35 уровня. Мастер!", "category": "level", "required": 35, "xp_reward": 600, "icon": "💫"},
    "level_40": {"name": "🎮 Уровень 40", "description": "Достигни 40 уровня. Полпути!", "category": "level", "required": 40, "xp_reward": 750, "icon": "💫"},
    "level_45": {"name": "🎮 Уровень 45", "description": "Достигни 45 уровня. Чемпион!", "category": "level", "required": 45, "xp_reward": 900, "icon": "💎"},
    "level_50": {"name": "🎮 Уровень 50", "description": "Достигни 50 уровня. Герой!", "category": "level", "required": 50, "xp_reward": 1000, "icon": "💎"},
    "level_55": {"name": "🎮 Уровень 55", "description": "Достигни 55 уровня. Легенда!", "category": "level", "required": 55, "xp_reward": 1200, "icon": "👑"},
    "level_60": {"name": "🎮 Уровень 60", "description": "Достигни 60 уровня. Мифический!", "category": "level", "required": 60, "xp_reward": 1500, "icon": "👑"},
    "level_65": {"name": "🎮 Уровень 65", "description": "Достигни 65 уровня. Эпический!", "category": "level", "required": 65, "xp_reward": 2000, "icon": "🌟"},
    "level_70": {"name": "🎮 Уровень 70", "description": "Достигни 70 уровня. Бессмертный!", "category": "level", "required": 70, "xp_reward": 2500, "icon": "⚡"},
    "level_75": {"name": "🎮 Уровень 75", "description": "Достигни 75 уровня. Полубог!", "category": "level", "required": 75, "xp_reward": 3000, "icon": "⚡"},
    "level_80": {"name": "🎮 Уровень 80 — МАКСИМУМ!", "description": "Достигни 80 уровня! Абсолютный максимум! Ты — ТИТАН!", "category": "level", "required": 80, "xp_reward": 5000, "icon": "🌌"},

    # ============ ДНЕВНЫЕ РЕКОРДЫ ============
    "daily_squats_50": {"name": "⚡ Полтинник приседов", "description": "Сделай 50 приседаний за один день", "category": "daily", "exercise": "Приседания", "required": 50, "xp_reward": 30, "icon": "⚡"},
    "daily_squats_100": {"name": "⚡ Сотня за день", "description": "100 приседаний за один день!", "category": "daily", "exercise": "Приседания", "required": 100, "xp_reward": 80, "icon": "⚡"},
    "daily_squats_200": {"name": "⚡ Двести приседов", "description": "200 приседаний за один день! Взрыв!", "category": "daily", "exercise": "Приседания", "required": 200, "xp_reward": 200, "icon": "💥"},
    "daily_squats_500": {"name": "⚡ 500 за день!", "description": "500 приседаний за один день! Безумие!", "category": "daily", "exercise": "Приседания", "required": 500, "xp_reward": 500, "icon": "🌋"},
    "daily_pullups_20": {"name": "⚡ 20 подтягиваний за день", "description": "20 подтягиваний за один день", "category": "daily", "exercise": "Подтягивания", "required": 20, "xp_reward": 50, "icon": "⚡"},
    "daily_pullups_50": {"name": "⚡ Полтинник подтягиваний", "description": "50 подтягиваний за день!", "category": "daily", "exercise": "Подтягивания", "required": 50, "xp_reward": 150, "icon": "💥"},
    "daily_pullups_100": {"name": "⚡ Сотня подтягиваний", "description": "100 подтягиваний за один день! Руки из стали!", "category": "daily", "exercise": "Подтягивания", "required": 100, "xp_reward": 400, "icon": "🌋"},
    "daily_pushups_30": {"name": "⚡ 30 отжиманий за день", "description": "30 отжиманий за один день", "category": "daily", "exercise": "Отжимания", "required": 30, "xp_reward": 40, "icon": "⚡"},
    "daily_pushups_50": {"name": "⚡ Полтинник отжиманий", "description": "50 отжиманий за день!", "category": "daily", "exercise": "Отжимания", "required": 50, "xp_reward": 100, "icon": "⚡"},
    "daily_pushups_100": {"name": "⚡ Сотня отжиманий за день", "description": "100 отжиманий за один день! Грудь горит!", "category": "daily", "exercise": "Отжимания", "required": 100, "xp_reward": 250, "icon": "💥"},
    "daily_pushups_200": {"name": "⚡ 200 отжиманий за день!", "description": "200 отжиманий за один день! Безумие!", "category": "daily", "exercise": "Отжимания", "required": 200, "xp_reward": 500, "icon": "🌋"},
    "daily_abs_100": {"name": "⚡ Сотня на пресс", "description": "100 на пресс за один день", "category": "daily", "exercise": "Пресс", "required": 100, "xp_reward": 40, "icon": "⚡"},
    "daily_abs_200": {"name": "⚡ 200 на пресс за день", "description": "200 на пресс за день! Кор в огне!", "category": "daily", "exercise": "Пресс", "required": 200, "xp_reward": 100, "icon": "💥"},
    "daily_abs_500": {"name": "⚡ 500 пресс за день!", "description": "500 на пресс за один день! Невероятно!", "category": "daily", "exercise": "Пресс", "required": 500, "xp_reward": 300, "icon": "🌋"},

    # ============ КОМБО (все упражнения за день) ============
    "combo_1": {"name": "🎯 Первое комбо", "description": "Сделай все 4 упражнения за один день. Полная тренировка!", "category": "combo", "required": 1, "xp_reward": 50, "icon": "🎯"},
    "combo_5": {"name": "🎯 Комбо-боец", "description": "5 дней с полным комбо. Ты любишь разнообразие!", "category": "combo", "required": 5, "xp_reward": 150, "icon": "🎯"},
    "combo_10": {"name": "🎯 Мастер комбо", "description": "10 дней с полным комбо!", "category": "combo", "required": 10, "xp_reward": 300, "icon": "🎯"},
    "combo_25": {"name": "🎯 Комбо-маньяк", "description": "25 дней с полным комбо! Ты всегда делаешь всё!", "category": "combo", "required": 25, "xp_reward": 700, "icon": "💎"},
    "combo_50": {"name": "🎯 Абсолютное комбо", "description": "50 дней с полным комбо! Ни одного упражнения не пропущено!", "category": "combo", "required": 50, "xp_reward": 1500, "icon": "👑"},
    "combo_100": {"name": "🎯 Легенда комбо", "description": "100 дней полного комбо! Ты совершенство!", "category": "combo", "required": 100, "xp_reward": 3000, "icon": "🌌"},
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
    "mage": {"name": "🔮 Маг", "emoji": "🔮", "description": "+15% XP за пресс и отжимания", "multiplier": 1.0, "exercise_bonus": {"Пресс": 0.15, "Отжимания": 0.15}},
    "rogue": {"name": "🗡️ Разбойник", "emoji": "🗡️", "description": "+10% XP", "multiplier": 1.1},
    "paladin": {"name": "🛡️ Паладин", "emoji": "🛡️", "description": "+5% XP, +20% за подтягивания", "multiplier": 1.05, "exercise_bonus": {"Подтягивания": 0.20}}
}

GENDERS = {
    "male": {"name": "♂️ Мужской", "emoji": "♂️"},
    "female": {"name": "♀️ Женский", "emoji": "♀️"}
}

BASE_XP = {"Приседания": 2, "Подтягивания": 5, "Пресс": 1, "Отжимания": 3}

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
class SuggestionStates(StatesGroup):
    waiting_for_suggestion = State()

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

def create_backup():
    """Создать резервную копию всех данных"""
    if not os.path.exists(BACKUP_FOLDER):
        os.makedirs(BACKUP_FOLDER)
    
    today = datetime.now().strftime("%Y-%m-%d_%H-%M")
    
    # Бэкап stats.json
    if os.path.exists(DATA_FILE):
        backup_name = os.path.join(BACKUP_FOLDER, f"stats_backup_{today}.json")
        with open(DATA_FILE, 'r', encoding='utf-8') as src:
            data = src.read()
        with open(backup_name, 'w', encoding='utf-8') as dst:
            dst.write(data)
    
    # Бэкап pending.json
    if os.path.exists(PENDING_FILE):
        backup_name = os.path.join(BACKUP_FOLDER, f"pending_backup_{today}.json")
        with open(PENDING_FILE, 'r', encoding='utf-8') as src:
            data = src.read()
        with open(backup_name, 'w', encoding='utf-8') as dst:
            dst.write(data)
    
    # Удаляем старые бэкапы
    cleanup_old_backups()
    
    return today

def cleanup_old_backups():
    """Удалить бэкапы старше BACKUP_KEEP_DAYS дней"""
    if not os.path.exists(BACKUP_FOLDER):
        return
    
    now = datetime.now()
    removed = 0
    
    for filename in os.listdir(BACKUP_FOLDER):
        filepath = os.path.join(BACKUP_FOLDER, filename)
        if os.path.isfile(filepath):
            file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
            if (now - file_time).days > BACKUP_KEEP_DAYS:
                os.remove(filepath)
                removed += 1
    
    return removed

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
    
    # Общие суммы
    totals = {"Приседания": 0, "Подтягивания": 0, "Отжимания": 0, "Пресс": 0}
    for day_stats in user_stats.values():
        for ex, val in day_stats.items():
            if ex in totals:
                totals[ex] += val
    
    total_all = sum(totals.values())
    days_count = len(user_stats)
    streak = char.get("current_streak", 0)
    best_streak = char.get("best_streak", 0)
    max_streak = max(streak, best_streak)
    combo_count = char.get("combo_count", 0)
    
    # Дневные рекорды (сегодня)
    today = str(date.today())
    today_stats = user_stats.get(today, {"Приседания": 0, "Подтягивания": 0, "Отжимания": 0, "Пресс": 0})
    
    for ach_id, ach in ACHIEVEMENTS.items():
        if ach_id in current_achievements:
            continue
        
        earned = False
        
        if ach["category"] == "repetitions":
            if totals.get(ach["exercise"], 0) >= ach["required"]:
                earned = True
                
        elif ach["category"] == "days":
            if days_count >= ach["required"]:
                earned = True
                
        elif ach["category"] == "streak":
            if max_streak >= ach["required"]:
                earned = True
                
        elif ach["category"] == "level":
            if char["level"] >= ach["required"]:
                earned = True
                
        elif ach["category"] == "total":
            if total_all >= ach["required"]:
                earned = True
                
        elif ach["category"] == "daily":
            if today_stats.get(ach["exercise"], 0) >= ach["required"]:
                earned = True
                
        elif ach["category"] == "combo":
            if combo_count >= ach["required"]:
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
        data["stats"][user_id][today] = {"Приседания": 0, "Подтягивания": 0, "Отжимания": 0, "Пресс": 0}
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
    if all(today_stats.get(ex, 0) > 0 for ex in ["Приседания", "Подтягивания", "Отжимания", "Пресс"]):
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
    return data.get("stats", {}).get(user_id, {}).get(str(date.today()), {"Приседания": 0, "Подтягивания": 0, "Отжимания": 0, "Пресс": 0})

def get_user_total_stats(user_id: str) -> tuple:
    data = load_data()
    totals = {"Приседания": 0, "Подтягивания": 0, "Отжимания": 0, "Пресс": 0}
    days_count = 0
    for day_stats in data.get("stats", {}).get(user_id, {}).values():
        days_count += 1
        for ex, val in day_stats.items():
            if ex in totals:
                totals[ex] += val
    return totals, days_count
def load_suggestions():
    if not os.path.exists(SUGGESTIONS_FILE):
        return []
    with open(SUGGESTIONS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_suggestions(data):
    with open(SUGGESTIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def add_suggestion(user_id: str, username: str, name: str, text: str) -> int:
    suggestions = load_suggestions()
    suggestion = {
        "id": len(suggestions) + 1,
        "user_id": user_id,
        "username": username,
        "name": name,
        "text": text,
        "date": str(datetime.now()),
        "status": "new",  # new, read, done, rejected
        "admin_reply": None
    }
    suggestions.append(suggestion)
    save_suggestions(suggestions)
    return suggestion["id"]
# ================= КЛАВИАТУРЫ =================

def get_main_keyboard():
    kb = [
        [KeyboardButton(text="Присед 30"), KeyboardButton(text="Подтягивание 10")],
        [KeyboardButton(text="Отжимание 20"), KeyboardButton(text="Пресс 50")],
        [KeyboardButton(text="👤 Мой персонаж"), KeyboardButton(text="🏆 Достижения")],
        [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="👥 Рейтинг")],
        [KeyboardButton(text="📖 Техника"), KeyboardButton(text="⏰ Напоминания")],
        [KeyboardButton(text="⚙️ Настройки")]
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
        [KeyboardButton(text="💡 Все предложения")],
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
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="💡 Предложения")],
        [KeyboardButton(text="🗑️ Удалить персонажа")],
        [KeyboardButton(text="🔙 Главное меню")]
    ], resize_keyboard=True)

def get_technique_keyboard():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🦵 Техника приседаний")],
        [KeyboardButton(text="💪 Техника подтягиваний")],
        [KeyboardButton(text="✊ Техника отжиманий")],
        [KeyboardButton(text="🔥 Техника пресса")],
        [KeyboardButton(text="🔙 Главное меню")]
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

@dp.message(F.text.regexp(r'^(присед|подтягивание|отжимание|пресс)\s+(\d+)$', flags=2))
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
    match = re.match(r'(присед|подтягивание|отжимание|пресс)\s+(\d+)', message.text, re.IGNORECASE)
    names = {"присед": "Приседания", "подтягивание": "Подтягивания", "отжимание": "Отжимания", "пресс": "Пресс"}
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
    try:
        if callback.message.caption:
            await callback.message.edit_caption(
                caption=callback.message.caption + f"\n\n✅ **ОДОБРЕНО**\n+{xp} XP",
                parse_mode="Markdown"
            )
        else:
            await callback.message.edit_text(
                text=f"✅ **ОДОБРЕНО**\n+{xp} XP",
                parse_mode="Markdown"
            )
    except Exception:
        await callback.message.answer(f"✅ Одобрено! +{xp} XP")
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
        f"📊 Всего: 🦵{totals['Приседания']} 💪{totals['Подтягивания']} ✊{totals['Отжимания']} 🔥{totals['Пресс']}",
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

@dp.message(Command("backup"))
async def cmd_backup(message: types.Message):
    """Ручной бэкап (только админ)"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет доступа!")
        return
    
    try:
        backup_time = create_backup()
        
        # Считаем файлы в папке бэкапов
        backup_files = os.listdir(BACKUP_FOLDER) if os.path.exists(BACKUP_FOLDER) else []
        total_size = 0
        for f in backup_files:
            filepath = os.path.join(BACKUP_FOLDER, f)
            if os.path.isfile(filepath):
                total_size += os.path.getsize(filepath)
        
        size_kb = total_size / 1024
        size_mb = size_kb / 1024
        
        if size_mb >= 1:
            size_text = f"{size_mb:.1f} МБ"
        else:
            size_text = f"{size_kb:.1f} КБ"
        
        await message.answer(
            f"💾 **Бэкап создан!**\n\n"
            f"📅 Время: {backup_time}\n"
            f"📁 Папка: {BACKUP_FOLDER}/\n"
            f"📄 Файлов: {len(backup_files)}\n"
            f"💿 Размер: {size_text}\n"
            f"🗑️ Хранение: {BACKUP_KEEP_DAYS} дней",
            parse_mode="Markdown"
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

@dp.message(F.text == "💡 Все предложения")
async def admin_suggestions(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    
    suggestions = load_suggestions()
    
    if not suggestions:
        await message.answer("📭 Нет предложений", reply_markup=get_admin_keyboard())
        return
    
    # Статусы
    status_icons = {
        "new": "🆕",
        "read": "👁️",
        "done": "✅",
        "rejected": "❌"
    }
    
    new_count = sum(1 for s in suggestions if s["status"] == "new")
    read_count = sum(1 for s in suggestions if s["status"] == "read")
    done_count = sum(1 for s in suggestions if s["status"] == "done")
    rejected_count = sum(1 for s in suggestions if s["status"] == "rejected")
    
    msg = (
        f"💡 **Все предложения** ({len(suggestions)})\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🆕 Новых: {new_count}\n"
        f"👁️ Прочитано: {read_count}\n"
        f"✅ Сделано: {done_count}\n"
        f"❌ Отклонено: {rejected_count}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    )
    
    # Показываем последние 15 (новые сверху)
    for s in reversed(suggestions[-15:]):
        icon = status_icons.get(s["status"], "❓")
        date_short = s["date"][:10]
        text_short = s["text"][:50] + ("..." if len(s["text"]) > 50 else "")
        msg += f"{icon} #{s['id']} | {s['name']} | {date_short}\n"
        msg += f"   {text_short}\n\n"
    
    await message.answer(msg[:4000], parse_mode="Markdown", reply_markup=get_admin_keyboard())

@dp.message(F.text == "📊 Статистика бота")
async def bot_stats(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    
    data = load_data()
    pending = get_all_pending_requests()
    chars = data["characters"]
    
    total = {"Приседания": 0, "Подтягивания": 0, "Отжимания": 0, "Пресс": 0}
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
        f"✊ Отжимания: {total['Отжимания']}\n"
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
    user_id = str(message.from_user.id)
    char = get_character(user_id)
    if not char:
        await message.answer("❌ /start", reply_markup=get_main_keyboard())
        return
    
    earned = char.get("achievements", [])
    totals, days_count = get_user_total_stats(user_id)
    total_all = sum(totals.values())
    max_streak = max(char.get("current_streak", 0), char.get("best_streak", 0))
    combo_count = char.get("combo_count", 0)
    today_stats = get_today_stats(user_id)
    
    # Группируем по категориям
    categories = {
        "🦵 ПРИСЕДАНИЯ": [],
        "💪 ПОДТЯГИВАНИЯ": [],
        "✊ ОТЖИМАНИЯ": [],
        "🔥 ПРЕСС": [],
        "🏋️ ОБЩЕЕ": [],
        "📅 ДНИ ТРЕНИРОВОК": [],
        "🔥 СЕРИЯ ПОДРЯД": [],
        "🎮 УРОВНИ": [],
        "⚡ ДНЕВНЫЕ РЕКОРДЫ": [],
        "🎯 КОМБО": []
    }
    
    for aid, a in ACHIEVEMENTS.items():
        is_earned = aid in earned
        
        # Считаем прогресс
        if a["category"] == "repetitions":
            current = totals.get(a["exercise"], 0)
        elif a["category"] == "days":
            current = days_count
        elif a["category"] == "streak":
            current = max_streak
        elif a["category"] == "level":
            current = char.get("level", 1)
        elif a["category"] == "total":
            current = total_all
        elif a["category"] == "daily":
            current = today_stats.get(a.get("exercise", ""), 0)
        elif a["category"] == "combo":
            current = combo_count
        else:
            current = 0
        
        req = a["required"]
        
        if is_earned:
            status = "✅"
            progress = ""
        else:
            status = "🔒"
            percent = min(100, int(current / req * 100)) if req > 0 else 0
            progress = f" ({current}/{req})"
        
        # Короткое описание
        if a["category"] == "repetitions":
            short = f"{req} {a['exercise'].lower()}"
        elif a["category"] == "days":
            short = f"{req} дн. тренировок"
        elif a["category"] == "streak":
            short = f"{req} дн. подряд"
        elif a["category"] == "level":
            short = f"Уровень {req}"
        elif a["category"] == "total":
            short = f"{req} повторений"
        elif a["category"] == "daily":
            short = f"{req} {a.get('exercise', '').lower()} за день"
        elif a["category"] == "combo":
            short = f"{req} дн. полного комбо"
        else:
            short = a["description"]
        
        line = f"{status} {a['icon']} {short}{progress} — +{a['xp_reward']} XP"
        
        # Определяем категорию для группировки
        if a["category"] == "repetitions":
            if "Приседания" in a.get("exercise", ""):
                categories["🦵 ПРИСЕДАНИЯ"].append(line)
            elif "Подтягивания" in a.get("exercise", ""):
                categories["💪 ПОДТЯГИВАНИЯ"].append(line)
            elif "Отжимания" in a.get("exercise", ""):
                categories["✊ ОТЖИМАНИЯ"].append(line)
            elif "Пресс" in a.get("exercise", ""):
                categories["🔥 ПРЕСС"].append(line)
        elif a["category"] == "total":
            categories["🏋️ ОБЩЕЕ"].append(line)
        elif a["category"] == "days":
            categories["📅 ДНИ ТРЕНИРОВОК"].append(line)
        elif a["category"] == "streak":
            categories["🔥 СЕРИЯ ПОДРЯД"].append(line)
        elif a["category"] == "level":
            categories["🎮 УРОВНИ"].append(line)
        elif a["category"] == "daily":
            categories["⚡ ДНЕВНЫЕ РЕКОРДЫ"].append(line)
        elif a["category"] == "combo":
            categories["🎯 КОМБО"].append(line)
    
    # Собираем сообщения (разбиваем на части чтобы не превысить лимит)
    messages = []
    current_msg = f"🏆 Достижения ({len(earned)}/{len(ACHIEVEMENTS)})\n"
    
    for cat_name, lines in categories.items():
        if not lines:
            continue
        
        section = f"\n{'─' * 22}\n{cat_name}\n{'─' * 22}\n"
        for line in lines:
            section += f"{line}\n"
        
        # Если сообщение станет слишком длинным — отправляем и начинаем новое
        if len(current_msg) + len(section) > 3900:
            messages.append(current_msg)
            current_msg = ""
        
        current_msg += section
    
    if current_msg:
        messages.append(current_msg)
    
    # Отправляем все части
    for i, msg in enumerate(messages):
        if i == len(messages) - 1:
            await message.answer(msg, reply_markup=get_main_keyboard())
        else:
            await message.answer(msg)





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
        f"📅 Сегодня:\n"
        f"  🦵{today['Приседания']} 💪{today['Подтягивания']} ✊{today['Отжимания']} 🔥{today['Пресс']}\n\n"
        f"🏆 Всего ({days} дн.):\n"
        f"  🦵{total['Приседания']} 💪{total['Подтягивания']} ✊{total['Отжимания']} 🔥{total['Пресс']}"
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

@dp.message(F.text == "💡 Предложения")
async def suggestion_start(message: types.Message, state: FSMContext):
    """Пользователь хочет оставить предложение"""
    user_id = str(message.from_user.id)
    char = get_character(user_id)
    if not char:
        await message.answer("❌ /start", reply_markup=get_main_keyboard())
        return
    
    await state.set_state(SuggestionStates.waiting_for_suggestion)
    await message.answer(
        "💡 **Предложения и пожелания**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Напиши что бы ты хотел улучшить, добавить\n"
        "или изменить в боте.\n\n"
        "Любые идеи приветствуются:\n"
        "  • Новые упражнения\n"
        "  • Новые функции\n"
        "  • Исправление ошибок\n"
        "  • Что угодно!\n\n"
        "✍️ Напиши своё предложение:\n\n"
        "Или нажми «❌ Отменить»",
        parse_mode="Markdown",
        reply_markup=get_cancel_keyboard()
    )


@dp.message(SuggestionStates.waiting_for_suggestion, F.text == "❌ Отменить")
async def suggestion_cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Отменено", reply_markup=get_settings_keyboard())


@dp.message(SuggestionStates.waiting_for_suggestion)
async def suggestion_process(message: types.Message, state: FSMContext):
    """Сохраняем предложение"""
    user_id = str(message.from_user.id)
    char = get_character(user_id)
    user_data = load_data()["users"].get(user_id, {})
    
    if not message.text or len(message.text.strip()) < 3:
        await message.answer("❌ Слишком короткое сообщение. Напиши подробнее!")
        return
    
    if len(message.text) > 2000:
        await message.answer("❌ Слишком длинное! Максимум 2000 символов.")
        return
    
    # Сохраняем
    suggestion_id = add_suggestion(
        user_id=user_id,
        username=user_data.get("username", ""),
        name=char["name"] if char else "Неизвестный",
        text=message.text.strip()
    )
    
    await state.clear()
    
    await message.answer(
        f"✅ **Предложение #{suggestion_id} отправлено!**\n\n"
        f"Спасибо за твой вклад, {char['name']}! 💪\n"
        f"Администратор рассмотрит его в ближайшее время.",
        parse_mode="Markdown",
        reply_markup=get_settings_keyboard()
    )
    
    # Уведомляем админа
    try:
        await bot.send_message(
            ADMIN_ID,
            f"💡 **Новое предложение #{suggestion_id}**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 От: **{char['name']}**\n"
            f"🆔 ID: `{user_id}`\n"
            f"📱 @{user_data.get('username', 'нет')}\n\n"
            f"💬 Текст:\n{message.text.strip()}\n\n"
            f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Прочитано", callback_data=f"sug_read_{suggestion_id}"),
                    InlineKeyboardButton(text="✔️ Сделано", callback_data=f"sug_done_{suggestion_id}")
                ],
                [
                    InlineKeyboardButton(text="💬 Ответить", callback_data=f"sug_reply_{suggestion_id}"),
                    InlineKeyboardButton(text="❌ Отклонить", callback_data=f"sug_reject_{suggestion_id}")
                ]
            ])
        )
    except Exception as e:
        print(f"Ошибка уведомления админа: {e}")

@dp.callback_query(F.data.startswith("sug_read_"))
async def sug_mark_read(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    sug_id = int(callback.data.replace("sug_read_", ""))
    suggestions = load_suggestions()
    for s in suggestions:
        if s["id"] == sug_id:
            s["status"] = "read"
            break
    save_suggestions(suggestions)
    await callback.answer("✅ Отмечено как прочитанное")


@dp.callback_query(F.data.startswith("sug_done_"))
async def sug_mark_done(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    sug_id = int(callback.data.replace("sug_done_", ""))
    suggestions = load_suggestions()
    user_id = None
    for s in suggestions:
        if s["id"] == sug_id:
            s["status"] = "done"
            user_id = s["user_id"]
            break
    save_suggestions(suggestions)
    
    # Уведомляем пользователя
    if user_id:
        try:
            await bot.send_message(
                int(user_id),
                f"✅ **Твоё предложение #{sug_id} реализовано!**\n\n"
                f"Спасибо за идею! Она была добавлена в бота! 🎉",
                parse_mode="Markdown"
            )
        except:
            pass
    
    await callback.answer("✔️ Отмечено как сделано!")


@dp.callback_query(F.data.startswith("sug_reject_"))
async def sug_reject(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    sug_id = int(callback.data.replace("sug_reject_", ""))
    suggestions = load_suggestions()
    user_id = None
    for s in suggestions:
        if s["id"] == sug_id:
            s["status"] = "rejected"
            user_id = s["user_id"]
            break
    save_suggestions(suggestions)
    
    if user_id:
        try:
            await bot.send_message(
                int(user_id),
                f"💡 Предложение #{sug_id} рассмотрено.\n"
                f"К сожалению, сейчас мы не можем его реализовать. "
                f"Но спасибо за идею! 🙏",
                parse_mode="Markdown"
            )
        except:
            pass
    
    await callback.answer("❌ Отклонено")


@dp.callback_query(F.data.startswith("sug_reply_"))
async def sug_reply_start(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    sug_id = int(callback.data.replace("sug_reply_", ""))
    await state.set_state(AdminStates.sending_message)
    
    # Находим user_id по предложению
    suggestions = load_suggestions()
    user_id = None
    for s in suggestions:
        if s["id"] == sug_id:
            user_id = s["user_id"]
            break
    
    if not user_id:
        await callback.answer("Предложение не найдено!")
        return
    
    await state.update_data(editing_user_id=user_id, suggestion_id=sug_id)
    await callback.message.answer(
        f"💬 Напиши ответ на предложение #{sug_id}:\n\nИли напиши `отмена`"
    )
    await callback.answer()

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

@dp.message(F.text == "🦵 Техника приседаний")
async def tech_squats(message: types.Message):
    text = (
        "🦵 ТЕХНИКА ПРИСЕДАНИЙ\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "📌 Исходное положение:\n"
        "  • Ноги на ширине плеч\n"
        "  • Носки слегка развёрнуты наружу\n"
        "  • Руки перед собой или за головой\n"
        "  • Спина прямая, взгляд вперёд\n"
        "\n"
        "⬇️ Движение вниз:\n"
        "  • Начинай движение с отведения таза назад\n"
        "  • Колени двигаются в сторону носков\n"
        "  • Опускайся до параллели бёдер с полом\n"
        "  • Пятки НЕ отрываются от пола\n"
        "  • Спина остаётся прямой\n"
        "\n"
        "⬆️ Движение вверх:\n"
        "  • Отталкивайся пятками от пола\n"
        "  • Выпрямляй ноги плавно\n"
        "  • Колени НЕ своди внутрь\n"
        "  • В верхней точке не переразгибай колени\n"
        "\n"
        "⚠️ Частые ошибки:\n"
        "  ❌ Колени выходят за носки\n"
        "  ❌ Спина округляется\n"
        "  ❌ Пятки отрываются от пола\n"
        "  ❌ Колени сводятся внутрь\n"
        "  ❌ Слишком быстрое выполнение\n"
        "\n"
        "💡 Советы:\n"
        "  ✅ Дыши: вдох вниз, выдох вверх\n"
        "  ✅ Держи кор в напряжении\n"
        "  ✅ Начни с неглубоких приседаний\n"
        "  ✅ Представь что садишься на стул\n"
        "\n"
        "🎯 Какие мышцы работают:\n"
        "  • Квадрицепсы (передняя часть бедра)\n"
        "  • Ягодичные мышцы\n"
        "  • Бицепс бедра (задняя часть)\n"
        "  • Мышцы кора (стабилизация)"
    )
    
    image_path = os.path.join(IMAGES_FOLDER, "squats.jpg")
    if os.path.exists(image_path):
        photo = types.FSInputFile(image_path)
        await message.answer_photo(photo=photo, caption=text[:1024], reply_markup=get_technique_keyboard())
        if len(text) > 1024:
            await message.answer(text[1024:], reply_markup=get_technique_keyboard())
    else:
        await message.answer(text, reply_markup=get_technique_keyboard())


@dp.message(F.text == "💪 Техника подтягиваний")
async def tech_pullups(message: types.Message):
    text = (
        "💪 ТЕХНИКА ПОДТЯГИВАНИЙ\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "📌 Исходное положение:\n"
        "  • Хват чуть шире плеч (прямой хват)\n"
        "  • Руки полностью выпрямлены\n"
        "  • Тело висит свободно\n"
        "  • Ноги можно слегка согнуть и скрестить\n"
        "\n"
        "⬆️ Движение вверх:\n"
        "  • Сведи лопатки вместе\n"
        "  • Тяни себя ГРУДЬЮ к перекладине\n"
        "  • Локти двигаются вниз и назад\n"
        "  • Подбородок должен быть ВЫШЕ перекладины\n"
        "  • Не раскачивайся и не дёргайся\n"
        "\n"
        "⬇️ Движение вниз:\n"
        "  • Опускайся ПЛАВНО и ПОДКОНТРОЛЬНО\n"
        "  • Полностью выпрямляй руки внизу\n"
        "  • Не бросай тело вниз резко\n"
        "  • Негативная фаза = рост мышц!\n"
        "\n"
        "⚠️ Частые ошибки:\n"
        "  ❌ Рывки и раскачивания (киппинг)\n"
        "  ❌ Неполная амплитуда\n"
        "  ❌ Подбородок не доходит до перекладины\n"
        "  ❌ Резкое падение вниз\n"
        "  ❌ Слишком узкий или широкий хват\n"
        "\n"
        "💡 Советы:\n"
        "  ✅ Вдох внизу, выдох на подъёме\n"
        "  ✅ Если не можешь — начни с негативных\n"
        "     (запрыгни наверх и медленно опускайся)\n"
        "  ✅ Используй резинку для помощи\n"
        "  ✅ Австралийские подтягивания для начала\n"
        "\n"
        "📊 Виды хвата:\n"
        "  • Прямой (ладони от себя) — спина + бицепс\n"
        "  • Обратный (ладони к себе) — больше бицепс\n"
        "  • Широкий — акцент на широчайшие\n"
        "  • Узкий — акцент на руки\n"
        "\n"
        "🎯 Какие мышцы работают:\n"
        "  • Широчайшие мышцы спины\n"
        "  • Бицепсы\n"
        "  • Предплечья (сила хвата)\n"
        "  • Задние дельты\n"
        "  • Мышцы кора (стабилизация)"
    )
    
    image_path = os.path.join(IMAGES_FOLDER, "pullups.jpg")
    if os.path.exists(image_path):
        photo = types.FSInputFile(image_path)
        await message.answer_photo(photo=photo, caption=text[:1024], reply_markup=get_technique_keyboard())
        if len(text) > 1024:
            await message.answer(text[1024:], reply_markup=get_technique_keyboard())
    else:
        await message.answer(text, reply_markup=get_technique_keyboard())

@dp.message(F.text == "✊ Техника отжиманий")
async def tech_pushups(message: types.Message):
    text = (
        "✊ ТЕХНИКА ОТЖИМАНИЙ\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "📌 Исходное положение:\n"
        "  • Упор лёжа, руки чуть шире плеч\n"
        "  • Ладони на уровне груди\n"
        "  • Тело — прямая линия от головы до пяток\n"
        "  • Пресс и ягодицы напряжены\n"
        "  • Взгляд слегка вперёд, не в пол\n"
        "\n"
        "⬇️ Движение вниз:\n"
        "  • Сгибай руки, опускаясь ПЛАВНО\n"
        "  • Локти под углом 45° к телу\n"
        "  • Опускайся пока грудь почти коснётся пола\n"
        "  • НЕ прогибай поясницу\n"
        "  • НЕ поднимай таз вверх\n"
        "\n"
        "⬆️ Движение вверх:\n"
        "  • Отталкивайся ладонями от пола\n"
        "  • Выпрямляй руки полностью\n"
        "  • Тело остаётся прямой линией\n"
        "  • Не разгибай локти рывком\n"
        "\n"
        "⚠️ Частые ошибки:\n"
        "  ❌ Провисание поясницы (горб)\n"
        "  ❌ Таз поднимается вверх (домик)\n"
        "  ❌ Локти разводятся в стороны на 90°\n"
        "  ❌ Неполная амплитуда\n"
        "  ❌ Голова задирается вверх или падает\n"
        "\n"
        "💡 Советы:\n"
        "  ✅ Вдох вниз, выдох на подъёме\n"
        "  ✅ Если тяжело — начни с коленей\n"
        "  ✅ Или отжимайся от скамьи/стены\n"
        "  ✅ Держи кор напряжённым всё время\n"
        "  ✅ Лучше 10 правильных чем 30 кривых\n"
        "\n"
        "📊 Виды отжиманий:\n"
        "  • Классические — грудь + трицепс\n"
        "  • Широкие — больше грудь\n"
        "  • Узкие (алмазные) — больше трицепс\n"
        "  • С коленей — облегчённый вариант\n"
        "  • Наклонные (от скамьи) — для начинающих\n"
        "\n"
        "🎯 Какие мышцы работают:\n"
        "  • Грудные мышцы\n"
        "  • Трицепсы\n"
        "  • Передние дельты (плечи)\n"
        "  • Мышцы кора (стабилизаци��)"
    )
    
    image_path = os.path.join(IMAGES_FOLDER, "pushups.jpg")
    if os.path.exists(image_path):
        photo = types.FSInputFile(image_path)
        await message.answer_photo(photo=photo, caption=text[:1024], reply_markup=get_technique_keyboard())
        if len(text) > 1024:
            await message.answer(text[1024:], reply_markup=get_technique_keyboard())
    else:
        await message.answer(text, reply_markup=get_technique_keyboard())

@dp.message(F.text == "🔥 Техника пресса")
async def tech_abs(message: types.Message):
    text = (
        "🔥 ТЕХНИКА УПРАЖНЕНИЙ НА ПРЕСС\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "📌 Скручивания (основное):\n"
        "\n"
        "  Исходное положение:\n"
        "  • Ляг на спину, ноги согнуты в коленях\n"
        "  • Стопы на полу на ширине плеч\n"
        "  • Руки за головой (НЕ тяни шею!)\n"
        "  • Поясница прижата к полу\n"
        "\n"
        "  Выполнение:\n"
        "  • Напряги пресс и оторви лопатки от пола\n"
        "  • Поднимайся за счёт мышц живота\n"
        "  • НЕ тяни себя руками за голову\n"
        "  • Задержись на секунду в верхней точке\n"
        "  • Плавно опустись обратно\n"
        "\n"
        "📌 Подъём ног (нижний пресс):\n"
        "  • Ляг на спину, руки вдоль тела\n"
        "  • Поясница прижата к полу!\n"
        "  • Поднимай прямые ноги до 90°\n"
        "  • Медленно опускай, не касаясь пола\n"
        "\n"
        "📌 Планка (статика):\n"
        "  • Упор на предплечья и носки\n"
        "  • Тело — прямая линия\n"
        "  • Не прогибай и не поднимай таз\n"
        "  • Держи 30-60 секунд = 30-60 повторений\n"
        "\n"
        "⚠️ Частые ошибки:\n"
        "  ❌ Тянешь голову руками\n"
        "  ❌ Поясница отрывается от пола\n"
        "  ❌ Слишком быстрые рывки\n"
        "  ❌ Задержка дыхания\n"
        "  ❌ Полный подъём корпуса (нагрузка на спину)\n"
        "\n"
        "💡 Советы:\n"
        "  ✅ Выдох на подъёме, вдох на опускании\n"
        "  ✅ Чувствуй жжение в мышцах — это хорошо!\n"
        "  ✅ Качество важнее количества\n"
        "  ✅ Чередуй виды упражнений\n"
        "  ✅ Делай медленно и подконтрольно\n"
        "\n"
        "🎯 Какие мышцы работают:\n"
        "  • Прямая мышца живота (кубики)\n"
        "  • Косые мышцы живота\n"
        "  • Поперечная мышца (глубокий кор)\n"
        "  • Мышцы-сгибатели бедра"
    )
    
    image_path = os.path.join(IMAGES_FOLDER, "abs.jpg")
    if os.path.exists(image_path):
        photo = types.FSInputFile(image_path)
        await message.answer_photo(photo=photo, caption=text[:1024], reply_markup=get_technique_keyboard())
        if len(text) > 1024:
            await message.answer(text[1024:], reply_markup=get_technique_keyboard())
    else:
        await message.answer(text, reply_markup=get_technique_keyboard())

@dp.message()
async def unknown(message: types.Message, state: FSMContext):
    await state.clear()
    if not get_character(str(message.from_user.id)):
        await message.answer("/start")
    else:
        await message.answer("📹 Для записи упражнений отправь:\nПрисед 30, Подтягивание 10, Отжимание 20, Пресс 50", reply_markup=get_main_keyboard())

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
async def scheduled_backup():
    """Автоматический бэкап по расписанию"""
    try:
        backup_time = create_backup()
        print(f"✅ Бэкап создан: {backup_time}")
        
        # Уведомляем админа
        data = load_data()
        users_count = len(data.get("characters", {}))
        
        try:
            await bot.send_message(
                ADMIN_ID,
                f"💾 **Автоматический бэкап создан**\n\n"
                f"📅 {backup_time}\n"
                f"👥 Пользователей: {users_count}\n"
                f"📁 Папка: {BACKUP_FOLDER}/",
                parse_mode="Markdown"
            )
        except:
            pass
    except Exception as e:
        print(f"❌ Ошибка бэкапа: {e}")
from aiohttp import web

async def health_check(request):
    """Простой эндпоинт для Render"""
    data = load_data()
    return web.json_response({
        "status": "ok",
        "bot": "running",
        "users": len(data.get("characters", {}))
    })

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    
    if not os.path.exists(IMAGES_FOLDER):
        os.makedirs(IMAGES_FOLDER)
    
    if not os.path.exists(BACKUP_FOLDER):
        os.makedirs(BACKUP_FOLDER)
    
    scheduler.add_job(send_reminders, 'cron', minute='*')
    scheduler.add_job(penalty_warnings, 'cron', hour=WARNING_HOUR, minute=0)
    scheduler.add_job(apply_penalties, 'cron', hour=0, minute=5)
    scheduler.add_job(scheduled_backup, 'cron', hour=3, minute=0)
    scheduler.start()
    
    print(f"🤖 Бот запущен!")
    print(f"👑 Админ: {ADMIN_ID}")
    print(f"📹 Модерация видео: {'ВКЛ' if REQUIRE_VIDEO else 'ВЫКЛ'}")
    
    # Запускаем веб-сервер для Render
    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"🌐 Веб-сервер запущен на порту {port}")
    
    # Запускаем бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен")