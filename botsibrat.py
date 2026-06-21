import asyncio
import json
import uuid
import httpx
import websockets
import urllib.parse
import random
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# ========== CONFIG ==========
API_TOKEN = '8761069085:AAHwoCdvgamqNIU29AFoXwdb3dIdlENFa9k'
AUTH = "Basic LERMVCk3J3FdWmJ8TXgwKzohVDRQM2E5fVJ4J2VYb15bfjJiaExrSUIiTW8kPShMRw=="
COMMON_COOKIE = "m_at=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJfaWQiOiI2Nzg3OGVkNzgxNmUxMDRlMjliMDAxNzMiLCJwaG9uZSI6Iis5OTg5MDc5MTkwMDciLCJyb2xlcyI6WyJCQVNJQyJdLCJmdWxsTmFtZSI6IkFicm9yIC4uLiIsImlhdCI6MTc4MTk4MjQ3NywiZXhwIjoxNzgyNTg3Mjc3fQ.zrRU-T7iy5TnD7f5hrcXtQPWChOmUrD2eYlEexbQhEk;m_rt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJfaWQiOiI2Nzg3OGVkNzgxNmUxMDRlMjliMDAxNzMiLCJwaG9uZSI6Iis5OTg5MDc5MTkwMDciLCJyb2xlcyI6WyJCQVNJQyJdLCJmdWxsTmFtZSI6IkFicm9yIC4uLiIsImlhdCI6MTc4MTk4MjQ3NywiZXhwIjoxODEzNTE4NDc3fQ.JMjykek7Ij-tC7z2P5LleiMAHw6hkyxer1U2JULzz0U;m_did=095cece0e141edcb219c6d88b85879231694e1b5b5f47001e834a755a8b45c6e"

USER_AGENT_V2 = "os:android,os_version:32,sdk:android,sdk_version:2.9.78,device_model:SM-A536E,env:prod,is_prebuilt:false,framework:flutter,framework_version:3.9.2,framework_sdk_version:1.11.0"
IBRAT_API = "https://api.ibrat.dev"

ALLOWED_USERS = [6573103117, 223344556677]

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

active_bots = {}
active_tasks = {}
selected_room = {}   # chat_id -> (room_id, creator_name, creator_avatar)

class BotStates(StatesGroup):
    waiting_for_room_id = State()

def is_allowed(user_id: int):
    return user_id in ALLOWED_USERS

# ========== BARCHA LIVE XONALARNI Olish ==========
async def get_all_live_rooms():
    headers = {
        "cookie": COMMON_COOKIE,
        "authorization": AUTH,
        "user-agent": "Dart/3.9 (dart:io)",
        "accept-language": "uz",
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{IBRAT_API}/v1/voice-chat/rooms?page=1&limit=50&status=LIVE", headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                rooms = []
                for room in data.get("data", []):
                    if room.get("status") == "LIVE":
                        rooms.append({
                            "id": room["_id"],
                            "name": room.get("name", "Nomsiz xona"),
                            "creator": room.get("creatorName", "Noma'lum"),
                            "avatar": room.get("creatorAvatar", "https://robohash.org/default.png")
                        })
                return rooms
            return []
    except Exception as e:
        print(f"Xona olishda xato: {e}")
        return []

# ========== VOICE BOT CLASS (Yangi versiya) ==========
class VoiceBot:
    def __init__(self, user_id, name, avatar, room_id):
        self.user_id = user_id
        self.name = name
        self.avatar = avatar
        self.room_id = room_id
        self.ws = None

    async def send_msg(self, text):
        if self.ws:
            try:
                payload = {
                    "id": str(uuid.uuid4()),
                    "method": "broadcast",
                    "params": {"info": {"message": json.dumps({"messageId": str(uuid.uuid4()), "text": text}), "type": "chat"}, "roles": []},
                    "jsonrpc": "2.0"
                }
                await self.ws.send(json.dumps(payload))
            except:
                self.ws = None

    async def run(self):
        headers = {"cookie": COMMON_COOKIE, "authorization": AUTH, "content-type": "application/json"}
        while True:
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    res = await client.post(f"{IBRAT_API}/v1/voice-chat/rooms/{self.room_id}/join", headers=headers, json={"role": "moderator"})
                    code = res.json()["data"]["code"]
                    res = await client.post("https://auth.100ms.live/v2/token", json={"code": code, "user_id": self.user_id})
                    token = res.json()["token"]
                    encoded_ua = urllib.parse.quote(USER_AGENT_V2, safe="")
                    res = await client.get(f"https://prod-init.100ms.live/init?user_agent_v2={encoded_ua}", headers={"authorization": f"Bearer {token}"})
                    endpoint = res.json()["endpoint"]

                ws_url = f"{endpoint}?peer={uuid.uuid4()}&token={token}&user_agent_v2={encoded_ua}&protocol_version=2.5"

                async with websockets.connect(ws_url) as ws:
                    self.ws = ws
                    metadata_dict = {
                        "userId": self.user_id,
                        "username": self.name,
                        "avatar": self.avatar,
                        "verified": False
                    }
                    await ws.send(json.dumps({
                        "id": str(uuid.uuid4()),
                        "method": "join",
                        "params": {"data": json.dumps(metadata_dict), "name": self.name},
                        "jsonrpc": "2.0"
                    }))
                    async for _ in ws: pass
            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(5)

async def run_multiple_bots(bot_list):
    await asyncio.gather(*[b.run() for b in bot_list], return_exceptions=True)

# ========== HANDLERS ==========
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    if not is_allowed(message.from_user.id):
        return

    await message.answer("🔍 LIVE xonalar yuklanmoqda...")
    rooms = await get_all_live_rooms()

    if not rooms:
        return await message.answer("❌ Hozirda LIVE xona topilmadi.")

    text = "📋 **Hozirgi LIVE Xonalar:**\n\n"
    for room in rooms:
        text += f"**{room['name']}**\n"
        text += f"ID: `{room['id']}`\n"
        text += f"Ochgan: {room['creator']}\n\n"

    text += "Bot yubormoqchi bo'lgan xonaning **ID** sini yuboring:"
    await message.answer(text)
    await state.set_state(BotStates.waiting_for_room_id)


@dp.message(BotStates.waiting_for_room_id)
async def get_room_id(message: types.Message, state: FSMContext):
    if not is_allowed(message.from_user.id):
        return

    room_id = message.text.strip()
    if len(room_id) != 24 or not room_id.isalnum():
        return await message.answer("❌ Noto'g'ri Room ID! Qayta yuboring.")

    # Creator ma'lumotlarini olish uchun yana API chaqiramiz
    rooms = await get_all_live_rooms()
    selected = next((r for r in rooms if r["id"] == room_id), None)

    if not selected:
        return await message.answer("❌ Bu ID bilan LIVE xona topilmadi.")

    selected_room[message.chat.id] = (room_id, selected["creator"], selected["avatar"])

    await message.answer(f"✅ Xona tanlandi!\n\n"
                        f"**{selected['name']}**\n"
                        f"ID: `{room_id}`\n"
                        f"Ochgan: {selected['creator']}\n\n"
                        f"Endi bot sonini yuboring:\n"
                        f"`/bots 500` yoki `/start 500`")
    await state.clear()


@dp.message(Command("bots", "start"))
async def start_bots_cmd(message: types.Message, command: CommandObject):
    if not is_allowed(message.from_user.id):
        return

    chat_id = message.chat.id
    if chat_id not in selected_room:
        return await message.answer("Avval /start buyrug'i bilan xona tanlang!")

    args = command.args
    if not args or not args.isdigit():
        return await message.answer("Iltimos, bot sonini yozing.\nMasalan: `/bots 500`")

    count = min(int(args), 1000)
    room_id, creator_name, creator_avatar = selected_room[chat_id]

    await message.answer(f"🚀 {count} ta bot **{creator_name}** nomidan\n"
                        f"**{room_id}** xonasiga yuborilmoqda...")

    active_bots[chat_id] = []
    for i in range(1, count + 1):
        user_id = str(i)  # 1, 2, 3 ... 
        bot_obj = VoiceBot(user_id, creator_name, creator_avatar, room_id)
        active_bots[chat_id].append(bot_obj)

    task = asyncio.create_task(run_multiple_bots(active_bots[chat_id]))
    active_tasks[chat_id] = task

    await message.answer(f"✅ {count} ta bot muvaffaqiyatli yuborildi!\n"
                        f"Ism: **{creator_name}**\n"
                        f"Xona ID: `{room_id}`\n\n"
                        f"💬 Xabar yuborish: `/sms Matn`\n"
                        f"🛑 To‘xtatish: `/stop`")


@dp.message(Command("sms"))
async def send_sms(message: types.Message, command: CommandObject):
    if not is_allowed(message.from_user.id): return
    chat_id = message.chat.id
    if chat_id not in active_bots or not command.args:
        return await message.answer("Hozirda botlar ishlamayapti!")

    text = command.args
    tasks = [b.send_msg(text) for b in active_bots[chat_id] if b.ws]
    if tasks:
        await asyncio.gather(*tasks)
        await message.answer(f"📨 {len(tasks)} ta bot xabar yubordi.")
    else:
        await message.answer("Botlar hali ulanmagan.")


@dp.message(Command("stop"))
async def stop_bots(message: types.Message):
    if not is_allowed(message.from_user.id): return
    chat_id = message.chat.id
    if chat_id in active_tasks:
        active_tasks[chat_id].cancel()
        del active_tasks[chat_id]
        if chat_id in active_bots:
            del active_bots[chat_id]
        if chat_id in selected_room:
            del selected_room[chat_id]
        await message.answer("🛑 Barcha botlar to‘xtatildi.")
    else:
        await message.answer("Aktiv botlar yo‘q.")


async def main():
    print("Bot ishga tushdi → Yangi rejim (Creator nomi va rasmi bilan)")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
