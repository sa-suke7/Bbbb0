import os
import telebot
from youtube_search import YoutubeSearch
import requests
import yt_dlp
import http.server
import socketserver
import threading
import logging
import time

# إعداد السجلات
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# جلب توكن البوت من المتغيرات البيئية
API_TOKEN = os.getenv('API_TOKEN')

bot = telebot.TeleBot(API_TOKEN)

# تخزين نتائج البحث مؤقتاً
bot.results = {}
bot.users = set()
developer_id = 5683930416  # ID المطور

# عند بداية البوت
@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    user_info = message.from_user
    user_username = f"@{user_info.username}" if user_info.username else "لا يوجد"
    
    if chat_id == developer_id:
        markup = telebot.types.InlineKeyboardMarkup()
        broadcast_button = telebot.types.InlineKeyboardButton("إذاعة 📢", callback_data="broadcast")
        markup.add(broadcast_button)
        bot.send_message(chat_id, "<b>• مرحبا عزيزي المطور يمكنك في أوامر البوت الخاص بك عن طريق الأزرار التالية 🦾</b>", reply_markup=markup, parse_mode='HTML')
    else:
        welcome_message = (
            f"↯︙أهلاً بك عزيزي {user_username} ↫\n"
            f"↯︙في بوت Youtube Search.\n"
            "↯︙أرسل ما تريد البحث عنه."
        )
        markup = telebot.types.InlineKeyboardMarkup()
        world_eren_button = telebot.types.InlineKeyboardButton("⦗ WORLD EREN ⦘", url="https://t.me/ERENYA0")
        markup.add(world_eren_button)
        
        bot.send_message(chat_id, welcome_message, reply_markup=markup, parse_mode='HTML')

    if chat_id not in bot.users:
        bot.users.add(chat_id)
        user_name = user_info.first_name
        user_id = user_info.id
        total_users = len(bot.users)
        bot.send_message(developer_id, f"٭ تم دخول شخص جديد إلى البوت الخاص بك 👾\n"
        "-----------------------\n"
        f"• الاسم : <code>{user_name}</code>\n"
        f"• المعرف : {user_username}\n"
        f"• الايدي : <code>{user_id}</code>\n"
        "-----------------------\n"
        f"• عدد الأعضاء الكلي : {total_users}", parse_mode='HTML')

# البحث عن الفيديوهات
@bot.message_handler(func=lambda message: True)
def search_song(message):
    search_term = message.text
    markup = telebot.types.InlineKeyboardMarkup()
    search_button = telebot.types.InlineKeyboardButton("ابحث 🔦", callback_data=f"search_{search_term}")
    markup.add(search_button)

    bot.send_message(message.chat.id, f"اضغط \"ابحث 🔦\" للبحث عن:\n⏺: <code>{search_term}</code>", reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data.startswith("search_"))
def handle_search(call):
    search_term = call.data.split("_")[1]
    bot.delete_message(call.message.chat.id, call.message.message_id)
    
    searching_msg = bot.send_message(call.message.chat.id, f"<b>جاري البحث عن:</b> <code>{search_term}</code>...", parse_mode='HTML')
    
    # تشغيل البحث في خيط منفصل
    search_thread = threading.Thread(target=perform_search, args=(call, search_term, searching_msg))
    search_thread.start()

def perform_search(call, search_term, searching_msg):
    try:
        results = YoutubeSearch(search_term, max_results=5).to_dict()
        markup = telebot.types.InlineKeyboardMarkup()

        for idx, result in enumerate(results):
            title = result['title']
            button = telebot.types.InlineKeyboardButton(title, callback_data=f"video_{idx}")
            markup.add(button)

        bot.results[call.message.chat.id] = results
        sent_msg = bot.send_message(call.message.chat.id, f"<b>تم البحث عن:</b> <code>{search_term}</code> 🔦", reply_markup=markup, parse_mode='HTML')
        
        bot.delete_message(call.message.chat.id, searching_msg.message_id)
        bot.results[f'message_{call.message.chat.id}'] = sent_msg.message_id
    
    except Exception as e:
        logging.error(f"خطأ أثناء البحث: {str(e)}")
        bot.send_message(call.message.chat.id, f"<b>حدث خطأ أثناء البحث:</b> <code>{str(e)}</code>", parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data.startswith("video_"))
def handle_video_choice(call):
    index = int(call.data.split("_")[1])
    chat_id = call.message.chat.id
    video_data = bot.results[chat_id][index]
    video_url = f"https://www.youtube.com{video_data['url_suffix']}"
    video_thumbnail = video_data['thumbnails'][0]

    if f'message_{chat_id}' in bot.results:
        bot.delete_message(chat_id, bot.results[f'message_{chat_id}'])

    thumbnail_response = requests.get(video_thumbnail)
    thumbnail_filename = f"{chat_id}_thumbnail.jpg"
    with open(thumbnail_filename, 'wb') as file:
        file.write(thumbnail_response.content)

    markup = telebot.types.InlineKeyboardMarkup()
    btn_audio = telebot.types.InlineKeyboardButton("ملف صوتي 🎵", callback_data=f"audio_{index}")
    btn_voice = telebot.types.InlineKeyboardButton("تسجيل صوتي 🎤", callback_data=f"voice_{index}")
    btn_back = telebot.types.InlineKeyboardButton("عودة ↩️", callback_data=f"back_to_results")
    markup.add(btn_audio, btn_voice)
    markup.add(btn_back)

    with open(thumbnail_filename, 'rb') as thumb:
        sent_msg = bot.send_photo(chat_id, thumb, caption="<b>كيف تريد تحميل المقطع؟</b>", reply_markup=markup, parse_mode='HTML')

    bot.results[f'message_{chat_id}'] = sent_msg.message_id

@bot.callback_query_handler(func=lambda call: call.data.startswith(("audio_", "voice_")))
def handle_download_choice(call):
    index = int(call.data.split("_")[1])
    chat_id = call.message.chat.id
    video_data = bot.results[chat_id][index]
    video_url = f"https://www.youtube.com{video_data['url_suffix']}"
    video_title = video_data['title'].replace("|", "-").replace(" ", "_")
    video_thumbnail = video_data['thumbnails'][0]

    if f'message_{chat_id}' in bot.results:
        bot.delete_message(chat_id, bot.results[f'message_{chat_id}'])

    output_filename = f"{video_title}.mp3"

    # تحديد الحد الأقصى لحجم الملف (50 ميجا)
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 ميجا بايت
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'extractaudio': True,
        'audioformat': 'mp3',
        'outtmpl': output_filename,
        'quiet': True,
        'cookiefile': 'cookies.txt',  # استخدام ملف الكوكيز
    }

    try:
        loading_msg = bot.send_message(chat_id, "<b>جاري تحميل المقطع...</b>", parse_mode='HTML')

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            file_size = info.get('filesize', 0)

            if file_size and file_size > MAX_FILE_SIZE:
                bot.send_message(chat_id, f"<b>عذراً، حجم الملف يتجاوز 50 ميجا ولا يمكن تحميله.</b>", parse_mode='HTML')
                bot.delete_message(chat_id, loading_msg.message_id)
                return

            ydl.download([video_url])

        thumbnail_response = requests.get(video_thumbnail)
        thumbnail_filename = f"{chat_id}_voice_thumbnail.jpg"
        with open(thumbnail_filename, 'wb') as file:
            file.write(thumbnail_response.content)

        caption = f"⌔╎البحث: {video_data['title']}"
        if call.data.startswith("audio_"):
            send_audio_via_requests(chat_id, output_filename, caption, thumbnail_filename)
        elif call.data.startswith("voice_"):
            send_voice_via_requests(chat_id, output_filename, caption)

        os.remove(output_filename)
        os.remove(thumbnail_filename)
        bot.delete_message(chat_id, loading_msg.message_id)

    except Exception as e:
        logging.error(f"خطأ أثناء تحميل المقطع: {str(e)}")
        bot.send_message(chat_id, f"<b>حدث خطأ أثناء تحميل المقطع:</b> <code>{str(e)}</code>", parse_mode='HTML')

def send_audio_via_requests(chat_id, audio_file, caption, thumbnail_file):
    url = f"https://api.telegram.org/bot{API_TOKEN}/sendAudio"
    with open(audio_file, 'rb') as file_data, open(thumbnail_file, 'rb') as thumb_data:
        response = requests.post(url, data={'chat_id': chat_id, 'caption': caption}, 
                                 files={'audio': file_data, 'thumb': thumb_data})
    return response.json()

def send_voice_via_requests(chat_id, voice_file, caption):
    url = f"https://api.telegram.org/bot{API_TOKEN}/sendVoice"
    with open(voice_file, 'rb') as file_data:
        response = requests.post(url, data={'chat_id': chat_id, 'caption': caption}, 
                                 files={'voice': file_data})
    return response.json()

@bot.callback_query_handler(func=lambda call: call.data == "back_to_results")
def return_to_results(call):
    chat_id = call.message.chat.id
    if f'message_{chat_id}' in bot.results:
        bot.delete_message(chat_id, bot.results[f'message_{chat_id}'])
    
    results = bot.results.get(chat_id)
    if results:
        markup = telebot.types.InlineKeyboardMarkup()
        for idx, result in enumerate(results):
            title = result['title']
            button = telebot.types.InlineKeyboardButton(title, callback_data=f"video_{idx}")
            markup.add(button)
        
        sent_msg = bot.send_message(chat_id, "<b>اختر المقطع:</b>", reply_markup=markup, parse_mode='HTML')
        bot.results[f'message_{chat_id}'] = sent_msg.message_id

# تشغيل الخادم مع دعم الخيوط المتعددة
class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass

def run_server():
    handler = http.server.SimpleHTTPRequestHandler
    with ThreadedTCPServer(("", 8000), handler) as httpd:
        logging.info("Serving on port 8000")
        httpd.serve_forever()

# تشغيل الخادم في خيط جديد
server_thread = threading.Thread(target=run_server)
server_thread.start()

# استمرارية تشغيل البوت مع معالجة الأخطاء
def start_bot():
    while True:
        try:
            bot.polling(none_stop=True)
        except Exception as e:
            logging.error(f"خطأ غير متوقع: {str(e)}")
            time.sleep(5)  # الانتظار قليلاً قبل إعادة التشغيل

# بدء البوت
start_bot()