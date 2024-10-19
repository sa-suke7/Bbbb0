import telebot
from youtube_search import YoutubeSearch
import requests
import os
import yt_dlp
import http.server
import socketserver
import threading

API_TOKEN = '7512265911:AAGGHa_stp4gHj8PCs-yj7gwjTFAguPby7A'
bot = telebot.TeleBot(API_TOKEN)

# تخزين النتائج للمستخدمين
bot.results = {}
bot.users = set()

developer_id = 5683930416  # ID المطور

# بدء البوت
@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    user_info = message.from_user
    user_username = f"@{user_info.username}" if user_info.username else "غير متوفر"
    
    # رسالة ترحيبية للمطور
    if chat_id == developer_id:
        markup = telebot.types.InlineKeyboardMarkup()
        broadcast_button = telebot.types.InlineKeyboardButton("إرسال رسالة", callback_data="broadcast")
        markup.add(broadcast_button)
        bot.send_message(chat_id, "<b>• مرحبا بك في بوت البحث عن الفيديوهات</b>", reply_markup=markup, parse_mode='HTML')
    else:
        # رسالة ترحيبية للمستخدمين
        welcome_message = (
            f"مرحبا بك {user_username} \n"
            f"استخدم بوت البحث عن يوتيوب.\n"
            "استمتع!"
        )
        markup = telebot.types.InlineKeyboardMarkup()
        world_eren_button = telebot.types.InlineKeyboardButton("WORLD EREN", url="https://t.me/ERENYA0")
        markup.add(world_eren_button)
        
        bot.send_message(chat_id, welcome_message, reply_markup=markup, parse_mode='HTML')

    # تسجيل المستخدمين
    if chat_id not in bot.users:
        bot.users.add(chat_id)
        user_name = user_info.first_name
        user_id = user_info.id
        total_users = len(bot.users)

        # إعلام المطور بتسجيل مستخدم جديد
        bot.send_message(developer_id, f"مستخدم جديد:\n"
        f"• الاسم: <code>{user_name}</code>\n"
        f"• معرف المستخدم: {user_username}\n"
        f"• ID: <code>{user_id}</code>\n"
        f"• العدد الكلي للمستخدمين: {total_users}", parse_mode='HTML')

# البحث عن الفيديوهات
@bot.message_handler(func=lambda message: True)
def search_song(message):
    search_term = message.text
    markup = telebot.types.InlineKeyboardMarkup()
    search_button = telebot.types.InlineKeyboardButton("بحث", callback_data=f"search_{search_term}")
    markup.add(search_button)

    bot.send_message(message.chat.id, f"جاري البحث عن: <code>{search_term}</code>", reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data.startswith("search_"))
def handle_search(call):
    search_term = call.data.split("_")[1]
    bot.delete_message(call.message.chat.id, call.message.message_id)
    
    searching_msg = bot.send_message(call.message.chat.id, f"<b>جاري البحث عن:</b> <code>{search_term}</code>...", parse_mode='HTML')

    results = YoutubeSearch(search_term, max_results=5).to_dict()
    markup = telebot.types.InlineKeyboardMarkup()

    for idx, result in enumerate(results):
        title = result['title']
        button = telebot.types.InlineKeyboardButton(title, callback_data=f"video_{idx}")
        markup.add(button)

    bot.results[call.message.chat.id] = results
    sent_msg = bot.send_message(call.message.chat.id, f"<b>نتائج البحث عن:</b> <code>{search_term}</code>", reply_markup=markup, parse_mode='HTML')
    
    bot.delete_message(call.message.chat.id, searching_msg.message_id)
    bot.results[f'message_{call.message.chat.id}'] = sent_msg.message_id

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
    btn_audio = telebot.types.InlineKeyboardButton("تحميل صوت", callback_data=f"audio_{index}")
    btn_voice = telebot.types.InlineKeyboardButton("تحميل صوت مع التعليق", callback_data=f"voice_{index}")
    btn_back = telebot.types.InlineKeyboardButton("العودة للنتائج", callback_data=f"back_to_results")
    markup.add(btn_audio, btn_voice)
    markup.add(btn_back)

    with open(thumbnail_filename, 'rb') as thumb:
        sent_msg = bot.send_photo(chat_id, thumb, caption="<b>اختر تحميل الفيديو</b>", reply_markup=markup, parse_mode='HTML')

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
    
    # استخدام ملف الكوكيز
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
        loading_msg = bot.send_message(chat_id, "<b>جاري التحميل...</b>", parse_mode='HTML')

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])

        thumbnail_response = requests.get(video_thumbnail)
        thumbnail_filename = f"{chat_id}_voice_thumbnail.jpg"
        with open(thumbnail_filename, 'wb') as file:
            file.write(thumbnail_response.content)

        caption = f"تحميل: {video_data['title']}"
        if call.data.startswith("audio_"):
            send_audio_via_requests(chat_id, output_filename, caption, thumbnail_filename)
        elif call.data.startswith("voice_"):
            send_voice_via_requests(chat_id, output_filename, caption)

        os.remove(output_filename)
        os.remove(thumbnail_filename)
        bot.delete_message(chat_id, loading_msg.message_id)

    except Exception as e:
        bot.send_message(chat_id, f"<b>حدث خطأ أثناء التحميل:</b> <code>{str(e)}</code>", parse_mode='HTML')

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
        
        sent_msg = bot.send_message(chat_id, "<b>الرجاء اختيار فيديو:</b>", reply_markup=markup, parse_mode='HTML')
        bot.results[f'message_{chat_id}'] = sent_msg.message_id

# تشغيل الخادم المحلي على المنفذ 8000
def run_server():
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", 8000), handler) as httpd:
        print("Serving on port 8000")
        httpd.serve_forever()

# بدء الخادم في خيط منفصل
server_thread = threading.Thread(target=run_server)
server_thread.start()

while True:
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        print(f"Error occurred: {e}")
        continue
