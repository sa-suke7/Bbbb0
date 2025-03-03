import json
import os
import re
import random
import asyncio
import requests
from telethon import TelegramClient, events, Button, functions, types
from telethon import errors
from telethon.tl.functions.messages import SendReactionRequest
from telethon.errors import (
    PeerIdInvalidError,
    ChatWriteForbiddenError,
    FloodWaitError,
    UserIsBlockedError,
    SessionPasswordNeededError,
    PhoneCodeExpiredError,
)
from telethon.tl.functions.contacts import BlockRequest, UnblockRequest, GetContactsRequest, GetBlockedRequest
from telethon.tl.functions.channels import JoinChannelRequest, LeaveChannelRequest
from telethon.tl.functions.photos import UploadProfilePhotoRequest
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.types import InputUser
from telethon.sessions import StringSession
from telethon.utils import get_display_name
from telethon import Button
import http.server
import socketserver
import threading
import os
from telethon.errors import FloodWaitError

api_id = os.getenv('api_id')  # api_id
api_hash = os.getenv('api_hash')  # api_hash
bot_token =  os.getenv("bot_token")  # ـ BOT_TOKEN 

bot = TelegramClient('bot', api_id, api_hash).start(bot_token=bot_token)

user_accounts = {}  # {user_id: {"sessions": [], "users": []}}
allowed_users = []  # المستخدمون المسموح لهم باستخدام البوت
owner_id = int(os.getenv('owner_id'))  # ID المطور

# تحميل البيانات من ملف إذا كان موجودًا
if os.path.exists('sessions.json'):
    with open('sessions.json', 'r') as f:
        user_accounts = json.load(f)
else:
    user_accounts = {}

# وظيفة لحفظ البيانات في ملف
def save_data():
    with open('sessions.json', 'w') as f:
        json.dump(user_accounts, f)

# دالة للتحكم في معدل الطلبات
async def rate_limit():
    await asyncio.sleep(1)  # انتظار ثانية واحدة بين كل طلب

# دالة لإعادة المحاولة عند حدوث FloodWait
async def handle_flood_wait(e, client, target, message):
    print(f"FloodWait: Waiting for {e.seconds} seconds")
    await asyncio.sleep(e.seconds)
    await client.send_message(target, message)

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    sender = await event.get_sender()
    sender_id = str(sender.id)  # تحويل إلى نص لضمان الاتساق
    username = sender.username or "بدون يوزر"
    full_name = f"{sender.first_name} {sender.last_name or ''}".strip()

    # التحقق إذا كان المستخدم مسجلًا بالفعل
    if sender_id not in user_accounts:
        # تسجيل المستخدم الجديد
        user_accounts[sender_id] = {"sessions": [], "users": []}
        save_data()  # حفظ البيانات إلى ملف

        # إرسال رسالة للمطور عند دخول عضو جديد
        total_users = len(user_accounts)  # إجمالي عدد المستخدمين
        message = (
            f"**☑️| انضم عضو جديد**\n"
            f"━━━━━━━━━━━━━\n"
            f"👤 **الاسم:** {full_name}\n"
            f"🔗 **المعرف:** @{username if username != 'بدون يوزر' else 'بدون يوزر'}\n"
            f"🆔 **الآي دي:** `{sender_id}`\n"
            f"━━━━━━━━━━━━━\n"
            f"📊 **إجمالي الأعضاء:** {total_users}\n"
        )
        await bot.send_message(owner_id, message)

    # السماح للمطور باستخدام البوت بدون اشتراك
    if sender_id != str(owner_id) and f"{sender_id}" not in allowed_users and f"@{username}" not in allowed_users:
        await event.respond("🚫 أنت غير مسموح لك باستخدام هذا البوت. لتفعيل البوت تواصل مع مطوري: @PP2P6")
        return

    # إنشاء سجل للمستخدم إذا لم يكن موجودًا
    if sender_id not in user_accounts:
        user_accounts[sender_id] = {"sessions": [], "users": []}
        save_data()

    buttons = [
        [Button.inline('اضافة رقم', 'addnum')],
        [Button.inline('📊 عدد الحسابات', 'numacc'), Button.inline('🗑️ حذف رقم', 'delnum')],
        [Button.inline('⛔️ حظر مستخدم', 'blockuser'), Button.inline('✅ فك حظر مستخدم', 'unblockuser')],
        [Button.inline('📩 إرسال رسالة', 'sendmsg')],
        [Button.inline('📥 جلب الكود', 'get_code'), Button.inline('📞 جلب رقم الهاتف', 'get_phone')],
        [Button.inline('🖼️ إضافة صورة', 'add_profile_photo'), Button.inline('📤 رفع صورة لتلجراف', 'telegraph')],
        [Button.inline('🔄 تغيير اليوزر', 'change_username'), Button.inline('📝 تغيير الاسم', 'change_name')],
        [Button.inline('👁️ مشاهدة منشور', 'view_post'), Button.inline('📽️ مشاهدة استوري', 'view_story')],
        [Button.inline('🚀 انضمام لقناة', 'join'), Button.inline('🚪 غادر قناة', 'leave')],
        [Button.inline('🎉 رشق تفاعلات', 'react')],
        [Button.inline('⚙️ أوامر السوبرات', 'publish_commands'), Button.inline('اوامر بوت دعمكم', 'support_commands')],
        [Button.inline('🟢 تنشيط الحسابات أونلاين', 'activate_online')]  # إضافة الزر الجديد هنا
    ]

    # إضافة أزرار إدارة الاشتراك للمطور فقط
    if sender_id == str(owner_id):
        buttons.append([Button.inline('✅ إضافة اشتراك ', 'add_user'), Button.inline('❌ حذف اشتراك ', 'remove_user')])

    await event.respond("• مرحبا عزيزي المطور في البوت التحكم الخاص بك يمكنك التحكم في البوت عن طريق الازرار ⚜️ ", buttons=buttons)

@bot.on(events.CallbackQuery(pattern='addnum'))
async def add_account(event):
    sender_id = str(event.sender_id)
    username = f"@{event.sender.username}" if event.sender.username else sender_id

    # التحقق إذا كان المستخدم هو المطور أو لديه اشتراك
    if sender_id != str(owner_id) and (sender_id not in allowed_users and username not in allowed_users):
        await event.respond("🚫 أنت غير مسموح لك باستخدام هذا الخيار. لتفعيل البوت تواصل مع المطور.")
        return

    # إنشاء سجل للمستخدم إذا لم يكن موجودًا
    if sender_id not in user_accounts:
        user_accounts[sender_id] = {"sessions": [], "users": []}

    async with bot.conversation(event.sender_id) as conv:
        try:
            # تعريف api_id و api_hash بشكل عام
            api_id = None
            api_hash = None

            # عرض أزرار لاختيار طريقة التسجيل
            await conv.send_message(
                "♢ اختر طريقة التسجيل:",
                buttons=[
                    [Button.inline("رقم الهاتف ", b"phone_login")],
                    [Button.inline("سيشن ", b"session_login")]
                ]
            )

            # انتظار اختيار المستخدم
            response = await conv.wait_event(events.CallbackQuery)
            choice = response.data

            # طلب عدد الحسابات التي يريد المستخدم إضافتها
            await conv.send_message("كم حساب تريد إضافته؟")
            num_accounts_response = await conv.get_response()
            num_accounts = int(num_accounts_response.text)

            for i in range(num_accounts):
                if choice == b"phone_login":
                    # تسجيل الدخول باستخدام رقم الهاتف
                    await conv.send_message(f"- حسنـا قم بـ إرسـال كـود الـ (آيبي ايدي - ᴀᴩɪ_ɪᴅ) الان 🏷\n\n- او اضغط /skip لـ المواصلـه عبـر ايبيات البـوت التلقائيـه 🪁 (الحساب {i+1}/{num_accounts})")
                    response = await conv.get_response()
                    api_id = response.text

                    if api_id.lower() == "/skip":
                        # استخدام الإيبيات الافتراضية إذا تم الضغط على /skip
                        api_id = "29984076"
                        api_hash = "be3aaeef107fa2578ee47271b4aa5645"
                        await conv.send_message("- استخدمنا الإيبيات الافتراضية. ")
                    else:
                        await conv.send_message("- حسنـا قم بـ إرسـال كـود الـ (آيبي هاش - ᴀᴩɪ_ʜᴀsʜ) الان 🏷\n\n- او اضغط /cancel لـ الالغـاء")
                        api_hash = (await conv.get_response()).text

                        # التأكد من أن المستخدم لم يضغط على /cancel بعد إرسال رسالة الآيبي هاش
                        if api_hash.lower() == "/cancel":
                            await conv.send_message("» تم الالغـاء ...\n» ارسـل  /start  لـ البـدء مـن جديـد")
                            return

                    await conv.send_message("- قم بالضغـط ع زر ارسـال جهـة الاتصـال\n- او إرسـال رقـم الهاتـف مع مفتـاح الدولـة\n- مثال : +967777117888")
                    phone_number = (await conv.get_response()).text

                    # إرسال رسالة "جاري إرسال كود الدخول" مباشرة بعد إدخال رقم الهاتف
                    sending_code_msg = await conv.send_message("**جاري إرسال كود الدخول ⎙....**")

                    # بدء عملية تسجيل الدخول
                    client = TelegramClient(StringSession(), api_id, api_hash)
                    await client.connect()
                    if not await client.is_user_authorized():
                        await client.send_code_request(phone_number)

                        # حذف رسالة "جاري إرسال كود الدخول" بعد إرسال الكود
                        await sending_code_msg.delete()

                        # إرسال رسالة تطلب إدخال الكود مع مسافات
                        await conv.send_message("**قم بإرسال الكود مع مسافات بين الأرقام، مثال: 1 2 3 4**")
                        verification_code = (await conv.get_response()).text

                        try:
                            await client.sign_in(phone_number, verification_code.replace(" ", ""))
                        except PhoneCodeExpiredError:
                            await conv.send_message("**عـذراً .. لقـد انتهـى الوقت**\n**ارسـل  /start  لـ البـدء مـن جديـد**")
                            return
                        except SessionPasswordNeededError:
                            await conv.send_message("- قـم بادخـال كلمـة مـرور حسابـك ( التحقق بـ خطوتين ).\n- بــدون مســافـات")
                            password = (await conv.get_response()).text
                            try:
                                await client.sign_in(password=password)
                            except Exception as e:
                                await conv.send_message(f"**خطأ في كلمة المرور: {str(e)}**")
                                return

                    # حفظ الجلسة واسم المستخدم
                    session_str = client.session.save()
                    user = await client.get_me()  # الحصول على معلومات الحساب

                    # التحقق من أن الحساب غير مضاف مسبقًا
                    if any(str(user.id) in account for account in user_accounts[sender_id]["users"]):
                        await conv.send_message(f"❌ الحساب {user.first_name} مضاف مسبقًا.")
                        return

                    user_accounts[sender_id]["sessions"].append(session_str)
                    user_accounts[sender_id]["users"].append(f"{user.id} - {user.first_name}")  # حفظ ID واسم المستخدم

                elif choice == b"session_login":
                    # تسجيل الدخول باستخدام جلسة تيرمكس
                    await conv.send_message(f"» حسنـاً .. عـزيـزي 🙋🏻‍♀\n» قم بـ إرسـال كـود ᴛᴇʟᴇᴛʜᴏɴ أو ᴩʏʀᴏɢʀᴀᴍ الآن � (الحساب {i+1}/{num_accounts})")
                    session_str = (await conv.get_response()).text.strip()

                    # استخدام الإيبيات الافتراضية إذا لم يتم تحديدها
                    if not api_id or not api_hash:
                        api_id = "29984076"
                        api_hash = "be3aaeef107fa2578ee47271b4aa5645"

                    # التحقق من صحة الجلسة
                    try:
                        client = TelegramClient(StringSession(session_str), api_id, api_hash)
                        await client.connect()

                        if not await client.is_user_authorized():
                            await conv.send_message("❌ الجلسة غير صالحة. يرجى إرسال جلسة صحيحة.")
                            return

                        # حفظ الجلسة واسم المستخدم
                        user = await client.get_me()  # الحصول على معلومات الحساب

                        # التحقق من أن الحساب غير مضاف مسبقًا
                        if any(str(user.id) in account for account in user_accounts[sender_id]["users"]):
                            await conv.send_message(f"❌ الحساب {user.first_name} مضاف مسبقًا.")
                            return

                        user_accounts[sender_id]["sessions"].append(session_str)
                        user_accounts[sender_id]["users"].append(f"{user.id} - {user.first_name}")  # حفظ ID واسم المستخدم
                    except Exception as e:
                        await conv.send_message(f"❌ حدث خطأ أثناء التحقق من الجلسة: {str(e)}")
                        return

                else:
                    await conv.send_message("❌ الاختيار غير صحيح.")
                    return

                # تخزين الجلسات في ملف
                save_data()

                await conv.send_message(f"✔️ تم إضافة الحساب بنجاح: {user.first_name} 🎉 (الحساب {i+1}/{num_accounts})")

        except Exception as e:
            await conv.send_message(f"**☆ ❌ حدث خطأ: {str(e)}**")


@bot.on(events.CallbackQuery(pattern='numacc'))
async def show_num_accounts(event):
    sender_id = str(event.sender_id)
    username = f"@{event.sender.username}" if event.sender.username else sender_id

    # التحقق إذا كان المستخدم هو المطور أو لديه اشتراك
    if sender_id != str(owner_id) and (sender_id not in allowed_users and username not in allowed_users):
        await event.respond("🚫 أنت غير مسموح لك باستخدام هذا الخيار. لتفعيل البوت تواصل مع المطور.")
        return

    if sender_id not in user_accounts or not user_accounts[sender_id]["sessions"]:
        await event.respond("🚫 لا توجد حسابات مسجلة لديك.")
    else:
        # عرض الحسابات المسجلة (يتم تحديثها تلقائيًا)
        accounts_list = "\n".join([f"{i+1}. {user}" for i, user in enumerate(user_accounts[sender_id]["users"])])
        await event.respond(f"📋 الحسابات المسجلة:\n{accounts_list}\n📊 إجمالي الحسابات: {len(user_accounts[sender_id]['sessions'])}")


@bot.on(events.CallbackQuery(pattern='delnum'))
async def delete_account(event):
    sender_id = str(event.sender_id)
    username = f"@{event.sender.username}" if event.sender.username else sender_id  

    if sender_id != str(owner_id) and (sender_id not in allowed_users and username not in allowed_users):
        await event.respond("🚫 أنت غير مسموح لك باستخدام هذا الخيار. لتفعيل البوت تواصل مع المطور.")
        return

    # التحقق إذا كان لدى المستخدم حسابات مسجلة
    if sender_id not in user_accounts or not user_accounts[sender_id]["sessions"]:
        await event.respond("🚫 لا توجد حسابات لحذفها.")
        return

    # إنشاء أزرار لكل حساب مع زر "حذف الكل"
    buttons = []
    accounts = user_accounts[sender_id]["users"]
    
    # تجميع الأزرار في صفوف تحتوي على 4 أزرار في كل صف
    for i in range(0, len(accounts), 4):
        row = accounts[i:i+4]  # أخذ 4 حسابات في كل صف
        buttons.append([
            Button.inline(f"حذف الحساب {i+j+1}", f"delete_{i+j}")
            for j in range(len(row))
        ])

    # إضافة زر "حذف جميع الحسابات" في صف منفصل
    buttons.append([Button.inline("حذف جميع الحسابات", b"delete_all")])

    await event.respond("📋 اختر الحساب الذي تريد حذفه:", buttons=buttons)

@bot.on(events.CallbackQuery)
async def handle_delete_choice(event):
    sender_id = str(event.sender_id)
    choice = event.data

    if choice == b"delete_all":
        # حذف جميع الحسابات
        user_accounts[sender_id]["users"].clear()
        user_accounts[sender_id]["sessions"].clear()

        # حفظ البيانات
        save_data()

        await event.respond("✅ تم حذف جميع الحسابات بنجاح.")
    elif choice.startswith(b"delete_"):
        # حذف حساب محدد
        account_num = int(choice.split(b"_")[1])

        # حذف الحساب من القوائم
        deleted_user = user_accounts[sender_id]["users"].pop(account_num)
        user_accounts[sender_id]["sessions"].pop(account_num)

        # حفظ البيانات
        save_data()

        await event.respond(f"✅ تم حذف الحساب ({deleted_user}) بنجاح.")
@bot.on(events.CallbackQuery(pattern='sendmsg'))
async def send_message(event):
    sender_id = str(event.sender_id)
    username = f"@{event.sender.username}" if event.sender.username else sender_id  

    if sender_id != str(owner_id) and (sender_id not in allowed_users and username not in allowed_users):
        await event.respond("🚫 أنت غير مسموح لك باستخدام هذا الخيار. لتفعيل البوت تواصل مع المطور.")
        return

    # التحقق إذا كان لدى المستخدم حسابات مسجلة
    if sender_id not in user_accounts or not user_accounts[sender_id]["sessions"]:
        await event.respond("🚫 لا توجد حسابات مسجلة لديك.")
        return

    async with bot.conversation(event.sender_id) as conv:
        try:
            # طلب اليوزر نيم
            await conv.send_message("♢ ارسل اليوزر نيم للشخص الذي تريد إرسال الرسالة إليه 📬")
            username = (await conv.get_response()).text

            # طلب محتوى الرسالة
            await conv.send_message("♢ ارسل محتوى الرسالة التي تريد إرسالها: ✏️")
            message_content = (await conv.get_response()).text

            # طلب عدد الحسابات التي سيتم استخدامها
            max_accounts = len(user_accounts[sender_id]["sessions"])
            await conv.send_message(f"♢ **كم عدد الحسابات التي تريد استخدامها لإضافة النقاط؟ (الحد الأقصى {max_accounts}):**\n\nيمكنك إدخال نطاق مثل 10-20 لبدء التجميع من الحساب رقم 10 إلى الحساب رقم 20.")
            account_input = (await conv.get_response()).text

            # تحليل النطاق إذا كان المدخل يحتوي على "-"
            if '-' in account_input:
                start, end = map(int, account_input.split('-'))
                account_indices = list(range(start - 1, end))  # تحويل إلى مؤشرات (تبدأ من 0)
            else:
                account_count = int(account_input)
                account_indices = list(range(min(account_count, max_accounts)))

            # تنفيذ عملية الإرسال
            for i in account_indices:
                session_str = user_accounts[sender_id]["sessions"][i]
                client = TelegramClient(StringSession(session_str), api_id, api_hash)
                await client.connect()

                try:
                    await client.send_message(username, message_content)
                    await conv.send_message(f"✅ تم إرسال الرسالة باستخدام الحساب رقم {i + 1}.")
                except FloodWaitError as e:
                    await handle_flood_wait(e, client, username, message_content)
                except Exception as e:
                    await conv.send_message(f"❌ حدث خطأ باستخدام الحساب رقم {i + 1}: {str(e)}")
                finally:
                    await client.disconnect()

            await conv.send_message(f"✅ تم إرسال الرسالة باستخدام {len(account_indices)} حساب(ات).")
        except Exception as e:
            await conv.send_message(f"❌ حدث خطأ أثناء الإرسال: {str(e)}")
                            
@bot.on(events.CallbackQuery(pattern='react'))
async def handle_reactions(event):
    sender_id = str(event.sender_id)
    username = f"@{event.sender.username}" if event.sender.username else sender_id  

    if sender_id != str(owner_id) and (sender_id not in allowed_users and username not in allowed_users):
        await event.respond("🚫 أنت غير مسموح لك باستخدام هذا الخيار. لتفعيل البوت تواصل مع المطور.")
        return

    # التحقق إذا كان لدى المستخدم حسابات مسجلة
    if sender_id not in user_accounts or not user_accounts[sender_id]["sessions"]:
        await event.respond("🚫 لا توجد حسابات مسجلة لديك.")
        return

    async with bot.conversation(event.sender_id) as conv:
        try:
            # طلب الإيموجي من المستخدم
            await conv.send_message("♢ اختر الإيموجي الذي تريد التفاعل به:")
            emoji = (await conv.get_response()).text.strip()

            # إزالة الفارق الزمني (Variant) من الإيموجي
            emoji = emoji.replace("\uFE0F", "")

            # طلب رابط المنشور
            await conv.send_message("♢ أرسل رابط المنشور الذي تريد التفاعل عليه:")
            post_link = (await conv.get_response()).text.strip()

            # استخراج معرف القناة ورقم الرسالة من الرابط
            try:
                if "t.me" in post_link:
                    parts = post_link.split("/")
                    if len(parts) >= 2:
                        channel_username = parts[-2]  # اسم القناة أو المعرف
                        message_id = int(parts[-1])  # رقم الرسالة
                    else:
                        await conv.send_message("❌ الرابط غير صالح. يرجى إرسال رابط صحيح.")
                        return
                else:
                    await conv.send_message("❌ الرابط غير صالح. يرجى إرسال رابط من Telegram.")
                    return
            except ValueError:
                await conv.send_message("❌ الرابط غير صالح. تأكد من أن الرابط يحتوي على رقم رسالة صحيح.")
                return

            # طلب عدد الحسابات التي سيتم استخدامها للتفاعل
            max_accounts = len(user_accounts[sender_id]["sessions"])
            await conv.send_message(f"♢ كم عدد الحسابات التي تريد استخدامها للتفاعل؟ (الحد الأقصى {max_accounts}):\n\nيمكنك إدخال نطاق مثل 10-20 لبدء التفاعل من الحساب رقم 10 إلى الحساب رقم 20.")
            account_input = (await conv.get_response()).text.strip()

            # تحليل النطاق إذا كان المدخل يحتوي على "-"
            if '-' in account_input:
                start, end = map(int, account_input.split('-'))
                account_indices = list(range(start - 1, end))  # تحويل إلى مؤشرات (تبدأ من 0)
            else:
                account_count = int(account_input)
                account_indices = list(range(min(account_count, max_accounts)))

            # تنفيذ عملية التفاعل
            successful_reactions = 0
            for i in account_indices:
                if i >= max_accounts:
                    await conv.send_message(f"⚠️ الحساب رقم {i + 1} غير موجود. تخطي.")
                    continue

                session_str = user_accounts[sender_id]["sessions"][i]
                client = TelegramClient(StringSession(session_str), api_id, api_hash)
                await client.connect()

                try:
                    # الحصول على كيان القناة
                    channel_entity = await client.get_entity(channel_username)

                    # الحصول على الرسالة
                    message = await client.get_messages(channel_entity, ids=message_id)
                    if not message:
                        await conv.send_message(f"❌ الحساب رقم {i + 1}: لا يمكن العثور على الرسالة.")
                        continue

                    # التحقق من التفاعلات المتاحة
                    if message.reactions:
                        available_emojis = [reaction.reaction.emoticon.replace("\uFE0F", "") for reaction in message.reactions.results if hasattr(reaction.reaction, 'emoticon')]
                        if emoji not in available_emojis:
                            await conv.send_message(f"⚠️ الإيموجي {emoji} غير متوفر في المنشور. التفاعلات المتاحة هي: {', '.join(available_emojis) if available_emojis else 'لا توجد تفاعلات متاحة'}.")
                            continue

                    # التحقق مما إذا كان الحساب قد تفاعل سابقًا
                    if message.reactions:
                        reactions_list = message.reactions.results if hasattr(message.reactions, 'results') else []
                        user_reacted = False
                        for reaction in reactions_list:
                            if hasattr(reaction.reaction, 'emoticon') and reaction.reaction.emoticon.replace("\uFE0F", "") == emoji:
                                # التحقق مما إذا كان الحساب الحالي قد تفاعل
                                if hasattr(reaction, 'recent_reactions'):
                                    for recent_reaction in reaction.recent_reactions:
                                        if recent_reaction.peer_id.user_id == client.get_me().id:
                                            user_reacted = True
                                            break
                        if user_reacted:
                            await conv.send_message(f"⚠️ الحساب رقم {i + 1} قد تفاعل بالفعل بالإيموجي {emoji} على هذا المنشور.")
                            continue

                    # التفاعل باستخدام الإيموجي المحدد
                    await client(SendReactionRequest(
                        peer=channel_entity,
                        msg_id=message_id,
                        reaction=[types.ReactionEmoji(emoticon=emoji)]  # إرسال التفاعل كقائمة
                    ))

                    await conv.send_message(f"✅ تم التفاعل باستخدام الحساب رقم {i + 1} بالإيموجي {emoji}.")
                    successful_reactions += 1
                except PeerIdInvalidError:
                    await conv.send_message(f"❌ الحساب رقم {i + 1}: لا يمكن العثور على القناة أو المجموعة.")
                except ChatWriteForbiddenError:
                    await conv.send_message(f"❌ الحساب رقم {i + 1}: لا يمكن التفاعل في هذه القناة (قد تكون القناة خاصة أو محظورة).")
                except Exception as e:
                    await conv.send_message(f"❌ حدث خطأ باستخدام الحساب رقم {i + 1}: {str(e)}")

                await client.disconnect()

            await conv.send_message(f"✅ تم الانتهاء من عملية التفاعل بنجاح. عدد التفاعلات الناجحة: {successful_reactions}.")
        except Exception as e:
            await conv.send_message(f"❌ حدث خطأ أثناء التفاعل: {str(e)}")

@bot.on(events.CallbackQuery(pattern='join'))
async def join_channel(event):
    sender_id = str(event.sender_id)
    username = f"@{event.sender.username}" if event.sender.username else sender_id  

    if sender_id != str(owner_id) and (sender_id not in allowed_users and username not in allowed_users):
        await event.respond("🚫 أنت غير مسموح لك باستخدام هذا الخيار. لتفعيل البوت تواصل مع المطور.")
        return

    # التحقق إذا كان لدى المستخدم حسابات مسجلة
    if sender_id not in user_accounts or not user_accounts[sender_id]["sessions"]:
        await event.respond("🚫 لا توجد حسابات مسجلة لديك.")
        return

    async with bot.conversation(event.sender_id) as conv:
        try:
            # طلب رابط القناة
            await conv.send_message("♢ ارسل رابط القناة أو المجموعة: 🔝")
            link = (await conv.get_response()).text

            # طلب عدد الحسابات أو النطاق
            max_accounts = len(user_accounts[sender_id]["sessions"])
            await conv.send_message(f"♢ ارسل عدد الحسابات التي تريد استخدامها للانضمام (الحد الأقصى {max_accounts}):\n\nيمكنك إدخال نطاق مثل 10-20 لبدء الانضمام من الحساب رقم 10 إلى الحساب رقم 20.")
            account_input = (await conv.get_response()).text.strip()

            # تحليل النطاق إذا كان المدخل يحتوي على "-"
            if '-' in account_input:
                start, end = map(int, account_input.split('-'))
                account_indices = list(range(start - 1, end))  # تحويل إلى مؤشرات (تبدأ من 0)
            else:
                account_count = int(account_input)
                account_indices = list(range(min(account_count, max_accounts)))

            # تنفيذ عملية الانضمام
            success_count = 0
            for i in account_indices:
                if i >= max_accounts:
                    await conv.send_message(f"⚠️ الحساب رقم {i + 1} غير موجود. تخطي.")
                    continue

                session_str = user_accounts[sender_id]["sessions"][i]
                client = TelegramClient(StringSession(session_str), api_id, api_hash)
                await client.connect()

                try:
                    entity = await client.get_entity(link)
                    # التحقق مما إذا كان الحساب منضم بالفعل
                    try:
                        await client(functions.channels.GetParticipantRequest(entity, await client.get_me()))
                        await conv.send_message(f"⚠️ الحساب رقم {i + 1} منضم بالفعل إلى القناة.")
                        continue  # تخطي هذا الحساب
                    except errors.UserNotParticipantError:
                        # إذا لم يكن الحساب منضمًا، يتم الانضمام
                        await client(functions.channels.JoinChannelRequest(entity))
                        await conv.send_message(f"✅ الحساب رقم {i + 1} انضم إلى القناة بنجاح.")
                        success_count += 1
                except Exception as e:
                    await conv.send_message(f"❌ حدث خطأ باستخدام الحساب رقم {i + 1}: {str(e)}")

                await client.disconnect()

            await conv.send_message(f"✅ تم الانضمام إلى {link} باستخدام {success_count} حساب(ات).")
        except Exception as e:
            await conv.send_message(f"❌ حدث خطأ أثناء الانضمام: {str(e)}")


@bot.on(events.CallbackQuery(pattern='leave'))
async def leave_channel(event):
    sender_id = str(event.sender_id)
    username = f"@{event.sender.username}" if event.sender.username else sender_id  

    if sender_id != str(owner_id) and (sender_id not in allowed_users and username not in allowed_users):
        await event.respond("🚫 أنت غير مسموح لك باستخدام هذا الخيار. لتفعيل البوت تواصل مع المطور.")
        return

    # التحقق إذا كان لدى المستخدم حسابات مسجلة
    if sender_id not in user_accounts or not user_accounts[sender_id]["sessions"]:
        await event.respond("🚫 لا توجد حسابات مسجلة لديك.")
        return

    async with bot.conversation(event.sender_id) as conv:
        try:
            # طلب رابط القناة
            await conv.send_message("♢ ارسل رابط القناة أو المجموعة التي تريد المغادرة منها: 🔝")
            link = (await conv.get_response()).text

            # طلب عدد الحسابات أو النطاق
            max_accounts = len(user_accounts[sender_id]["sessions"])
            await conv.send_message(f"♢ كم عدد الحسابات التي تريد المغادرة بها؟ (الحد الأقصى {max_accounts}):\n\nيمكنك إدخال نطاق مثل 10-20 لبدء المغادرة من الحساب رقم 10 إلى الحساب رقم 20.")
            account_input = (await conv.get_response()).text.strip()

            # تحليل النطاق إذا كان المدخل يحتوي على "-"
            if '-' in account_input:
                start, end = map(int, account_input.split('-'))
                account_indices = list(range(start - 1, end))  # تحويل إلى مؤشرات (تبدأ من 0)
            else:
                account_count = int(account_input)
                account_indices = list(range(min(account_count, max_accounts)))

            # تنفيذ عملية المغادرة
            success_count = 0
            for i in account_indices:
                if i >= max_accounts:
                    await conv.send_message(f"⚠️ الحساب رقم {i + 1} غير موجود. تخطي.")
                    continue

                session_str = user_accounts[sender_id]["sessions"][i]
                client = TelegramClient(StringSession(session_str), api_id, api_hash)
                await client.connect()

                try:
                    entity = await client.get_entity(link)
                    # التحقق مما إذا كان الحساب منضمًا
                    try:
                        participant = await client(functions.channels.GetParticipantRequest(entity, await client.get_me()))
                        if not participant:
                            await conv.send_message(f"⚠️ الحساب رقم {i + 1} غير منضم إلى القناة.")
                            continue  # تخطي هذا الحساب
                    except errors.UserNotParticipantError:
                        await conv.send_message(f"⚠️ الحساب رقم {i + 1} غير منضم إلى القناة.")
                        continue  # تخطي هذا الحساب

                    # مغادرة القناة
                    await client(functions.channels.LeaveChannelRequest(entity))
                    await conv.send_message(f"✅ الحساب رقم {i + 1} غادر القناة بنجاح.")
                    success_count += 1
                except Exception as e:
                    await conv.send_message(f"❌ حدث خطأ باستخدام الحساب رقم {i + 1}: {str(e)}")

                await client.disconnect()

            await conv.send_message(f"✅ تم المغادرة بنجاح من {link} باستخدام {success_count} حساب(ات).")
        except Exception as e:
            await conv.send_message(f"❌ حدث خطأ أثناء المغادرة: {str(e)}")
            
@bot.on(events.CallbackQuery(pattern='activate_online'))
async def activate_online(event):
    sender_id = str(event.sender_id)
    username = f"@{event.sender.username}" if event.sender.username else sender_id  

    if sender_id != str(owner_id) and (sender_id not in allowed_users and username not in allowed_users):
        await event.respond("🚫 أنت غير مسموح لك باستخدام هذا الخيار. لتفعيل البوت تواصل مع المطور.")
        return

    # التحقق إذا كان لدى المستخدم حسابات مسجلة
    if sender_id not in user_accounts or not user_accounts[sender_id]["sessions"]:
        await event.respond("🚫 لا توجد حسابات مسجلة لديك.")
        return

    async with bot.conversation(event.sender_id) as conv:
        try:
            # إعلام المستخدم ببدء التنشيط
            await conv.send_message("🟢 جاري تنشيط الحسابات أونلاين...")

            # تنشيط الحسابات أونلاين
            for session_str in user_accounts[sender_id]["sessions"]:
                client = TelegramClient(StringSession(session_str), api_id, api_hash)
                await client.connect()

                # جعل الحساب أونلاين
                await client(functions.account.UpdateStatusRequest(offline=False))

                await client.disconnect()

            await conv.send_message("✅ تم تنشيط الحسابات أونلاين بنجاح.")

            # الانتظار لمدة 10 ثواني
            await asyncio.sleep(10)

            # إعادة الحسابات إلى وضع الأوفلاين
            for session_str in user_accounts[sender_id]["sessions"]:
                client = TelegramClient(StringSession(session_str), api_id, api_hash)
                await client.connect()

                # جعل الحساب أوفلاين
                await client(functions.account.UpdateStatusRequest(offline=True))

                await client.disconnect()

            await conv.send_message("✅ تم إعادة الحسابات إلى وضع الأوفلاين بعد 10 ثواني.")
        except Exception as e:
            await conv.send_message(f"❌ حدث خطأ أثناء تنشيط الحسابات: {str(e)}") 



@bot.on(events.CallbackQuery(pattern='get_code'))
async def get_last_message(event):
    sender_id = str(event.sender_id)
    username = f"@{event.sender.username}" if event.sender.username else sender_id  
    if sender_id != str(owner_id) and (sender_id not in allowed_users and username not in allowed_users):
        await event.respond("🚫 أنت غير مسموح لك باستخدام هذا الخيار. لتفعيل البوت تواصل مع المطور.")
        return
    # التحقق إذا كان لدى المستخدم حسابات مسجلة
    if sender_id not in user_accounts or not user_accounts[sender_id]["sessions"]:
        await event.respond("🚫 لا توجد حسابات مسجلة لديك.")
        return

    async with bot.conversation(event.sender_id) as conv:
        try:
            # عرض الحسابات المسجلة للمستخدم
            accounts_list = "\n".join([f"{i+1}. {user}" for i, user in enumerate(user_accounts[sender_id]["users"])])
            await conv.send_message(f"📋 الحسابات المسجلة لديك:\n{accounts_list}\n\n♢ أرسل رقم الحساب الذي تريد استخدامه (مثال: 1):")

            # انتظار رد المستخدم برقم الحساب
            account_num = (await conv.get_response()).text.strip()

            # التحقق من صحة الإدخال
            try:
                account_num = int(account_num) - 1  # تحويل الرقم إلى مؤشر في القائمة
                if account_num < 0 or account_num >= len(user_accounts[sender_id]["sessions"]):
                    await conv.send_message("❌ رقم الحساب غير صحيح.")
                    return
            except ValueError:
                await conv.send_message("❌ الرقم الذي أدخلته غير صالح. يجب أن يكون رقمًا.")
                return

            # طلب الرابط أو اليوزر نيم الخاص بالمحادثة
            await conv.send_message("♢ أرسل الرابط (مثل tg://openmessage?user_id=777000) أو اليوزر نيم (مثال: @username):")
            chat_input = (await conv.get_response()).text.strip()

            # استخدام الحساب المحدد
            session_str = user_accounts[sender_id]["sessions"][account_num]
            client = TelegramClient(StringSession(session_str), api_id, api_hash)
            await client.connect()

            # تحديد الكيان بناءً على الإدخال (آي دي أو يوزر نيم)
            try:
                if chat_input.startswith("tg://openmessage?user_id="):
                    # استخراج الآي دي من الرابط
                    user_id = chat_input.split('=')[1]
                    try:
                        chat_id = int(user_id)  # تحويل الآي دي إلى عدد صحيح
                        chat_entity = await client.get_entity(chat_id)
                    except ValueError:
                        await conv.send_message("❌ الآي دي غير صالح. تأكد من إرسال رابط صحيح.")
                        return
                elif chat_input.startswith("@"):
                    # استخدام اليوزر نيم
                    username = chat_input.lstrip('@')  # إزالة علامة @ من اليوزر نيم
                    chat_entity = await client.get_entity(username)
                else:
                    await conv.send_message("❌ الإدخال غير صالح. يجب أن يكون رابطًا أو يوزر نيم.")
                    return
            except Exception as e:
                await conv.send_message(f"❌ حدث خطأ أثناء الحصول على المحادثة: {str(e)}")
                return

            # جلب آخر رسالة من المحادثة
            try:
                messages = await client.get_messages(chat_entity, limit=1)
                if messages:
                    last_message = messages[0]
                    await conv.send_message(f"📄 آخر رسالة في المحادثة:\n\n{last_message.text}")
                else:
                    await conv.send_message("❌ لا توجد رسائل في هذه المحادثة.")
            except Exception as e:
                await conv.send_message(f"❌ حدث خطأ أثناء جلب الرسائل: {str(e)}")

            await client.disconnect()

        except Exception as e:
            await conv.send_message(f"❌ حدث خطأ غير متوقع: {str(e)}")

@bot.on(events.CallbackQuery(pattern='blockuser'))
async def block_user(event):
    sender_id = str(event.sender_id)
    username = f"@{event.sender.username}" if event.sender.username else sender_id  
    
    if sender_id != str(owner_id) and (sender_id not in allowed_users and username not in allowed_users):
        await event.respond("🚫 أنت غير مسموح لك باستخدام هذا الخيار. لتفعيل البوت تواصل مع المطور.")
        return
    # التحقق إذا كان لدى المستخدم حسابات مسجلة
    if sender_id not in user_accounts or not user_accounts[sender_id]["sessions"]:
        await event.respond("**🚫 لا توجد حسابات مسجلة لديك.**", parse_mode='md')
        return

    async with bot.conversation(event.sender_id) as conv:
        try:
            # طلب اليوزر نيم
            await conv.send_message("**♢ ارسل اليوزر نيم للشخص الذي تريد حظره (مثل: @username): 🚫**", parse_mode='md')
            username = (await conv.get_response()).text

            # طلب نطاق الحسابات التي سيتم استخدامها للحظر
            max_accounts = len(user_accounts[sender_id]["sessions"])
            await conv.send_message(f"**♢ كم عدد الحسابات التي تريد استخدامها للحظر؟ (الحد الأقصى {max_accounts}): ❗️\n\n> يمكنك إدخال نطاق مثل 10-20 لبدء الحظر من الحساب رقم 10 إلى الحساب رقم 20.**", parse_mode='md')
            account_range = (await conv.get_response()).text

            # تحليل النطاق المدخل
            if '-' in account_range:
                start, end = map(int, account_range.split('-'))
                start = max(1, start)
                end = min(max_accounts, end)
            else:
                start = 1
                end = min(int(account_range), max_accounts)

            # تنفيذ عملية الحظر
            success_count = 0
            for i in range(start - 1, end):
                session_str = user_accounts[sender_id]["sessions"][i]
                client = TelegramClient(StringSession(session_str), api_id, api_hash)
                await client.connect()

                try:
                    user_to_block = await client.get_entity(username)
                    
                    # التحقق مما إذا كان الحساب محظورًا من قِبل المستخدم
                    try:
                        await client.send_message(user_to_block, "test")
                    except UserIsBlockedError:
                        await conv.send_message(f"**⚠️ الحساب {i + 1} محظور من قِبل المستخدم {username}.**", parse_mode='md')
                        continue

                    # الحصول على قائمة المحظورين
                    blocked_users = await client(GetContactsRequest(hash=0))
                    blocked_ids = [user.id for user in blocked_users.users]

                    # التحقق مما إذا كان المستخدم محظورًا بالفعل
                    if user_to_block.id in blocked_ids:
                        await conv.send_message(f"**⚠️ الحساب {i + 1} قام بتخطي حظر {username} لأنه محظور بالفعل.**", parse_mode='md')
                        continue

                    # حظر المستخدم
                    await client(BlockRequest(id=user_to_block.id))
                    success_count += 1
                    await conv.send_message(f"**✅ الحساب {i + 1} قام بحظر {username} بنجاح.**", parse_mode='md')
                except Exception as e:
                    await conv.send_message(f"**❌ الحساب {i + 1} واجه خطأ أثناء حظر {username}: {str(e)}**", parse_mode='md')
                finally:
                    await client.disconnect()

            await conv.send_message(f"**✅ تم حظر المستخدم {username} باستخدام {success_count} حساب(ات) من أصل {end - start + 1}.**", parse_mode='md')
        except Exception as e:
            await conv.send_message(f"**❌ حدث خطأ أثناء الحظر: {str(e)}**", parse_mode='md')

@bot.on(events.CallbackQuery(pattern='unblockuser'))
async def unblock_user(event):
    sender_id = str(event.sender_id)
    username = f"@{event.sender.username}" if event.sender.username else sender_id  
    
    if sender_id != str(owner_id) and (sender_id not in allowed_users and username not in allowed_users):
        await event.respond("🚫 أنت غير مسموح لك باستخدام هذا الخيار. لتفعيل البوت تواصل مع المطور.")
        return
    # التحقق إذا كان لدى المستخدم حسابات مسجلة
    if sender_id not in user_accounts or not user_accounts[sender_id]["sessions"]:
        await event.respond("**🚫 لا توجد حسابات مسجلة لديك.**", parse_mode='md')
        return

    async with bot.conversation(event.sender_id) as conv:
        try:
            # طلب اليوزر نيم
            await conv.send_message("**♢ ارسل اليوزر نيم للشخص الذي تريد فك حظره (مثل: @username): 🔝**", parse_mode='md')
            username = (await conv.get_response()).text

            # طلب نطاق الحسابات التي سيتم استخدامها لفك الحظر
            max_accounts = len(user_accounts[sender_id]["sessions"])
            await conv.send_message(f"**♢ كم عدد الحسابات التي تريد استخدامها لفك الحظر؟ (الحد الأقصى {max_accounts}): ❗️\n\n> يمكنك إدخال نطاق مثل 10-20 لبدء التجميع من الحساب رقم 10 إلى الحساب رقم 20.**", parse_mode='md')
            account_range = (await conv.get_response()).text

            # تحليل النطاق المدخل
            if '-' in account_range:
                start, end = map(int, account_range.split('-'))
                start = max(1, start)
                end = min(max_accounts, end)
            else:
                start = 1
                end = min(int(account_range), max_accounts)

            # تنفيذ عملية فك الحظر
            success_count = 0
            for i in range(start - 1, end):
                session_str = user_accounts[sender_id]["sessions"][i]
                client = TelegramClient(StringSession(session_str), api_id, api_hash)
                await client.connect()

                try:
                    user_to_unblock = await client.get_entity(username)
                    
                    # الحصول على قائمة المحظورين
                    blocked_users = await client(GetBlockedRequest(offset=0, limit=100))
                    blocked_ids = [user.id for user in blocked_users.users]

                    # التحقق مما إذا كان المستخدم محظورًا
                    if user_to_unblock.id not in blocked_ids:
                        await conv.send_message(f"**⚠️ الحساب {i + 1} قام بتخطي فك حظر {username} لأنه غير محظور.**", parse_mode='md')
                        continue

                    # فك حظر المستخدم
                    await client(UnblockRequest(id=user_to_unblock.id))
                    success_count += 1
                    await conv.send_message(f"**✅ الحساب {i + 1} قام بفك حظر {username} بنجاح.**", parse_mode='md')
                except Exception as e:
                    await conv.send_message(f"**❌ الحساب {i + 1} واجه خطأ أثناء فك حظر {username}: {str(e)}**", parse_mode='md')
                finally:
                    await client.disconnect()

            await conv.send_message(f"**✅ تم فك حظر المستخدم {username} باستخدام {success_count} حساب(ات) من أصل {end - start + 1}.**", parse_mode='md')
        except Exception as e:
            await conv.send_message(f"**❌ حدث خطأ أثناء فك الحظر: {str(e)}**", parse_mode='md')
            
@bot.on(events.CallbackQuery(pattern='add_user'))
async def add_user(event):
    sender_id = str(event.sender_id)
    username = f"@{event.sender.username}" if event.sender.username else sender_id  
    # التحقق إذا كان المستخدم هو المطور
    if sender_id != str(owner_id):
        await event.respond("🚫 أنت غير مسموح لك باستخدام هذا البوت. لتفعيل البوت تواصل مع المطور.")
        return

    async with bot.conversation(event.sender_id) as conv:
        try:
            await conv.send_message("♢ ارسل اليوزر نيم أو ID الخاص بالمستخدم لإضافته إلى قائمة المشتركين: 🔝")
            user_id_or_username = (await conv.get_response()).text.strip()

            # إضافة المستخدم إلى قائمة المسموح لهم
            if user_id_or_username not in allowed_users:
                allowed_users.append(user_id_or_username)

                # حفظ البيانات
                save_data()

                # إعلام المستخدم (إذا كان لديه يوزر)
                if user_id_or_username.startswith('@'):
                    try:
                        user = await bot.get_entity(user_id_or_username)
                        await bot.send_message(user.id, "🎉 تم تفعيل اشتراكك في البوت. أهلاً بك!")
                    except Exception as e:
                        await conv.send_message(f"⚠️ تعذر إرسال رسالة للمستخدم: {str(e)}")

                await conv.send_message(f"✅ تم إضافة المستخدم {user_id_or_username} بنجاح.")
            else:
                await conv.send_message(f"⚠️ المستخدم {user_id_or_username} موجود بالفعل في قائمة المشتركين.")
        except Exception as e:
            await conv.send_message(f"❌ حدث خطأ أثناء إضافة المستخدم: {str(e)}")
            
@bot.on(events.CallbackQuery(pattern='remove_user'))
async def remove_user(event):
    sender_id = str(event.sender_id)
    username = f"@{event.sender.username}" if event.sender.username else sender_id  
    # التحقق إذا كان المستخدم هو المطور
    if sender_id != str(owner_id):
        await event.respond("🚫 أنت غير مسموح لك باستخدام هذا البوت.")
        return

    async with bot.conversation(event.sender_id) as conv:
        try:
            await conv.send_message("♢ ارسل اليوزر نيم أو ID الخاص بالمستخدم لإزالته من قائمة المشتركين: ❗️")
            user_id_or_username = (await conv.get_response()).text.strip()

            # حذف المستخدم من القائمة
            if user_id_or_username in allowed_users:
                allowed_users.remove(user_id_or_username)

                # حفظ البيانات
                save_data()

                await conv.send_message(f"✅ تم إزالة المستخدم {user_id_or_username} بنجاح.")
            else:
                await conv.send_message(f"⚠️ المستخدم {user_id_or_username} غير موجود في قائمة المشتركين.")
        except Exception as e:
            await conv.send_message(f"❌ حدث خطأ أثناء إزالة المستخدم: {str(e)}")

@bot.on(events.CallbackQuery(pattern='publish_commands'))
async def publish_commands(event):
    # تعريف الأزرار داخل الدالة
    buttons = [
        [Button.inline('نشر', 'publish'), Button.inline('تكرار', 'repeat')],  # نشر بجانب تكرار
        [Button.inline('إيقاف نشر', 'stop_publish'), Button.inline('إيقاف تكرار', 'stop_repeat')],  # إيقاف نشر بجانب إيقاف تكرار
        [Button.inline('عودة', 'back_to_main')]  # زر العودة في الصف الأخير
    ]

    # تعديل الرسالة وإظهار الأزرار
    await event.edit("• أختر من اوامر السوبرات الآتية", buttons=buttons)


@bot.on(events.CallbackQuery(pattern='back_to_main'))
async def back_to_main(event):
    # تعريف الأزرار مع إضافة زر "أوامر دعمكم"
    buttons = [
        [Button.inline('اضافة رقم', 'addnum')],
        [Button.inline('📊 عدد الحسابات', 'numacc'), Button.inline('🗑️ حذف رقم', 'delnum')],
        [Button.inline('⛔️ حظر مستخدم', 'blockuser'), Button.inline('✅ فك حظر مستخدم', 'unblockuser')],
        [Button.inline('📩 إرسال رسالة', 'sendmsg')],
        [Button.inline('📥 جلب الكود', 'get_code'), Button.inline('📞 جلب رقم الهاتف', 'get_phone')],
        [Button.inline('🖼️ إضافة صورة', 'add_profile_photo'), Button.inline('📤 رفع صورة لتلجراف', 'telegraph')],
        [Button.inline('🔄 تغيير اليوزر', 'change_username'), Button.inline('📝 تغيير الاسم', 'change_name')],
        [Button.inline('👁️ مشاهدة منشور', 'view_post'), Button.inline('📽️ مشاهدة استوري', 'view_story')],
        [Button.inline('🚀 انضمام لقناة', 'join'), Button.inline('🚪 غادر قناة', 'leave')],
        [Button.inline('🎉 رشق تفاعلات', 'react')],
        [Button.inline('⚙️ أوامر السوبرات', 'publish_commands'), Button.inline('اوامر بوت دعمكم', 'support_commands')],
        [Button.inline('🟢 تنشيط الحسابات أونلاين', 'activate_online')]  # إضافة الزر الجديد هنا
    ]

    # إضافة أزرار إدارة الاشتراك للمطور فقط
    if str(event.sender_id) == str(owner_id):
        buttons.append([Button.inline('✅ إضافة اشتراك ', 'add_user'), Button.inline('❌ حذف اشتراك ', 'remove_user')])

    # تعديل الرسالة وإظهار الأزرار
    await event.edit("• مرحبا عزيزي المطور في البوت التحكم الخاص بك يمكنك التحكم في البوت عن طريق الازرار ⚜️ ", buttons=buttons)

    # إضافة أزرار إدارة الاشتراك للمطور فقط
    if str(event.sender_id) == str(owner_id):
        buttons.append([Button.inline('✅ إضافة اشتراك ', 'add_user'), Button.inline('❌ حذف اشتراك ', 'remove_user')])

                                              

# متغير للتحكم في عملية النشر
is_publishing = False

@bot.on(events.CallbackQuery(pattern='stop_publish'))
async def stop_publishing(event):
    global is_publishing
    is_publishing = False  # إيقاف عملية النشر
    await event.respond("✅ تم إيقاف النشر بنجاح.")

@bot.on(events.CallbackQuery(pattern='^publish$'))
async def publish(event):
    global is_publishing
    sender_id = str(event.sender_id)
    username = f"@{event.sender.username}" if event.sender.username else sender_id  
    
    if sender_id != str(owner_id) and (sender_id not in allowed_users and username not in allowed_users):
        await event.respond("🚫 أنت غير مسموح لك باستخدام هذا الخيار. لتفعيل البوت تواصل مع المطور.")
        return

    # التحقق إذا كان لدى المستخدم حسابات مسجلة
    if sender_id not in user_accounts or not user_accounts[sender_id]["sessions"]:
        await event.respond("🚫 لا توجد حسابات مسجلة لديك.")
        return

    async with bot.conversation(event.sender_id) as conv:
        try:
            # طلب رابط المجموعة
            await conv.send_message("📎 أرسل رابط المجموعة التي تريد النشر فيها:")
            group_link = (await conv.get_response()).text

            # طلب محتوى الرسالة
            await conv.send_message("📄 أرسل محتوى الرسالة التي تريد نشرها:")
            message_content = (await conv.get_response()).text

            # طلب الفاصل الزمني بين الرسائل
            await conv.send_message("⏱ أرسل الفاصل الزمني (بالثواني) بين كل رسالة:")
            interval = int((await conv.get_response()).text)

            # طلب عدد الحسابات أو النطاق
            max_accounts = len(user_accounts[sender_id]["sessions"])
            await conv.send_message(f"🔢 أرسل عدد الحسابات التي تريد استخدامها للنشر (الحد الأقصى {max_accounts}):\n\nيمكنك إدخال نطاق مثل 10-20 لبدء النشر من الحساب رقم 10 إلى الحساب رقم 20.")
            account_input = (await conv.get_response()).text.strip()

            # تحليل النطاق إذا كان المدخل يحتوي على "-"
            if '-' in account_input:
                start, end = map(int, account_input.split('-'))
                account_indices = list(range(start - 1, end))  # تحويل إلى مؤشرات (تبدأ من 0)
            else:
                account_count = int(account_input)
                account_indices = list(range(min(account_count, max_accounts)))

            # بدء عملية النشر
            is_publishing = True
            while is_publishing:  # سيستمر النشر طالما أن is_publishing = True
                for i in account_indices:
                    if i >= max_accounts:
                        await conv.send_message(f"⚠️ الحساب رقم {i + 1} غير موجود. تخطي.")
                        continue

                    if not is_publishing:  # التحقق من إيقاف النشر
                        break

                    session_str = user_accounts[sender_id]["sessions"][i]
                    client = TelegramClient(StringSession(session_str), api_id, api_hash)
                    await client.connect()

                    try:
                        # التحقق من انضمام الحساب للمجموعة
                        group_entity = await client.get_entity(group_link)
                        await client.send_message(group_entity, message_content)
                        await conv.send_message(f"✅ تم إرسال الرسالة باستخدام الحساب رقم {i + 1}.")
                    except Exception as e:
                        if "not a participant" in str(e):
                            await conv.send_message(f"⚠️ الحساب رقم {i + 1} غير مشترك بالمجموعة. استخدم زر '🚀 انضم' لإضافة الحساب.")
                        else:
                            await conv.send_message(f"❌ حدث خطأ باستخدام الحساب رقم {i + 1}: {str(e)}")

                    await client.disconnect()

                    # انتظار الفاصل الزمني بين الرسائل
                    await asyncio.sleep(interval)

            await conv.send_message("✅ تم إيقاف النشر بنجاح.")
        except Exception as e:
            await conv.send_message(f"❌ حدث خطأ أثناء النشر: {str(e)}")

@bot.on(events.CallbackQuery(pattern='telegraph'))
async def telegraph(event):
    sender_id = str(event.sender_id)
    username = f"@{event.sender.username}" if event.sender.username else sender_id

    # التحقق إذا كان المستخدم هو المطور أو لديه اشتراك
    if sender_id != str(owner_id) and (sender_id not in allowed_users and username not in allowed_users):
        await event.respond("🚫 أنت غير مسموح لك باستخدام هذا الخيار. لتفعيل البوت تواصل مع المطور.")
        return

    async with bot.conversation(event.sender_id) as conv:
        try:
            # طلب الصورة من المستخدم
            await conv.send_message("📤 أرسل الصورة التي تريد رفعها:")
            photo = await conv.get_response()

            # التحقق من أن المستخدم أرسل صورة
            if not photo.media or not hasattr(photo.media, 'photo'):
                await conv.send_message("🚫 لم تقم بإرسال صورة. الرجاء إرسال صورة.")
                return

            # تنزيل الصورة
            try:
                photo_path = await photo.download_media()
                await conv.send_message(f"✅ تم تنزيل الصورة بنجاح: {photo_path}")
            except Exception as e:
                await conv.send_message(f"❌ حدث خطأ أثناء تنزيل الصورة: {str(e)}")
                return

            # التحقق من حجم الصورة
            try:
                file_size = os.path.getsize(photo_path)  # حجم الملف بالبايت
                if file_size > 10 * 1024 * 1024:  # مثال: 10 ميجابايت كحد أقصى
                    await conv.send_message("🚫 حجم الصورة كبير جدًا. الحد الأقصى هو 10 ميجابايت.")
                    os.remove(photo_path)
                    return
            except Exception as e:
                await conv.send_message(f"❌ حدث خطأ أثناء التحقق من حجم الصورة: {str(e)}")
                return

            # رفع الصورة إلى catbox.moe
            try:
                with open(photo_path, 'rb') as file:
                    response = requests.post(
                        'https://catbox.moe/user/api.php',
                        data={"reqtype": "fileupload"},  # إضافة المعلمة المطلوبة
                        files={"fileToUpload": file}
                    )
                    response.raise_for_status()  # رفع استثناء إذا كانت حالة الرد غير ناجحة
            except requests.exceptions.RequestException as e:
                await conv.send_message(f"❌ حدث خطأ أثناء رفع الصورة: {str(e)}")
                os.remove(photo_path)
                return

            # التحقق من نجاح الرفع
            if response.status_code == 200:
                image_url = response.text
                await conv.send_message(f"✅ تم رفع الصورة بنجاح! الرابط:\n{image_url}")
            else:
                await conv.send_message(f"❌ حدث خطأ أثناء رفع الصورة. حالة الرد: {response.status_code}")

            # حذف الصورة المحملة مؤقتًا
            try:
                os.remove(photo_path)
                await conv.send_message("✅ تم حذف الصورة المؤقتة بنجاح.")
            except Exception as e:
                await conv.send_message(f"❌ حدث خطأ أثناء حذف الصورة المؤقتة: {str(e)}")

        except Exception as e:
            await conv.send_message(f"❌ حدث خطأ غير متوقع: {str(e)}")

@bot.on(events.CallbackQuery(pattern='repeat'))
async def repeat_message(event):
    sender_id = str(event.sender_id)
    username = f"@{event.sender.username}" if event.sender.username else sender_id  
    
    if sender_id != str(owner_id) and (sender_id not in allowed_users and username not in allowed_users):
        await event.respond("🚫 أنت غير مسموح لك باستخدام هذا الخيار. لتفعيل البوت تواصل مع المطور.")
        return

    # التحقق إذا كان لدى المستخدم حسابات مسجلة
    if sender_id not in user_accounts or not user_accounts[sender_id]["sessions"]:
        await event.respond("🚫 لا توجد حسابات مسجلة لديك.")
        return

    async with bot.conversation(event.sender_id) as conv:
        try:
            # طلب رابط المجموعة
            await conv.send_message("♢ أرسل رابط المجموعة التي تريد التكرار فيها:")
            group_link = (await conv.get_response()).text

            # طلب محتوى الرسالة
            await conv.send_message("♢ أرسل محتوى الرسالة التي تريد تكرارها:")
            message_content = (await conv.get_response()).text

            # طلب الفاصل الزمني بين الرسائل
            await conv.send_message("♢ أرسل الفاصل الزمني (بالثواني) بين كل رسالة:")
            interval = int((await conv.get_response()).text)

            # طلب عدد المرات التي تريد تكرار الرسالة
            await conv.send_message("♢ كم مرة تريد تكرار الرسالة؟")
            repeat_count = int((await conv.get_response()).text)

            # طلب عدد الحسابات أو النطاق
            max_accounts = len(user_accounts[sender_id]["sessions"])
            await conv.send_message(f"♢ كم عدد الحسابات التي تريد استخدامها للتكرار؟ (الحد الأقصى {max_accounts}):\n\nيمكنك إدخال نطاق مثل 10-20 لبدء التكرار من الحساب رقم 10 إلى الحساب رقم 20.")
            account_input = (await conv.get_response()).text.strip()

            # تحليل النطاق إذا كان المدخل يحتوي على "-"
            if '-' in account_input:
                start, end = map(int, account_input.split('-'))
                account_indices = list(range(start - 1, end))  # تحويل إلى مؤشرات (تبدأ من 0)
            else:
                account_count = int(account_input)
                account_indices = list(range(min(account_count, max_accounts)))

            # التحقق من انضمام الحسابات إلى المجموعة
            non_joined_accounts = []
            for i in account_indices:
                if i >= max_accounts:
                    await conv.send_message(f"⚠️ الحساب رقم {i + 1} غير موجود. تخطي.")
                    continue

                session_str = user_accounts[sender_id]["sessions"][i]
                client = TelegramClient(StringSession(session_str), api_id, api_hash)
                await client.connect()

                try:
                    # الحصول على كيان المجموعة
                    group_entity = await client.get_entity(group_link)

                    # التحقق من انضمام الحساب إلى المجموعة
                    try:
                        await client(functions.channels.GetParticipantRequest(
                            channel=group_entity,
                            participant=await client.get_me()
                        ))
                    except Exception as e:
                        non_joined_accounts.append(i + 1)
                        await conv.send_message(f"⚠️ الحساب رقم {i + 1} غير مشترك في المجموعة. الرجاء الانضمام أولاً.")
                        continue

                except Exception as e:
                    await conv.send_message(f"❌ حدث خطأ أثناء التحقق من انضمام الحساب رقم {i + 1}: {str(e)}")
                    continue

                await client.disconnect()

            # إذا كانت هناك حسابات غير منضمة، إعلام المستخدم
            if non_joined_accounts:
                await conv.send_message(f"🚫 الحسابات التالية غير منضمة إلى المجموعة: {', '.join(map(str, non_joined_accounts))}. الرجاء الانضمام أولاً.")
                return

            # تنفيذ عملية التكرار
            for _ in range(repeat_count):
                for i in account_indices:
                    if i >= max_accounts:
                        await conv.send_message(f"⚠️ الحساب رقم {i + 1} غير موجود. تخطي.")
                        continue

                    session_str = user_accounts[sender_id]["sessions"][i]
                    client = TelegramClient(StringSession(session_str), api_id, api_hash)
                    await client.connect()

                    try:
                        # الحصول على كيان المجموعة
                        group_entity = await client.get_entity(group_link)

                        # إرسال الرسالة
                        await client.send_message(group_entity, message_content)
                        await conv.send_message(f"✅ تم إرسال الرسالة باستخدام الحساب رقم {i + 1}.")
                    except Exception as e:
                        await conv.send_message(f"❌ حدث خطأ باستخدام الحساب رقم {i + 1}: {str(e)}")

                    await client.disconnect()

                    # انتظار الفاصل الزمني بين الرسائل
                    await asyncio.sleep(interval)

            await conv.send_message("✅ تم الانتهاء من عملية التكرار بنجاح.")
        except Exception as e:
            await conv.send_message(f"❌ حدث خطأ أثناء التكرار: {str(e)}")
            
@bot.on(events.CallbackQuery(pattern='support_commands'))
async def support_commands(event):
    # إنشاء الأزرار الفرعية
    buttons = [
    [Button.inline('تجميع', 'collect')],  # زر التجميع
    [Button.inline('جمع الهدية', 'gift'), Button.inline('تحويل نقاط', 'transfer')],  # أزرار أخرى
    [Button.inline('شحن كود', 'charge'), Button.inline('فحص', 'check')],  # شحن كود وفحص
    [Button.inline('عودة', 'back_to_main')]  # زر العودة
]

    # تعديل الرسالة وإظهار الأزرار الفرعية
    try:
        await event.edit("• اختر أحد أوامر الخاصه ببوت @DamKombot", buttons=buttons)
    except telethon.errors.rpcerrorlist.MessageNotModifiedError:
        print("لم يتم تعديل الرسالة لأن المحتوى لم يتغير.")


# تعريف الحدث للزر الجديد
@bot.on(events.CallbackQuery(pattern='get_phone'))
async def get_phone_number(event):
    sender_id = str(event.sender_id)
    username = f"@{event.sender.username}" if event.sender.username else sender_id  
    
    if sender_id != str(owner_id) and (sender_id not in allowed_users and username not in allowed_users):
        await event.respond("🚫 أنت غير مسموح لك باستخدام هذا الخيار. لتفعيل البوت تواصل مع المطور.")
        return

    # التحقق إذا كان لدى المستخدم حسابات مسجلة
    if sender_id not in user_accounts or not user_accounts[sender_id]["sessions"]:
        await event.respond("🚫 لا توجد حسابات مسجلة لديك.")
        return

    async with bot.conversation(event.sender_id) as conv:
        try:
            # عرض الحسابات المسجلة للمستخدم
            accounts_list = "\n".join([f"{i+1}. {user}" for i, user in enumerate(user_accounts[sender_id]["users"])])
            await conv.send_message(f"📋 الحسابات المسجلة لديك:\n{accounts_list}\n\n♢ أرسل رقم الحساب الذي تريد جلب رقم هاتفه (مثال: 1):")

            # انتظار رد المستخدم برقم الحساب
            account_num = (await conv.get_response()).text.strip()

            # التحقق من صحة الإدخال
            try:
                account_num = int(account_num) - 1  # تحويل الرقم إلى مؤشر في القائمة
                if account_num < 0 or account_num >= len(user_accounts[sender_id]["sessions"]):
                    await conv.send_message("❌ رقم الحساب غير صحيح.")
                    return
            except ValueError:
                await conv.send_message("❌ الرقم الذي أدخلته غير صالح. يجب أن يكون رقمًا.")
                return

            # استخدام الحساب المحدد
            session_str = user_accounts[sender_id]["sessions"][account_num]
            client = TelegramClient(StringSession(session_str), api_id, api_hash)
            await client.connect()

            # جلب معلومات الحساب
            try:
                me = await client.get_me()
                phone_number = me.phone  # جلب رقم الهاتف
                await conv.send_message(f"📞 رقم هاتف الحساب المحدد:\n\n{phone_number}")
            except Exception as e:
                await conv.send_message(f"❌ حدث خطأ أثناء جلب رقم الهاتف: {str(e)}")

            await client.disconnect()

        except Exception as e:
            await conv.send_message(f"❌ حدث خطأ غير متوقع: {str(e)}")

# تعريف الحدث للزر الجديد
@bot.on(events.CallbackQuery(pattern='add_profile_photo'))
async def add_profile_photo(event):
    sender_id = str(event.sender_id)
    username = f"@{event.sender.username}" if event.sender.username else sender_id  
    
    if sender_id != str(owner_id) and (sender_id not in allowed_users and username not in allowed_users):
        await event.respond("🚫 أنت غير مسموح لك باستخدام هذا الخيار. لتفعيل البوت تواصل مع المطور.")
        return

    # التحقق إذا كان لدى المستخدم حسابات مسجلة
    if sender_id not in user_accounts or not user_accounts[sender_id]["sessions"]:
        await event.respond("🚫 لا توجد حسابات مسجلة لديك.")
        return

    async with bot.conversation(event.sender_id) as conv:
        try:
            # طلب الصورة من المستخدم
            await conv.send_message("🖼 أرسل الصورة التي تريد جعلها صورة بروفايل:")
            photo = await conv.get_response()

            # التحقق من أن المستخدم أرسل صورة
            if not photo.media or not hasattr(photo.media, 'photo'):
                await conv.send_message("🚫 لم تقم بإرسال صورة. الرجاء إرسال صورة.")
                return

            # تنزيل الصورة
            try:
                photo_path = await photo.download_media()
                await conv.send_message(f"✅ تم تنزيل الصورة بنجاح: {photo_path}")
            except Exception as e:
                await conv.send_message(f"❌ حدث خطأ أثناء تنزيل الصورة: {str(e)}")
                return

            # عرض الحسابات المسجلة للمستخدم
            accounts_list = "\n".join([f"{i+1}. {user}" for i, user in enumerate(user_accounts[sender_id]["users"])])
            await conv.send_message(f"📋 الحسابات المسجلة لديك:\n{accounts_list}\n\n♢ أرسل رقم الحساب الذي تريد تغيير صورة البروفايل له (مثال: 1):")

            # انتظار رد المستخدم برقم الحساب
            account_num = (await conv.get_response()).text.strip()

            # التحقق من صحة الإدخال
            try:
                account_num = int(account_num) - 1  # تحويل الرقم إلى مؤشر في القائمة
                if account_num < 0 or account_num >= len(user_accounts[sender_id]["sessions"]):
                    await conv.send_message("❌ رقم الحساب غير صحيح.")
                    return
            except ValueError:
                await conv.send_message("❌ الرقم الذي أدخلته غير صالح. يجب أن يكون رقمًا.")
                return

            # استخدام الحساب المحدد
            session_str = user_accounts[sender_id]["sessions"][account_num]
            client = TelegramClient(StringSession(session_str), api_id, api_hash)
            await client.connect()

            # تغيير صورة البروفايل
            try:
                await client(functions.photos.UploadProfilePhotoRequest(
                    file=await client.upload_file(photo_path)
                ))
                await conv.send_message(f"✅ تم تغيير صورة البروفايل للحساب رقم {account_num + 1} بنجاح.")
            except Exception as e:
                await conv.send_message(f"❌ حدث خطأ أثناء تغيير صورة البروفايل: {str(e)}")

            await client.disconnect()

            # حذف الصورة المحملة مؤقتًا
            try:
                os.remove(photo_path)
                await conv.send_message("✅ تم حذف الصورة المؤقتة بنجاح.")
            except Exception as e:
                await conv.send_message(f"❌ حدث خطأ أثناء حذف الصورة المؤقتة: {str(e)}")

        except Exception as e:
            await conv.send_message(f"❌ حدث خطأ غير متوقع: {str(e)}")

@bot.on(events.CallbackQuery(pattern='change_username'))
async def change_username(event):
    sender_id = str(event.sender_id)
    username = f"@{event.sender.username}" if event.sender.username else sender_id  
    
    if sender_id != str(owner_id) and (sender_id not in allowed_users and username not in allowed_users):
        await event.respond("🚫 أنت غير مسموح لك باستخدام هذا الخيار. لتفعيل البوت تواصل مع المطور.")
        return

    # التحقق إذا كان لدى المستخدم حسابات مسجلة
    if sender_id not in user_accounts or not user_accounts[sender_id]["sessions"]:
        await event.respond("🚫 لا توجد حسابات مسجلة لديك.")
        return

    async with bot.conversation(event.sender_id) as conv:
        try:
            # عرض الحسابات المسجلة للمستخدم
            accounts_list = "\n".join([f"{i+1}. {user}" for i, user in enumerate(user_accounts[sender_id]["users"])])
            await conv.send_message(f"📋 الحسابات المسجلة لديك:\n{accounts_list}\n\n♢ أرسل رقم الحساب الذي تريد تغيير يوزره (مثال: 1):")

            # انتظار رد المستخدم برقم الحساب
            account_num = (await conv.get_response()).text.strip()

            # التحقق من صحة الإدخال
            try:
                account_num = int(account_num) - 1  # تحويل الرقم إلى مؤشر في القائمة
                if account_num < 0 or account_num >= len(user_accounts[sender_id]["sessions"]):
                    await conv.send_message("❌ رقم الحساب غير صحيح.")
                    return
            except ValueError:
                await conv.send_message("❌ الرقم الذي أدخلته غير صالح. يجب أن يكون رقمًا.")
                return

            # طلب اليوزر الجديد
            await conv.send_message("♢ أرسل اليوزر الجديد الذي تريد تعيينه (مثال: @newusername):")
            new_username = (await conv.get_response()).text.strip().lstrip('@')

            # التحقق من طول اليوزر
            if len(new_username) < 5:
                await conv.send_message("❌ اليوزر يجب أن يكون على الأقل 5 أحرف.")
                return

            # استخدام الحساب المحدد
            session_str = user_accounts[sender_id]["sessions"][account_num]
            client = TelegramClient(StringSession(session_str), api_id, api_hash)
            await client.connect()

            # التحقق إذا كان اليوزر مستخدم بالفعل
            try:
                check_username = await client(functions.account.CheckUsernameRequest(username=new_username))
                if not check_username:
                    await conv.send_message("❌ هذا اليوزر مستخدم بالفعل. الرجاء اختيار يوزر آخر.")
                    return
            except Exception as e:
                await conv.send_message(f"❌ حدث خطأ أثناء التحقق من اليوزر: {str(e)}")
                return

            # تغيير اليوزر
            try:
                await client(functions.account.UpdateUsernameRequest(username=new_username))
                await conv.send_message(f"✅ تم تغيير اليوزر للحساب رقم {account_num + 1} بنجاح إلى: @{new_username}")
            except Exception as e:
                await conv.send_message(f"❌ حدث خطأ أثناء تغيير اليوزر: {str(e)}")

            await client.disconnect()

        except Exception as e:
            await conv.send_message(f"❌ حدث خطأ غير متوقع: {str(e)}")


@bot.on(events.CallbackQuery(pattern='view_post'))
async def view_post(event):
    sender_id = str(event.sender_id)
    username = f"@{event.sender.username}" if event.sender.username else sender_id  
    
    if sender_id != str(owner_id) and (sender_id not in allowed_users and username not in allowed_users):
        await event.respond("🚫 أنت غير مسموح لك باستخدام هذا الخيار. لتفعيل البوت تواصل مع المطور.")
        return
    
    # التحقق إذا كان لدى المستخدم حسابات مسجلة
    if sender_id not in user_accounts or not user_accounts[sender_id]["sessions"]:
        await event.respond("🚫 لا توجد حسابات مسجلة لديك.")
        return

    async with bot.conversation(event.sender_id) as conv:
        try:
            # طلب رابط المنشور
            await conv.send_message("♢ أرسل رابط المنشور الذي تريد مشاهدته:")
            post_link = (await conv.get_response()).text.strip()

            # استخراج معرف القناة ورقم الرسالة من الرابط
            if "t.me" in post_link:
                parts = post_link.split("/")
                if len(parts) >= 2:
                    channel_username = parts[-2]  # اسم القناة أو المعرف
                    message_id = int(parts[-1])  # رقم الرسالة
                else:
                    await conv.send_message("❌ الرابط غير صالح. يرجى إرسال رابط صحيح.")
                    return
            else:
                await conv.send_message("❌ الرابط غير صالح. يرجى إرسال رابط من Telegram.")
                return

            # طلب عدد الحسابات أو النطاق
            max_accounts = len(user_accounts[sender_id]["sessions"])
            await conv.send_message(f"♢ كم عدد الحسابات التي تريد استخدامها للمشاهدة؟ (الحد الأقصى {max_accounts}):\n\nيمكنك إدخال نطاق مثل 10-20 لبدء المشاهدة من الحساب رقم 10 إلى الحساب رقم 20.")
            account_input = (await conv.get_response()).text.strip()

            # تحليل النطاق إذا كان المدخل يحتوي على "-"
            if '-' in account_input:
                start, end = map(int, account_input.split('-'))
                account_indices = list(range(start - 1, end))  # تحويل إلى مؤشرات (تبدأ من 0)
            else:
                account_count = int(account_input)
                account_indices = list(range(min(account_count, max_accounts)))

            # تنفيذ عملية مشاهدة المنشور بشكل متزامن
            async def view_post_with_account(session_str, account_number):
                client = TelegramClient(StringSession(session_str), api_id, api_hash)
                await client.connect()

                try:
                    # إضافة فترة انتظار بين الطلبات
                    await asyncio.sleep(2)  # انتظار 2 ثانية بين الطلبات

                    # الحصول على كيان القناة
                    channel_entity = await client.get_entity(channel_username)

                    # الحصول على الرسالة
                    message = await client.get_messages(channel_entity, ids=message_id)
                    if not message:
                        await conv.send_message(f"❌ الحساب رقم {account_number}: لا يمكن العثور على الرسالة.")
                        return False

                    # إرسال طلب مشاهدة المنشور
                    await client(functions.messages.GetMessagesViewsRequest(
                        peer=channel_entity,
                        id=[message_id],
                        increment=True
                    ))

                    await conv.send_message(f"✅ تمت مشاهدة المنشور باستخدام الحساب رقم {account_number}.")
                    return True
                except PeerIdInvalidError:
                    await conv.send_message(f"❌ الحساب رقم {account_number}: لا يمكن العثور على القناة أو المجموعة.")
                except ChatWriteForbiddenError:
                    await conv.send_message(f"❌ الحساب رقم {account_number}: لا يمكن مشاهدة المنشور في هذه القناة (قد تكون القناة خاصة أو محظورة).")
                except FloodWaitError as e:
                    await conv.send_message(f"❌ الحساب رقم {account_number}: يجب الانتظار {e.seconds} ثانية قبل المحاولة مرة أخرى.")
                except Exception as e:
                    await conv.send_message(f"❌ حدث خطأ باستخدام الحساب رقم {account_number}: {str(e)}")
                finally:
                    await client.disconnect()

                return False

            # إنشاء قائمة بالمهام (tasks) لكل حساب
            tasks = [
                view_post_with_account(user_accounts[sender_id]["sessions"][i], i + 1)
                for i in account_indices
            ]

            # تنفيذ المهام بشكل متزامن
            results = await asyncio.gather(*tasks)

            # حساب عدد المشاهدات الناجحة
            successful_views = sum(results)
            await conv.send_message(f"✅ تم الانتهاء من عملية مشاهدة المنشور بنجاح. عدد المشاهدات الناجحة: {successful_views}.")
        except Exception as e:
            await conv.send_message(f"❌ حدث خطأ أثناء مشاهدة المنشور: {str(e)}")

@bot.on(events.CallbackQuery(pattern='change_name'))
async def change_name(event):
    sender_id = str(event.sender_id)
    username = f"@{event.sender.username}" if event.sender.username else sender_id  
    
    if sender_id != str(owner_id) and (sender_id not in allowed_users and username not in allowed_users):
        await event.respond("🚫 أنت غير مسموح لك باستخدام هذا الخيار. لتفعيل البوت تواصل مع المطور.")
        return
    
    # التحقق إذا كان لدى المستخدم حسابات مسجلة
    if sender_id not in user_accounts or not user_accounts[sender_id]["sessions"]:
        await event.respond("🚫 لا توجد حسابات مسجلة لديك.")
        return

    async with bot.conversation(event.sender_id) as conv:
        try:
            # عرض الحسابات المسجلة للمستخدم
            accounts_list = "\n".join([f"{i+1}. {user}" for i, user in enumerate(user_accounts[sender_id]["users"])])
            await conv.send_message(f"📋 الحسابات المسجلة لديك:\n{accounts_list}\n\n♢ أرسل رقم الحساب الذي تريد تغيير اسمه (مثال: 1):")

            # انتظار رد المستخدم برقم الحساب
            account_num = (await conv.get_response()).text.strip()

            # التحقق من صحة الإدخال
            try:
                account_num = int(account_num) - 1  # تحويل الرقم إلى مؤشر في القائمة
                if account_num < 0 or account_num >= len(user_accounts[sender_id]["sessions"]):
                    await conv.send_message("❌ رقم الحساب غير صحيح.")
                    return
            except ValueError:
                await conv.send_message("❌ الرقم الذي أدخلته غير صالح. يجب أن يكون رقمًا.")
                return

            # طلب الاسم الجديد
            await conv.send_message("♢ أرسل الاسم الجديد الذي تريد تعيينه:")
            new_name = (await conv.get_response()).text.strip()

            # استخدام الحساب المحدد
            session_str = user_accounts[sender_id]["sessions"][account_num]
            client = TelegramClient(StringSession(session_str), api_id, api_hash)
            await client.connect()

            # تغيير الاسم
            try:
                await client(functions.account.UpdateProfileRequest(
                    first_name=new_name
                ))

                # الحصول على معلومات المستخدم بعد التحديث
                user = await client.get_me()

                # تحديث الاسم في القائمة user_accounts
                user_accounts[sender_id]["users"][account_num] = f"{user.id} - {new_name}"
                save_data()  # حفظ التغييرات في الملف

                await conv.send_message(f"✅ تم تغيير اسم الحساب رقم {account_num + 1} بنجاح إلى: {new_name}")
            except Exception as e:
                await conv.send_message(f"❌ حدث خطأ أثناء تغيير الاسم: {str(e)}")

            await client.disconnect()

        except Exception as e:
            await conv.send_message(f"❌ حدث خطأ غير متوقع: {str(e)}")


@bot.on(events.CallbackQuery(pattern='collect'))
async def collect_points(event):
    sender_id = str(event.sender_id)
    username = f"@{event.sender.username}" if event.sender.username else sender_id  

    if sender_id != str(owner_id) and (sender_id not in allowed_users and username not in allowed_users):
        await event.respond("🚫 أنت غير مسموح لك باستخدام هذا الخيار. لتفعيل البوت تواصل مع المطور.")
        return

    # التحقق إذا كان لدى المستخدم حسابات مسجلة
    if sender_id not in user_accounts or not user_accounts[sender_id]["sessions"]:
        await event.respond("🚫 **لا توجد حسابات مسجلة لديك.**")
        return

    async with bot.conversation(event.sender_id) as conv:
        try:
            # طلب عدد الحسابات التي سيتم استخدامها
            max_accounts = len(user_accounts[sender_id]["sessions"])
            await conv.send_message(
                "**♢ كم عدد الحسابات التي تريد استخدامها للتجميع؟ (الحد الأقصى 28):**\n\n"
                "> يمكنك إدخال نطاق مثل 10-20 لبدء التجميع من الحساب رقم 10 إلى الحساب رقم 20."
            )
            response = (await conv.get_response()).text

            # تحديد نطاق الحسابات
            if '-' in response:
                start, end = map(int, response.split('-'))
                account_indices = range(start - 1, end)
            else:
                account_count = int(response)
                account_indices = range(min(account_count, max_accounts))

            # تقسيم الحسابات إلى مجموعات من 2 للجمع المتزامن
            success_reports = []
            failure_reports = []

            for i in range(0, len(account_indices), 2):  # تغيير حجم الدفعة إلى 2
                batch = account_indices[i:i + 2]
                results = await asyncio.gather(*[collect_points_for_account(sender_id, idx, conv) for idx in batch], return_exceptions=True)

                # تسجيل النتائج
                for idx, result in zip(batch, results):
                    if isinstance(result, Exception):
                        failure_reports.append(f"❌ **الحساب رقم {idx + 1}:** فشل بسبب: {str(result)}")
                    else:
                        success_reports.append(f"✅ **الحساب رقم {idx + 1}:** تم التجميع بنجاح.")

                # إضافة فترة انتظار 15 ثانية بين كل دفعة
                await asyncio.sleep(15)

            # إرسال التقرير النهائي
            report = "📊 **تقرير التجميع:**\n\n"
            report += "\n".join(success_reports) + "\n"
            report += "\n".join(failure_reports)
            await conv.send_message(report)

        except Exception as e:
            await conv.send_message(f"❌ **حدث خطأ أثناء التجميع:** {str(e)}")
            
async def collect_points_for_account(sender_id, account_index, conv, retry_count=3):
    session_str = user_accounts[sender_id]["sessions"][account_index]
    client = TelegramClient(StringSession(session_str), api_id, api_hash)
    await client.connect()

    try:
        for attempt in range(retry_count):
            try:
                # إرسال /start إلى بوت @DamKombot
                await client.send_message('@DamKombot', '/start')
                await asyncio.sleep(10)  # زيادة وقت الانتظار إلى 10 ثواني

                # التحقق من الاشتراك الإجباري
                while True:
                    messages = await client.get_messages('@DamKombot', limit=1)
                    if messages and hasattr(messages[0], 'text') and "عليك الاشتراك بالقنوات" in messages[0].text:
                        buttons = messages[0].buttons
                        if buttons:
                            for button_row in buttons:
                                for button in button_row:
                                    if hasattr(button, 'text'):
                                        link = re.search(r'@(\w+)', button.text)
                                        if link:
                                            channel_username = link.group(0)
                                            try:
                                                await client(JoinChannelRequest(channel_username))
                                                await conv.send_message(f"✅ **الحساب رقم {account_index + 1} اشترك في قناة الإشتراك الاجباري {channel_username}.**")
                                                await asyncio.sleep(10)  # زيادة وقت الانتظار
                                            except FloodWaitError as e:
                                                await conv.send_message(f"⏳ **الحساب رقم {account_index + 1}: يلزم الانتظار {e.seconds} ثانية.**")
                                                await asyncio.sleep(e.seconds)  # الانتظار للمدة المطلوبة
                                                await client(JoinChannelRequest(channel_username))
                                            except Exception as e:
                                                await conv.send_message(f"❌ **الحساب رقم {account_index + 1}: حدث خطأ أثناء الاشتراك في القناة {channel_username}: {str(e)}**")
                            await client.send_message('@DamKombot', '/start')
                            await asyncio.sleep(10)  # زيادة وقت الانتظار
                        else:
                            break  # الخروج من الحلقة إذا لم تكن هناك قنوات إجبارية

                # إرسال إخطار للمستخدم ببدء التجميع
                await conv.send_message(f"✅ **بدأ التجميع في الحساب رقم {account_index + 1}...**")

                # الحصول على آخر رسالة من البوت
                messages = await client.get_messages('@DamKombot', limit=1)
                if messages and hasattr(messages[0], 'text') and "نقاطك" in messages[0].text:
                    # الضغط على زر "تجميع ✳️"
                    await messages[0].click(text="تجميع ✳️")
                    await asyncio.sleep(10)  # زيادة وقت الانتظار

                    # الحصول على آخر رسالة من البوت بعد الضغط على زر التجميع
                    messages = await client.get_messages('@DamKombot', limit=1)
                    if messages and hasattr(messages[0], 'text') and "✳️ تجميع نقاط" in messages[0].text:
                        # الضغط على زر "الانضمام لقنوات 📣"
                        await messages[0].click(text="الانضمام لقنوات 📣")
                        await asyncio.sleep(10)  # زيادة وقت الانتظار

                        # حلقة الاشتراك في القنوات
                        max_attempts = 50
                        attempt = 0

                        while attempt < max_attempts:
                            try:
                                messages = await client.get_messages('@DamKombot', limit=1)
                                if messages and hasattr(messages[0], 'text'):
                                    if "لا يوجد قنوات حالياً 🤍" in messages[0].text:
                                        await conv.send_message(f"✅ **الحساب رقم {account_index + 1}: لا يوجد المزيد من القنوات للاشتراك.**")
                                        break

                                    if "اشترك فالقناة" in messages[0].text:
                                        channel_username = re.search(r'@(\w+)', messages[0].text).group(1)
                                        if channel_username:
                                            try:
                                                # الانضمام إلى القناة
                                                await client(JoinChannelRequest(channel_username))
                                                await conv.send_message(f"♢ **الحساب رقم {account_index + 1}: تم الاشتراك في @{channel_username}.**")
                                                await asyncio.sleep(10)  # زيادة وقت الانتظار

                                                # الضغط على زر "اشتركت ✅"
                                                await messages[0].click(text="اشتركت ✅")
                                                await asyncio.sleep(10)  # زيادة وقت الانتظار

                                                # مغادرة القناة
                                                await client(LeaveChannelRequest(channel_username))
                                                await conv.send_message(f"♢ **الحساب رقم {account_index + 1}: تم مغادرة @{channel_username}.**")
                                                await asyncio.sleep(10)  # زيادة وقت الانتظار

                                            except FloodWaitError as e:
                                                await conv.send_message(f"⏳ **يلزم الانتظار {e.seconds} ثانية قبل المحاولة مرة أخرى.**")
                                                await asyncio.sleep(e.seconds)  # الانتظار للفترة المطلوبة
                                                await client(JoinChannelRequest(channel_username))
                                            except Exception as e:
                                                raise Exception(f"حدث خطأ أثناء الاشتراك في القناة @{channel_username}: {str(e)}")

                                        attempt += 1
                                    else:
                                        await conv.send_message(f"⚠️ **لم يتم العثور على رابط قناة في الحساب رقم {account_index + 1}.**")
                                        break
                                else:
                                    await conv.send_message(f"⚠️ **لم يتم العثور على رسالة من البوت في الحساب رقم {account_index + 1}.**")
                                    break
                            except FloodWaitError as e:
                                await conv.send_message(f"⏳ **يلزم الانتظار {e.seconds} ثانية قبل المحاولة مرة أخرى.**")
                                await asyncio.sleep(e.seconds)  # الانتظار للفترة المطلوبة
                                continue  # إعادة المحاولة بعد الانتظار

                # إرسال /start بعد الانتهاء من التجميع
                await client.send_message('@DamKombot', '/start')
                await asyncio.sleep(10)

                # إخبار المستخدم بنجاح التجميع لهذا الحساب
                await conv.send_message(f"✅ **تم الانتهاء من عملية التجميع في الحساب رقم {account_index + 1}.**")
                return  # نجاح العملية

            except FloodWaitError as e:
                await conv.send_message(f"⏳ **الحساب رقم {account_index + 1}: يلزم الانتظار {e.seconds} ثانية.**")
                await asyncio.sleep(e.seconds)  # الانتظار للمدة المطلوبة
                continue  # إعادة المحاولة بعد الانتظار
            except Exception as e:
                if attempt < retry_count - 1:
                    await conv.send_message(f"⚠️ **الحساب رقم {account_index + 1}: إعادة المحاولة ({attempt + 1}/{retry_count}) بسبب: {str(e)}**")
                    await client.send_message('@DamKombot', '/start')  # إعادة إرسال /start
                    await asyncio.sleep(10)  # زيادة وقت الانتظار
                    continue
                else:
                    raise e  # رفع الخطأ إذا فشلت جميع المحاولات

    except Exception as e:
        raise e  # رفع الخطأ لتسجيله في التقرير

    finally:
        await client.disconnect()            


@bot.on(events.CallbackQuery(pattern='transfer'))
async def collect_gift(event):
    sender_id = str(event.sender_id)
    username = f"@{event.sender.username}" if event.sender.username else sender_id  

    if sender_id != str(owner_id) and (sender_id not in allowed_users and username not in allowed_users):
        await event.respond("🚫 أنت غير مسموح لك باستخدام هذا الخيار. لتفعيل البوت تواصل مع المطور.")
        return
        
    # التحقق إذا كان لدى المستخدم حسابات مسجلة
    if sender_id not in user_accounts or not user_accounts[sender_id]["sessions"]:
        await event.respond("🚫 **لا توجد حسابات مسجلة لديك.**")
        return

    async with bot.conversation(event.sender_id) as conv:
        try:
            # طلب الأيدي الذي سيتم التحويل إليه
            await conv.send_message("🔢 **أرسل الأيدي الذي تريد تحويل النقاط إليه:**")
            target_id = (await conv.get_response()).text

            # طلب عدد الحسابات التي سيتم استخدامها
            max_accounts = len(user_accounts[sender_id]["sessions"])
            await conv.send_message(f"♢ **كم عدد الحسابات التي تريد استخدامها لتحويل النقاط؟ (الحد الأقصى {max_accounts}):**\n\nيمكنك إدخال نطاق مثل 10-20 لبدء التجميع من الحساب رقم 10 إلى الحساب رقم 20.")
            account_input = (await conv.get_response()).text

            # تحليل النطاق إذا كان المدخل يحتوي على "-"
            if '-' in account_input:
                start, end = map(int, account_input.split('-'))
                account_indices = list(range(start - 1, end))  # تحويل إلى مؤشرات (تبدأ من 0)
            else:
                account_count = int(account_input)
                account_indices = list(range(min(account_count, max_accounts)))

            # تقسيم الحسابات إلى مجموعات من 2 للتحويل المتزامن
            success_reports = []
            failure_reports = []

            for i in range(0, len(account_indices), 2):
                batch = account_indices[i:i + 2]
                results = await asyncio.gather(*[transfer_points(sender_id, idx, target_id, conv) for idx in batch], return_exceptions=True)

                # تسجيل النتائج
                for idx, result in zip(batch, results):
                    if isinstance(result, Exception):
                        failure_reports.append(f"❌ **الحساب رقم {idx + 1}:** فشل بسبب: {str(result)}")
                    else:
                        success_reports.append(f"✅ **الحساب رقم {idx + 1}:** تم تحويل {result} نقطة بنجاح.")

                # انتظار 15 ثانية بين كل دفعة
                await asyncio.sleep(15)

            # إرسال التقرير النهائي
            report = "📊 **تقرير تحويل النقاط:**\n\n"
            report += "\n".join(success_reports) + "\n"
            report += "\n".join(failure_reports)
            await conv.send_message(report)

        except Exception as e:
            await conv.send_message(f"🚫 **حدث خطأ أثناء تنفيذ العملية:** {str(e)}")
            
async def transfer_points(sender_id, account_index, target_id, conv, retry_count=2):
    session_str = user_accounts[sender_id]["sessions"][account_index]
    client = TelegramClient(StringSession(session_str), api_id, api_hash)
    await client.connect()

    try:
        for attempt in range(retry_count):
            try:
                # إرسال /start إلى بوت @DamKombot
                await client.send_message('@DamKombot', '/start')
                await asyncio.sleep(10)  # زيادة وقت الانتظار إلى 10 ثواني

                # التحقق من الاشتراك الإجباري
                while True:
                    messages = await client.get_messages('@DamKombot', limit=1)
                    if messages and hasattr(messages[0], 'text') and "عليك الاشتراك بالقنوات" in messages[0].text:
                        buttons = messages[0].buttons
                        if buttons:
                            for button_row in buttons:
                                for button in button_row:
                                    if hasattr(button, 'text'):
                                        link = re.search(r'@(\w+)', button.text)
                                        if link:
                                            channel_username = link.group(0)
                                            try:
                                                await client(JoinChannelRequest(channel_username))
                                                await conv.send_message(f"✅ **الحساب رقم {account_index + 1} اشترك في قناة الإشتراك الاجباري {channel_username}.**")
                                                await asyncio.sleep(10)  # زيادة وقت الانتظار
                                            except FloodWaitError as e:
                                                await conv.send_message(f"⏳ **الحساب رقم {account_index + 1}: يلزم الانتظار {e.seconds} ثانية.**")
                                                await asyncio.sleep(e.seconds)  # الانتظار للمدة المطلوبة
                                                await client(JoinChannelRequest(channel_username))
                                            except Exception as e:
                                                await conv.send_message(f"❌ **الحساب رقم {account_index + 1}: حدث خطأ أثناء الاشتراك في القناة {channel_username}: {str(e)}**")
                            await client.send_message('@DamKombot', '/start')
                            await asyncio.sleep(10)  # زيادة وقت الانتظار
                        else:
                            break  # الخروج من الحلقة إذا لم تكن هناك قنوات إجبارية

                # إرسال إخطار للمستخدم ببدء تحويل النقاط
                await conv.send_message(f"✅ **بدأ تحويل النقاط في الحساب رقم {account_index + 1}...**")

                # الحصول على آخر رسالة من البوت
                messages = await client.get_messages('@DamKombot', limit=1)
                if messages and hasattr(messages[0], 'text') and "نقاطك" in messages[0].text:
                    # الضغط على زر "تحويل نقاط ♻️"
                    await messages[0].click(text="تحويل نقاط ♻️")
                    await asyncio.sleep(10)  # زيادة وقت الانتظار

                    # الحصول على آخر رسالة من البوت بعد الضغط على زر التجميع
                    messages = await client.get_messages('@DamKombot', limit=1)
                    if messages and hasattr(messages[0], 'text') and "🔢) اختر طريقة التحويل :" in messages[0].text:
                        # الضغط على زر "التحويل الى ايدي 👤"
                        await messages[0].click(text="التحويل الى ايدي 👤")
                        await asyncio.sleep(10)  # زيادة وقت الانتظار

                        # إرسال الأيدي الذي تم الحصول عليه من المستخدم
                        await client.send_message('@DamKombot', target_id)
                        await asyncio.sleep(10)  # زيادة وقت الانتظار

                        # الحصول على آخر رسالة من البوت بعد إرسال الأيدي
                        messages = await client.get_messages('@DamKombot', limit=1)
                        if messages and hasattr(messages[0], 'text') and "💳 ارسل الكمية :" in messages[0].text:
                            # إرسال عدد النقاط الذي تم استخراجه سابقًا
                            await client.send_message('@DamKombot', str(points_amount))
                            await conv.send_message(f"✅ **تم تحويل {points_amount} نقطة من الحساب رقم {account_index + 1} إلى الأيدي {target_id}.**")
                            await asyncio.sleep(10)  # زيادة وقت الانتظار
                            return points_amount  # إرجاع عدد النقاط المحولة

            except FloodWaitError as e:
                await conv.send_message(f"⏳ **الحساب رقم {account_index + 1}: يلزم الانتظار {e.seconds} ثانية.**")
                await asyncio.sleep(e.seconds)  # الانتظار للمدة المطلوبة
                continue  # إعادة المحاولة بعد الانتظار
            except Exception as e:
                if attempt < retry_count - 1:
                    await conv.send_message(f"⚠️ **الحساب رقم {account_index + 1}: إعادة المحاولة ({attempt + 1}/{retry_count}) بسبب: {str(e)}**")
                    await client.send_message('@DamKombot', '/start')  # إعادة إرسال /start
                    await asyncio.sleep(10)  # زيادة وقت الانتظار
                    continue
                else:
                    raise e  # رفع الخطأ إذا فشلت جميع المحاولات

    except Exception as e:
        raise e  # رفع الخطأ لتسجيله في التقرير

    finally:
        await client.disconnect()




                                                
@bot.on(events.CallbackQuery(pattern='gift'))
async def collect_gift(event):
    sender_id = str(event.sender_id)
    username = f"@{event.sender.username}" if event.sender.username else sender_id  
    
    if sender_id != str(owner_id) and (sender_id not in allowed_users and username not in allowed_users):
        await event.respond("🚫 أنت غير مسموح لك باستخدام هذا الخيار. لتفعيل البوت تواصل مع المطور.")
        return
    
    # التحقق إذا كان لدى المستخدم حسابات مسجلة
    if sender_id not in user_accounts or not user_accounts[sender_id]["sessions"]:
        await event.respond("🚫 **لا توجد حسابات مسجلة لديك.**")
        return

    async with bot.conversation(event.sender_id) as conv:
        try:
            # طلب عدد الحسابات التي سيتم استخدامها
            max_accounts = len(user_accounts[sender_id]["sessions"])
            await conv.send_message(f"♢ **كم عدد الحسابات التي تريد استخدامها لتجميع الهدايا؟ (الحد الأقصى {max_accounts}):**\n\nيمكنك إدخال نطاق مثل 10-20 لبدء التجميع من الحساب رقم 10 إلى الحساب رقم 20.")
            account_input = (await conv.get_response()).text

            # تحليل النطاق إذا كان المدخل يحتوي على "-"
            if '-' in account_input:
                start, end = map(int, account_input.split('-'))
                account_indices = list(range(start - 1, end))  # تحويل إلى مؤشرات (تبدأ من 0)
            else:
                account_count = int(account_input)
                account_indices = list(range(min(account_count, max_accounts)))

            # تقسيم الحسابات إلى مجموعات من 2 للجمع المتزامن
            success_reports = []
            failure_reports = []

            for i in range(0, len(account_indices), 2):
                batch = account_indices[i:i + 2]
                results = await asyncio.gather(*[collect_gift_for_account(sender_id, idx, conv) for idx in batch], return_exceptions=True)

                # تسجيل النتائج
                for idx, result in zip(batch, results):
                    if isinstance(result, Exception):
                        failure_reports.append(f"❌ **الحساب رقم {idx + 1}:** فشل بسبب: {str(result)}")
                    else:
                        success_reports.append(f"✅ **الحساب رقم {idx + 1}:** تم جمع الهدية بنجاح.")

                # انتظار 15 ثانية بين كل دفعة
                await asyncio.sleep(15)

            # إرسال التقرير النهائي
            report = "📊 **تقرير تجميع الهدايا:**\n\n"
            report += "\n".join(success_reports) + "\n"
            report += "\n".join(failure_reports)
            await conv.send_message(report)

        except Exception as e:
            await conv.send_message(f"❌ **حدث خطأ أثناء تجميع الهدايا:** {str(e)}")
async def collect_gift_for_account(sender_id, account_index, conv, retry_count=3):
    session_str = user_accounts[sender_id]["sessions"][account_index]
    client = TelegramClient(StringSession(session_str), api_id, api_hash)
    await client.connect()

    try:
        for attempt in range(retry_count):
            try:
                # إرسال /start إلى بوت @DamKombot
                await client.send_message('@DamKombot', '/start')
                await asyncio.sleep(10)  # زيادة وقت الانتظار إلى 10 ثواني

                # التحقق من الاشتراك الإجباري
                while True:
                    messages = await client.get_messages('@DamKombot', limit=1)
                    if messages and hasattr(messages[0], 'text') and "عليك الاشتراك بالقنوات" in messages[0].text:
                        buttons = messages[0].buttons
                        if buttons:
                            for button_row in buttons:
                                for button in button_row:
                                    if hasattr(button, 'text'):
                                        link = re.search(r'@(\w+)', button.text)
                                        if link:
                                            channel_username = link.group(0)
                                            try:
                                                await client(JoinChannelRequest(channel_username))
                                                await conv.send_message(f"✅ **الحساب رقم {account_index + 1} اشترك في قناة الإشتراك الاجباري {channel_username}.**")
                                                await asyncio.sleep(10)  # زيادة وقت الانتظار
                                            except FloodWaitError as e:
                                                await conv.send_message(f"⏳ **الحساب رقم {account_index + 1}: يلزم الانتظار {e.seconds} ثانية.**")
                                                await asyncio.sleep(e.seconds)  # الانتظار للمدة المطلوبة
                                                await client(JoinChannelRequest(channel_username))
                                            except Exception as e:
                                                await conv.send_message(f"❌ **الحساب رقم {account_index + 1}: حدث خطأ أثناء الاشتراك في القناة {channel_username}: {str(e)}**")
                            await client.send_message('@DamKombot', '/start')
                            await asyncio.sleep(10)  # زيادة وقت الانتظار
                        else:
                            break  # الخروج من الحلقة إذا لم تكن هناك قنوات إجبارية

                # إرسال إخطار للمستخدم ببدء تجميع الهدية
                await conv.send_message(f"✅ **بدأ تجميع الهدية في الحساب رقم {account_index + 1}...**")

                # الحصول على آخر رسالة من البوت
                messages = await client.get_messages('@DamKombot', limit=1)
                if messages and hasattr(messages[0], 'text') and "نقاطك" in messages[0].text:
                    # الضغط على زر "تجميع ✳️"
                    await messages[0].click(text="تجميع ✳️")
                    await asyncio.sleep(10)  # زيادة وقت الانتظار

                    # الحصول على آخر رسالة من البوت بعد الضغط على زر التجميع
                    messages = await client.get_messages('@DamKombot', limit=1)
                    if messages and hasattr(messages[0], 'text') and "✳️ تجميع نقاط" in messages[0].text:
                        # الضغط على زر "الهدية 🎁"
                        await messages[0].click(text="الهدية 🎁")
                        await asyncio.sleep(10)  # زيادة وقت الانتظار

                        # الحصول على آخر رسالة من البوت بعد الضغط على زر الهدية
                        messages = await client.get_messages('@DamKombot', limit=1)
                        if messages and hasattr(messages[0], 'text'):
                            if "🗃️ الحساب" in messages[0].text:
                                # إرسال إخطار بأن الهدية تم جمعها بنجاح
                                await conv.send_message(f"✅ **تم جمع الهدية في الحساب رقم {account_index + 1}.**")
                                # إرسال /start لإيقاف العملية
                                await client.send_message('@DamKombot', '/start')
                                await asyncio.sleep(10)  # زيادة وقت الانتظار
                                return  # نجاح العملية
                            else:
                                raise Exception("تم جمع الهدية من قبل.")
                        else:
                            raise Exception("لم يتم العثور على رسالة الهدية.")
                    else:
                        raise Exception("لم يتم العثور على زر الهدية.")
                else:
                    raise Exception("لم يتم العثور على رسالة النقاط.")

            except FloodWaitError as e:
                await conv.send_message(f"⏳ **الحساب رقم {account_index + 1}: يلزم الانتظار {e.seconds} ثانية.**")
                await asyncio.sleep(e.seconds)  # الانتظار للمدة المطلوبة
                continue  # إعادة المحاولة بعد الانتظار
            except Exception as e:
                if "تم جمع الهدية من قبل" in str(e):
                    raise Exception("تم جمع الهدية من قبل.")
                elif attempt < retry_count - 1:
                    await conv.send_message(f"⚠️ **الحساب رقم {account_index + 1}: إعادة المحاولة ({attempt + 1}/{retry_count}) بسبب: {str(e)}**")
                    await client.send_message('@DamKombot', '/start')  # إعادة إرسال /start
                    await asyncio.sleep(10)  # زيادة وقت الانتظار
                    continue
                else:
                    raise e  # رفع الخطأ إذا فشلت جميع المحاولات

    except Exception as e:
        raise e  # رفع الخطأ لتسجيله في التقرير

    finally:
        await client.disconnect()                                                                      



    






@bot.on(events.CallbackQuery(pattern='charge'))  # تعريف الزر بـ use_code
async def use_code(event):
    sender_id = str(event.sender_id)
    username = f"@{event.sender.username}" if event.sender.username else sender_id  
    
    if sender_id != str(owner_id) and (sender_id not in allowed_users and username not in allowed_users):
        await event.respond("🚫 أنت غير مسموح لك باستخدام هذا الخيار. لتفعيل البوت تواصل مع المطور.")
        return
        
    # التحقق إذا كان لدى المستخدم حسابات مسجلة
    if sender_id not in user_accounts or not user_accounts[sender_id]["sessions"]:
        await event.respond("🚫 **لا توجد حسابات مسجلة لديك.**")
        return

    async with bot.conversation(event.sender_id) as conv:
        try:
            # طلب الكود الذي سيتم استخدامه
            await conv.send_message("💳 **أرسل الكود الذي تريد شحنه:**")
            code = (await conv.get_response()).text

            # طلب عدد الحسابات التي سيتم استخدامها
            max_accounts = len(user_accounts[sender_id]["sessions"])
            await conv.send_message(f"♢ **كم عدد الحسابات التي تريد استخدامها لإضافة النقاط؟ (الحد الأقصى {max_accounts}):**\n\nيمكنك إدخال نطاق مثل 10-20 لبدء التجميع من الحساب رقم 10 إلى الحساب رقم 20.")
            account_input = (await conv.get_response()).text

            # تحليل النطاق إذا كان المدخل يحتوي على "-"
            if '-' in account_input:
                start, end = map(int, account_input.split('-'))
                account_indices = list(range(start - 1, end))  # تحويل إلى مؤشرات (تبدأ من 0)
            else:
                account_count = int(account_input)
                account_indices = list(range(min(account_count, max_accounts)))

            # تقسيم الحسابات إلى مجموعات من 2 للتحويل المتزامن
            success_reports = []
            failure_reports = []

            for i in range(0, len(account_indices), 2):  # تغيير حجم الدفعة إلى 2
                batch = account_indices[i:i + 2]
                tasks = [use_code_with_account(sender_id, idx, code, conv) for idx in batch]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # تسجيل النتائج
                for idx, result in zip(batch, results):
                    if isinstance(result, Exception):
                        failure_reports.append(f"❌ **الحساب رقم {idx + 1}:** فشل بسبب: {str(result)}")
                    else:
                        success_reports.append(f"✅ **الحساب رقم {idx + 1}:** تم شحن الكود بنجاح.")

                # زيادة وقت الانتظار بين الدفعات
                await asyncio.sleep(10)  # انتظار 10 ثواني بين كل دفعة

            # إرسال التقرير النهائي
            report = "📊 **تقرير شحن الكود:\n\n"
            report += "\n".join(success_reports) + "\n"
            report += "\n".join(failure_reports)
            await conv.send_message(report)

        except Exception as e:
            await conv.send_message(f"🚫 **حدث خطأ أثناء تنفيذ العملية:** {str(e)}")


async def use_code_with_account(sender_id, account_index, code, conv, retry_count=3):
    session_str = user_accounts[sender_id]["sessions"][account_index]
    client = TelegramClient(StringSession(session_str), api_id, api_hash)
    await client.connect()

    try:
        for attempt in range(retry_count):
            try:
                # إرسال إخطار ببدء العملية
                await conv.send_message(f"⏳ **بدأ العملية في الحساب رقم {account_index + 1}...**")

                # إرسال /start إلى بوت @DamKombot
                await client.send_message('@DamKombot', '/start')
                await asyncio.sleep(10)  # زيادة وقت الانتظار إلى 10 ثواني

                # التحقق من الاشتراك الإجباري
                while True:
                    messages = await client.get_messages('@DamKombot', limit=1)
                    if messages and hasattr(messages[0], 'text'):
                        if "عليك الاشتراك بالقنوات" in messages[0].text:
                            buttons = messages[0].buttons
                            if buttons:
                                for button_row in buttons:
                                    for button in button_row:
                                        if hasattr(button, 'text'):
                                            link = re.search(r'@(\w+)', button.text)
                                            if link:
                                                channel_username = link.group(0)
                                                try:
                                                    await client(JoinChannelRequest(channel_username))
                                                    await conv.send_message(f"✅ **الحساب رقم {account_index + 1} اشترك في قناة الإشتراك الاجباري {channel_username}.**")
                                                    await asyncio.sleep(10)  # زيادة وقت الانتظار
                                                except FloodWaitError as e:
                                                    await conv.send_message(f"⏳ **الحساب رقم {account_index + 1}: يلزم الانتظار {e.seconds} ثانية.**")
                                                    await asyncio.sleep(e.seconds)  # الانتظار للمدة المطلوبة
                                                    await client(JoinChannelRequest(channel_username))
                                                except Exception as e:
                                                    await conv.send_message(f"❌ **الحساب رقم {account_index + 1}: حدث خطأ أثناء الاشتراك في القناة {channel_username}: {str(e)}**")
                            await client.send_message('@DamKombot', '/start')
                            await asyncio.sleep(10)  # زيادة وقت الانتظار
                        else:
                            break  # الخروج من الحلقة إذا لم تكن هناك قنوات إجبارية

                # الحصول على آخر رسالة من البوت
                messages = await client.get_messages('@DamKombot', limit=1)
                if messages and hasattr(messages[0], 'buttons'):
                    # البحث عن زر "استخدام كود 💳"
                    for button_row in messages[0].buttons:
                        for button in button_row:
                            if button.text == "استخدام كود 💳":
                                # الضغط على الزر
                                await button.click()
                                await asyncio.sleep(10)  # زيادة وقت الانتظار

                                # إرسال الكود
                                await client.send_message('@DamKombot', code)
                                await asyncio.sleep(10)  # زيادة وقت الانتظار

                                # إرسال تقرير نجاح
                                await conv.send_message(f"✅ **الحساب رقم {account_index + 1}:** تم إرسال الكود بنجاح.")
                                return  # إنهاء العملية بعد إرسال الكود

                # إذا لم يتم العثور على الزر، إعادة المحاولة
                if attempt < retry_count - 1:
                    await conv.send_message(f"⚠️ **الحساب رقم {account_index + 1}: إعادة المحاولة ({attempt + 1}/{retry_count})**")
                    await client.send_message('@DamKombot', '/start')  # إعادة إرسال /start
                    await asyncio.sleep(10)  # زيادة وقت الانتظار
                    continue
                else:
                    raise Exception("لم يتم العثور على زر 'استخدام كود 💳' بعد عدة محاولات.")

            except FloodWaitError as e:
                await conv.send_message(f"⏳ **الحساب رقم {account_index + 1}: يلزم الانتظار {e.seconds} ثانية.**")
                await asyncio.sleep(e.seconds)  # الانتظار للمدة المطلوبة
                continue  # إعادة المحاولة بعد الانتظار
            except Exception as e:
                if attempt < retry_count - 1:
                    await conv.send_message(f"⚠️ **الحساب رقم {account_index + 1}: إعادة المحاولة ({attempt + 1}/{retry_count}) بسبب: {str(e)}**")
                    await asyncio.sleep(10)  # زيادة وقت الانتظار
                    continue
                else:
                    raise e  # رفع الخطأ إذا فشلت جميع المحاولات

    except Exception as e:
        raise e  # رفع الخطأ لتسجيله في التقرير

    finally:
        await client.disconnect()


@bot.on(events.CallbackQuery(pattern='check'))  # تعريف الزر بـ check
async def check_subscription(event):
    sender_id = str(event.sender_id)
    username = f"@{event.sender.username}" if event.sender.username else sender_id  
    
    if sender_id != str(owner_id) and (sender_id not in allowed_users and username not in allowed_users):
        await event.respond("🚫 أنت غير مسموح لك باستخدام هذا الخيار. لتفعيل البوت تواصل مع المطور.")
        return
        
    # التحقق إذا كان لدى المستخدم حسابات مسجلة
    if sender_id not in user_accounts or not user_accounts[sender_id]["sessions"]:
        await event.respond("🚫 **لا توجد حسابات مسجلة لديك.**")
        return

    async with bot.conversation(event.sender_id) as conv:
        try:
            # طلب عدد الحسابات التي سيتم استخدامها
            max_accounts = len(user_accounts[sender_id]["sessions"])
            await conv.send_message(f"♢ **كم عدد الحسابات التي تريد التحقق منها؟ (الحد الأقصى {max_accounts}):**\n\nيمكنك إدخال نطاق مثل 10-20 لبدء التحقق من الحساب رقم 10 إلى الحساب رقم 20.")
            account_input = (await conv.get_response()).text

            # تحليل النطاق إذا كان المدخل يحتوي على "-"
            if '-' in account_input:
                start, end = map(int, account_input.split('-'))
                account_indices = list(range(start - 1, end))  # تحويل إلى مؤشرات (تبدأ من 0)
            else:
                account_count = int(account_input)
                account_indices = list(range(min(account_count, max_accounts)))

            # تقسيم الحسابات إلى مجموعات من 2 للتحقق المتزامن
            success_reports = []
            failure_reports = []

            for i in range(0, len(account_indices), 2):
                batch = account_indices[i:i + 2]
                tasks = [check_subscription_for_account(sender_id, idx, conv) for idx in batch]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # تسجيل النتائج
                for idx, result in zip(batch, results):
                    if isinstance(result, Exception):
                        failure_reports.append(f"❌ **الحساب رقم {idx + 1}:** فشل بسبب: {str(result)}")
                    else:
                        success_reports.append(f"✅ **الحساب رقم {idx + 1}:** تم التحقق بنجاح.")

                # انتظار 10 ثواني بين كل دفعة
                await asyncio.sleep(10)

            # إرسال التقرير النهائي
            report = "📊 **تقرير التحقق:**\n\n"
            report += "\n".join(success_reports) + "\n"
            report += "\n".join(failure_reports)
            await conv.send_message(report)

        except Exception as e:
            await conv.send_message(f"🚫 **حدث خطأ أثناء تنفيذ العملية:** {str(e)}")


async def check_subscription_for_account(sender_id, account_index, conv, retry_count=3):
    session_str = user_accounts[sender_id]["sessions"][account_index]
    client = TelegramClient(StringSession(session_str), api_id, api_hash)
    await client.connect()

    try:
        for attempt in range(retry_count):
            try:
                # إرسال إخطار ببدء العملية
                await conv.send_message(f"⏳ **بدأ التحقق في الحساب رقم {account_index + 1}...**")

                # إرسال /start عشر مرات
                for i in range(10):
                    await client.send_message('@DamKombot', '/start')
                    await asyncio.sleep(3)  # انتظار 3 ثواني

                # الحصول على آخر رسالة من البوت
                messages = await client.get_messages('@DamKombot', limit=1)
                if messages and hasattr(messages[0], 'text'):
                    if "عليك الاشتراك بالقنوات" in messages[0].text:
                        buttons = messages[0].buttons
                        if buttons:
                            for button_row in buttons:
                                for button in button_row:
                                    if hasattr(button, 'text'):
                                        link = re.search(r'@(\w+)', button.text)
                                        if link:
                                            channel_username = link.group(0)
                                            try:
                                                await client(JoinChannelRequest(channel_username))
                                                await conv.send_message(f"✅ **الحساب رقم {account_index + 1} اشترك في قناة الإشتراك الاجباري {channel_username}.**")
                                                await asyncio.sleep(10)  # زيادة وقت الانتظار إلى 10 ثواني
                                            except FloodWaitError as e:
                                                await conv.send_message(f"⏳ **يلزم الانتظار {e.seconds} ثانية قبل المحاولة مرة أخرى.**")
                                                await asyncio.sleep(e.seconds)
                                                await client(JoinChannelRequest(channel_username))
                                            except Exception as e:
                                                await conv.send_message(f"❌ **حدث خطأ أثناء الاشتراك في القناة {channel_username}: {str(e)}**")
                        # إرسال /start مرة واحدة بعد الانتهاء من الاشتراك
                        await client.send_message('@DamKombot', '/start')
                        await asyncio.sleep(10)  # زيادة وقت الانتظار إلى 10 ثواني
                        return  # إنهاء العملية بعد الاشتراك

                    elif "مرحبا بك في بوت DomKom 👋" in messages[0].text:
                        await conv.send_message(f"✅ **الحساب رقم {account_index + 1}:** لا يوجد قنوات اشتراك إجباري.")
                        return  # إنهاء العملية إذا لم تكن هناك قنوات إجبارية

                # إذا لم يتم العثور على الرسالة المتوقعة، إعادة المحاولة
                if attempt < retry_count - 1:
                    await conv.send_message(f"⚠️ **الحساب رقم {account_index + 1}: إعادة المحاولة ({attempt + 1}/{retry_count})**")
                    await client.send_message('@DamKombot', '/start')  # إعادة إرسال /start
                    await asyncio.sleep(10)  # زيادة وقت الانتظار إلى 10 ثواني
                    continue
                else:
                    raise Exception("لم يتم العثور على الرسالة المتوقعة بعد عدة محاولات.")

            except Exception as e:
                if attempt < retry_count - 1:
                    await conv.send_message(f"⚠️ **الحساب رقم {account_index + 1}: إعادة المحاولة ({attempt + 1}/{retry_count}) بسبب: {str(e)}**")
                    await client.send_message('@DamKombot', '/start')  # إعادة إرسال /start
                    await asyncio.sleep(10)  # زيادة وقت الانتظار إلى 10 ثواني
                    continue
                else:
                    raise e  # رفع الخطأ إذا فشلت جميع المحاولات

    except Exception as e:
        raise e  # رفع الخطأ لتسجيله في التقرير

    finally:
        await client.disconnect()

def run_server():
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", 8000), handler) as httpd:
        print("Serving on port 8000")
        httpd.serve_forever()

# تشغيل الخادم في خيط جديد
server_thread = threading.Thread(target=run_server)
server_thread.start()	                

            
# تشغيل البوت
print("Bot is running...")
bot.run_until_disconnected()
   