import json
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from config import ADMIN_IDS

router = Router()
DB_PATH = "database.json"

class CloseShift(StatesGroup):
    waiting_for_photo = State()
    waiting_for_next_worker = State()

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Відкрити магазин"), KeyboardButton(text="Закрити магазин")],
        [KeyboardButton(text="Звіти адміністратора")]
    ],
    resize_keyboard=True
)

def load_db():
    try:
        with open(DB_PATH, "r") as f:
            return json.load(f)
    except:
        return {}

def save_db(data):
    with open(DB_PATH, "w") as f:
        json.dump(data, f, indent=2)

@router.message(F.text == "/start")
async def start(message: types.Message):
    await message.answer("👋 Вітаю! Оберіть дію:", reply_markup=main_menu)

@router.message(F.text.lower() == "відкрити магазин")
async def open_shift(message: types.Message):
    db = load_db()
    today = datetime.now().strftime("%Y-%m-%d")
    uid = str(message.from_user.id)
    db.setdefault(today, {})[uid] = {
        "name": message.from_user.full_name,
        "open_time": datetime.now().strftime("%H:%M"),
        "photo": None,
        "next": None
    }
    save_db(db)
    await message.answer("✅ Відкриття магазину зафіксовано.")

@router.message(F.text.lower() == "закрити магазин")
async def close_shift_start(message: types.Message, state: FSMContext):
    await message.answer("📸 Надішліть фото магазину перед закриттям.")
    await state.set_state(CloseShift.waiting_for_photo)

@router.message(CloseShift.waiting_for_photo, F.photo)
async def close_shift_photo(message: types.Message, state: FSMContext):
    db = load_db()
    today = datetime.now().strftime("%Y-%m-%d")
    uid = str(message.from_user.id)
    if today in db and uid in db[today]:
        db[today][uid]["photo"] = message.photo[-1].file_id
        save_db(db)
        await message.answer("👤 Тепер надішліть ПІБ того, хто працює завтра:")
        await state.set_state(CloseShift.waiting_for_next_worker)
    else:
        await message.answer("❌ Спочатку відкрийте магазин.")
        await state.clear()

@router.message(CloseShift.waiting_for_next_worker)
async def close_shift_name(message: types.Message, state: FSMContext):
    db = load_db()
    today = datetime.now().strftime("%Y-%m-%d")
    uid = str(message.from_user.id)
    if today in db and uid in db[today]:
        if not db[today][uid]["photo"]:
            await message.answer("⚠️ Не зафіксовано фото.")
            return
        db[today][uid]["next"] = message.text
        save_db(db)
        await message.answer("✅ Закриття магазину збережено.")
    await state.clear()

@router.message(F.text.lower() == "звіти адміністратора")
async def admin_panel(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return await message.answer("⛔ Немає доступу.")
    db = load_db()
    if not db:
        return await message.answer("📭 Немає записів.")
    report = ""
    for day, entries in sorted(db.items(), reverse=True):
        report += f"📅 {day}:
"
        for uid, entry in entries.items():
            status = "✅" if entry["photo"] else "❌ Без фото"
            report += (
                f"👤 {entry['name']} о {entry['open_time']} | "
                f"{status} | наступний: {entry.get('next', '—')}
"
            )
    await message.answer(report.strip())
