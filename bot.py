from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.tl.functions.account import UpdateProfileRequest
from datetime import datetime
import pytz
import asyncio
import os

# قراءة القيم من المتغيرات البيئية
api_id = os.getenv('API_ID')
api_hash = os.getenv('API_HASH')
phone_number = os.getenv('PHONE_NUMBER')

client = TelegramClient('session_name', api_id, api_hash)

# تحويل الأرقام إلى أرقام مزخرفة بنمط الرياضي
def to_smart_numbers(number_str):
    # تحويل الأرقام من 0-9 إلى Unicode مزخرف
    conversion = str.maketrans('0123456789', '𝟘𝟙𝟚𝟛𝟜𝟝𝟞𝟟𝟠𝟡')
    return number_str.translate(conversion)

async def start_client():
    await client.start(phone_number)
    try:
        # محاولة تسجيل الدخول
        await client.start()
    except SessionPasswordNeededError:
        # طلب كلمة المرور للخطوة الثانية إذا كانت مفعلة
        password = input('Enter your 2FA password: ')
        await client.start(password=password)

async def update_name():
    await start_client()
    me = await client.get_me()

    # الحصول على الوقت الحالي بتوقيت مصر
    egypt_tz = pytz.timezone('Africa/Cairo')
    current_time = datetime.now(egypt_tz).strftime("%H:%M")
    decorated_time = to_smart_numbers(current_time)

    # تحديث الاسم الأول
    new_name = decorated_time  # وضع الوقت المزخرف في الاسم الأول
    await client(UpdateProfileRequest(first_name=new_name))

    print(f"تم تحديث الاسم إلى: {new_name}")

async def main():
    while True:
        await update_name()
        await asyncio.sleep(60)  # إعادة التحديث كل دقيقة

# تشغيل البرنامج
with client:
    client.loop.run_until_complete(main())
