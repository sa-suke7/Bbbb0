import telethon
from telethon import TelegramClient, events, Button
import re
import asyncio
from datetime import datetime
import json

# قراءة القيم من متغيرات البيئة
API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')
BOT_TOKEN = os.getenv('BOT_TOKEN')
DEVELOPER_ID = int(os.getenv('DEVELOPER_ID'))

# إنشاء عميل Telethon
client = TelegramClient('bot_session', API_ID, API_HASH)


# تحميل أو إنشاء ملف المستخدمين
def load_users():
    try:
        with open('users.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_users(users):
    with open('users.json', 'w') as f:
        json.dump(users, f, ensure_ascii=False, indent=4)

# تخزين المستخدم إذا لم يكن موجودًا بالفعل
def store_user(user_id, user_name, user_username):
    users = load_users()
    if str(user_id) not in users:
        users[str(user_id)] = {
            'name': user_name,
            'username': user_username
        }
        save_users(users)

# وظيفة لحذف الرسائل بعد فترة معينة
async def delete_messages_later(chat_id, message_ids, delay=60):  
    await asyncio.sleep(delay)
    await client.delete_messages(chat_id, message_ids, revoke=True)

# وظيفة لعرض إحصائيات البوت
async def show_bot_stats(event):
    users = load_users()
    user_count = len(users)
    
    stats_message = f"📊 <b>إحصائيات البوت:</b>\n\n👥 <b>عدد المستخدمين:</b> {user_count}\n\n"
    
    for index, (user_id, user_data) in enumerate(users.items(), start=1):
        username = f"({user_data['username']})" if user_data['username'] else "(لا يوجد)"
        stats_message += f"{index}. {user_data['name']} {username} - ID: {user_id}\n"
    
    await event.edit(stats_message, parse_mode='html')

# وظيفة عد تنازلي لتحديث الرسالة كل 10 ثوانٍ
async def countdown(event, info_response, delay, date, views):
    for i in range(delay, 0, -10):
        try:
            await info_response.edit(f"""
            ↯︙تاريخ النشر ↫ ⦗ {date} ⦘
            ↯︙عدد المشاهدات ↫ ⦗ {views} ⦘
            ↯︙سيتم حذف المحتوى بعد ↫ ⦗ {i} ⦘ ثانية
            ↯︙قم بحفظه او اعادة التوجيه
            """, parse_mode='html')
            await asyncio.sleep(10)
        except:
            break  # الخروج إذا حدث خطأ مثل حذف الرسالة بالفعل

@client.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    user = await event.get_sender()
    
    # تخزين المستخدم عند إرسال /start
    store_user(user.id, user.first_name, user.username)

    if user.username:
        user_link = f'<a href="https://t.me/{user.username}">{user.first_name}</a>'
    else:
        user_link = user.first_name

    welcome_message = f"""
    ↯︙اهلاً بك عزيزي ↫ ⦗{user_link}⦘
    ↯︙في بوت حفظ المحتوى المقيد.    
    ↯︙ارسل رابط المنشور فقط.          """
    
    buttons = [
        [Button.url("⦗ WORLED EREN ⦘", "https://t.me/ERENYA0")]
    ]
    
    # إظهار زر "إحصائيات البوت" فقط للمطور
    if user.id == developer_id:
        buttons.append([Button.inline("📊 إحصائيات البوت", b'stats')])
    
    await event.reply(welcome_message, parse_mode='html', buttons=buttons, link_preview=False)

# التعامل مع الضغط على زر إحصائيات البوت
@client.on(events.CallbackQuery)
async def callback_handler(event):
    if event.data == b'stats':
        if event.sender_id == developer_id:
            await show_bot_stats(event)
        else:
            await event.answer("❌ ليس لديك صلاحية الوصول إلى هذه الميزة.", alert=True)

@client.on(events.NewMessage())
async def handler(event):
    if event.message.message == "/start":
        return
    
    links = event.message.message.strip().split()

    for link in links:
        if not re.match(r'https://t.me/([^/]+)/(\d+)', link):
            await event.reply("⚠️ <b>الرابط غير صالح. تأكد من إدخال رابط من قناة تليجرام.</b>", parse_mode='html')
            continue

        match = re.match(r'https://t.me/([^/]+)/(\d+)', link)
        if match:
            channel_username = match.group(1)
            post_id = match.group(2)

            try:
                post = await client.get_messages(channel_username, ids=int(post_id))
                message_text = post.message
                views = post.views or "غير معروف"
                date = post.date.strftime('%Y-%m-%d %H:%M:%S') if post.date else "تاريخ غير معروف"

                if post.media:
                    message_response = await client.send_file(event.chat_id, post.media, caption=message_text)
                else:
                    message_response = await event.reply(message_text)

                info_message = f"""
                ↯︙تاريخ النشر ↫ ⦗ {date} ⦘
                ↯︙عدد المشاهدات ↫ ⦗ {views} ⦘
                ↯︙سيتم حذف المحتوى بعد ↫ ⦗ 1 ⦘ دقيقة
                ↯︙قم بحفظه او اعادة التوجيه
                """
                info_response = await event.reply(info_message, parse_mode='html')

                asyncio.create_task(countdown(event, info_response, delay=60, date=date, views=views))

                await delete_messages_later(event.chat_id, [event.id, message_response.id, info_response.id], delay=60)

            except telethon.errors.rpcerrorlist.ChannelPrivateError:
                await event.reply("❌ <b>لا يمكن الوصول إلى هذه القناة لأنها خاصة.</b>", parse_mode='html')
            except telethon.errors.rpcerrorlist.MessageIdInvalidError:
                await event.reply("❌ <b>معرف المنشور غير صالح أو تم حذفه.</b>", parse_mode='html')
            except Exception as e:
                await event.reply(f"❌ <b>حدث خطأ غير متوقع:</b> {e}", parse_mode='html')

        else:
            await event.reply("⚠️ <b>يرجى إدخال رابط صحيح لمنشور من قناة مقيدة.</b>", parse_mode='html')

# بدء تشغيل البوت
while True:
    try:
        client.start(bot_token=BOT_TOKEN)
        print("Bot started successfully")
        client.run_until_disconnected()
    except Exception as e:
        print(f"Error occurred: {e}")
        continue
