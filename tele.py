import time
import telebot
import requests
import http.server
import socketserver
import threading
import os

# ضع هنا توكن البوت الخاص بك
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

CHANNEL_USERNAME = '@EREN_PYTHON'  # ضع هنا اسم المستخدم لقناتك

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

def check_subscription(chat_id):
    # التحقق من حالة الاشتراك في القناة
    chat_member = bot.get_chat_member(CHANNEL_USERNAME, chat_id)
    return chat_member.status in ['member', 'administrator', 'creator']

@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    if check_subscription(chat_id):
        # إذا كان المستخدم مشتركًا، أرسل رسالة الترحيب
        user_link = f"<a href='tg://user?id={message.from_user.id}'>{message.from_user.first_name}</a>"
        markup = telebot.types.InlineKeyboardMarkup()
        button = telebot.types.InlineKeyboardButton(text="⦗ WORLED EREN ⦘", url="https://t.me/ERENYA0")
        markup.add(button)
        
        bot.send_message(chat_id, 
                         f"↯︙اهلاً بك عزيزي ↫ ⦗{user_link}⦘\n"
                         f"↯︙في بوت رفع الصور.\n"
                         f"↯︙ارسل الصورة وسأرسل لك رابط لها.",
                         reply_markup=markup, parse_mode="HTML")
    else:
        # إذا لم يكن مشتركًا، أظهر رسالة الاشتراك
        send_subscription_prompt(chat_id)

def send_subscription_prompt(chat_id):
    # رسالة الاشتراك الإجباري
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("⦗ Python tools ⦘", url="https://t.me/EREN_PYTHON"))
    markup.add(telebot.types.InlineKeyboardButton("تحقق", callback_data='verify'))
    
    bot.send_message(chat_id, 
                     "عذرا عزيزي... يجب الإشتراك في قناة البوت الرسمية حتى تتمكن من إستخدام البوت...🙋‍♂\n"
                     "إشترك هنا ⏬⏬ ثم إضغط تحقق 👉", 
                     reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == 'verify')
def verify_subscription(call):
    chat_id = call.message.chat.id
    if check_subscription(chat_id):
        # إظهار رسالة تحقق منبثقة للمستخدم
        bot.answer_callback_query(call.id, "تم التحقق ✔️", show_alert=True)
        
        # حذف الرسالة الأصلية بعد التحقق
        bot.delete_message(chat_id, call.message.message_id)             
        
        # إرسال رسالة الترحيب بعد التحقق
        user_link = f"<a href='tg://user?id={call.from_user.id}'>{call.from_user.first_name}</a>"
        markup = telebot.types.InlineKeyboardMarkup()
        button = telebot.types.InlineKeyboardButton(text="⦗ WORLED EREN ⦘", url="https://t.me/ERENYA0")
        markup.add(button)
        
        bot.send_message(chat_id, 
                         f"↯︙اهلاً بك عزيزي ↫ ⦗{user_link}⦘\n"
                         f"↯︙في بوت رفع الصور.\n"
                         f"↯︙ارسل الصورة وسأرسل لك رابط لها.",
                         reply_markup=markup, parse_mode="HTML")
    else:
        # إظهار رسالة عدم الاشتراك للمستخدم في نافذة منبثقة
        bot.answer_callback_query(call.id, "عذراً، لم تشترك في القناة بعد.", show_alert=True)

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    chat_id = message.chat.id
    if check_subscription(chat_id):
        # إرسال الصورة مع زر "رفع الصورة" فقط للمشتركين
        markup = telebot.types.InlineKeyboardMarkup()
        upload_button = telebot.types.InlineKeyboardButton(text="• رفع الصورة •", callback_data="upload_image")
        markup.add(upload_button)
        
        # إرسال الصورة بدون جملة "جاري تحميل الصورة..."
        bot.send_photo(chat_id, message.photo[-1].file_id, reply_markup=markup)
    else:
        # إذا لم يكن المستخدم مشتركًا، أظهر رسالة الاشتراك
        send_subscription_prompt(chat_id)

@bot.callback_query_handler(func=lambda call: call.data == "upload_image")
def upload_image_callback(call):
    # تعديل اسم الزر إلى "جاري الرفع"
    markup = telebot.types.InlineKeyboardMarkup()
    uploading_button = telebot.types.InlineKeyboardButton(text="• جاري الرفع •", callback_data="uploading")
    markup.add(uploading_button)
    
    # تعديل الزر في نفس الرسالة فقط
    bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)

    # رفع الصورة إلى Catbox.moe
    file_info = bot.get_file(call.message.photo[-1].file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    
    # حفظ الصورة مؤقتاً
    with open("temp.jpg", "wb") as new_file:
        new_file.write(downloaded_file)

    # رفع الصورة إلى Catbox.moe
    with open("temp.jpg", "rb") as img_file:
        response = requests.post(
            "https://catbox.moe/user/api.php",
            data={"reqtype": "fileupload"},
            files={"fileToUpload": img_file}
        )
    
    # تحقق من نجاح الرفع
    if response.status_code == 200 and "https" in response.text:
        image_url = response.text
        
        # تعديل اسم الزر إلى "تم الإرسال"
        markup = telebot.types.InlineKeyboardMarkup()
        sent_button = telebot.types.InlineKeyboardButton(text="• تم الإرسال •", callback_data="sent")
        markup.add(sent_button)
        
        # تعديل الزر في نفس الرسالة فقط
        bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)

        # إرسال الرابط للمستخدم
        bot.send_message(call.message.chat.id, f"تم رفع الصورة بنجاح! الرابط: {image_url}")
    else:
        # في حالة حدوث خطأ أثناء الرفع
        bot.send_message(call.message.chat.id, "حدث خطأ أثناء رفع الصورة. حاول مرة أخرى لاحقًا.")
        
def run_server():
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", 8000), handler) as httpd:
        print("Serving on port 8000")
        httpd.serve_forever()

# تشغيل الخادم في خيط جديد
server_thread = threading.Thread(target=run_server)
server_thread.start()	                

# تكرار المحاولة في حال حدوث خطأ
while True:
    try:
        bot.polling()
    except Exception as e:
        print(f"حدث خطأ: {e}. إعادة تشغيل البوت...")
        time.sleep(5)  # الانتظار لمدة 5 ثوانٍ قبل إعادة التشغيل