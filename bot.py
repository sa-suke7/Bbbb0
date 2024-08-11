import requests
import time
import uuid
import random
import telebot
import threading
from flask import Flask

# الثوابت
telegram_bot_token = '7168692937:AAEkUQl949WySy4aPoIDI3q06xmUGDRJJY4'
delay = 30  # وقت الانتظار بين كل عملية جمع للكود (بالثواني)

# الألعاب المتاحة
games = {
    1: {
        'name': 'Riding Extreme 3D',
        'appToken': 'd28721be-fd2d-4b45-869e-9f253b554e50',
        'promoId': '43e35910-c168-4634-ad4f-52fd764a843f',
    },
    2: {
        'name': 'Chain Cube 2048',
        'appToken': 'd1690a07-3780-4068-810f-9b5bbf2931b2',
        'promoId': 'b4170868-cef0-424f-8eb9-be0622e8e8e3',
    },
    3: {
        'name': 'My Clone Army',
        'appToken': '74ee0b5b-775e-4bee-974f-63e7f4d5bacb',
        'promoId': 'fe693b26-b342-4159-8808-15e3ff7f8767',
    },
    4: {
        'name': 'Train Miner',
        'appToken': '82647f43-3f87-402d-88dd-09a90025313f',
        'promoId': 'c4480ac7-e178-4973-8061-9ed5b2e17954',
    }
}

bot = telebot.TeleBot(telegram_bot_token)

# تخزين معرفات الدردشة لكل مستخدم طلب الأكواد
user_chat_ids = {}
running = {}  # تعريف متغير running
selected_game = {}  # تخزين اللعبة المختارة لكل مستخدم

app = Flask(__name__)

def generate_client_id():
    timestamp = int(time.time() * 1000)
    random_numbers = ''.join(str(random.randint(0, 9)) for _ in range(19))
    return f"{timestamp}-{random_numbers}"

def login_client(game):
    client_id = generate_client_id()
    try:
        response = requests.post('https://api.gamepromo.io/promo/login-client', json={
            'appToken': game['appToken'],
            'clientId': client_id,
            'clientOrigin': 'deviceid'
        }, headers={
            'Content-Type': 'application/json; charset=utf-8',
        })
        response.raise_for_status()
        return response.json().get('clientToken')
    except requests.RequestException as error:
        print('خطأ في تسجيل دخول العميل:', error)
        time.sleep(5)
        return login_client(game)  # استدعاء ذاتي في حالة الخطأ

def register_event(game, token):
    event_id = str(uuid.uuid4())
    try:
        response = requests.post('https://api.gamepromo.io/promo/register-event', json={
            'promoId': game['promoId'],
            'eventId': event_id,
            'eventOrigin': 'undefined'
        }, headers={
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json; charset=utf-8',
        })
        response.raise_for_status()
        
        if not response.json().get('hasCode'):
            time.sleep(5)
            return register_event(game, token)  # استدعاء ذاتي في حالة عدم وجود كود
        else:
            return True
    except requests.RequestException as error:
        time.sleep(5)
        return register_event(game, token)  # استدعاء ذاتي في حالة الخطأ

def create_code(game, token):
    while True:
        try:
            response = requests.post('https://api.gamepromo.io/promo/create-code', json={
                'promoId': game['promoId']
            }, headers={
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json; charset=utf-8',
            })
            response.raise_for_status()
            promo_code = response.json().get('promoCode')
            if promo_code:
                return promo_code
        except requests.RequestException as error:
            print('خطأ في إنشاء الكود:', error)
            time.sleep(1)

def send_code_to_telegram(chat_id, game, codes):
    url = f'https://api.telegram.org/bot{telegram_bot_token}/sendMessage'
    payload = {
        'chat_id': chat_id,
        'text': f"أسم اللعبة: {game['name']}\n\n" + '\n'.join(codes),  # إرسال الأكواد كرسالة واحدة مفصولة بأسطر جديدة
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print(f'تم إرسال الأكواد إلى {chat_id} بنجاح:', response.json())  # طباعة الاستجابة
    except requests.RequestException as error:
        print('خطأ في إرسال الأكواد إلى تيليجرام:', error)
        if error.response:
            print('تفاصيل الاستجابة:', error.response.text)

def gen(chat_id, game):
    token = login_client(game)
    if register_event(game, token):
        codes = set()  # استخدام مجموعة لتخزين الأكواد الفريدة
        for _ in range(4):
            code = create_code(game, token)
            if code:
                codes.add(code)
            else:
                print("فشل في جمع كود")
        if codes:
            send_code_to_telegram(chat_id, game, list(codes))  # إرسال الأكواد إلى مستخدم معين
        else:
            print("لم يتم جمع أي أكواد")

def handle_telegram_command(message):
    chat_id = message.chat.id
    if message.text == '/start':
        user = message.from_user.first_name
        bot.reply_to(message, f"أهلا بك {user} في بوت Key codes يمكنك لرؤية الأوامر:\n\nأرسل /help")
    elif message.text == '/help':
        bot.reply_to(message, ("دليل التشغيل :\n"
                               "لبدء التجميع ارسل : /promo\n"
                               "لإيقاف التشغيل ارسل : /stop\n"
                               "لاختيار اللعبة أرسل : /game [رقم اللعبة]\n"
                               "الألعاب المتاحة:\n"
                               "1. Riding Extreme 3D\n"
                               "2. Chain Cube 2048\n"
                               "3. My Clone Army\n"
                               "4. Train Miner\n"
                               "للتواصل مع مطوري : @sens_7i0bot\n"
                               "ملاحظات : \n"
                               "البوت يقوم بتجميع كود كل دقيقتين لذلك انتظر"))
    elif message.text.startswith('/game'):
        try:
            game_id = int(message.text.split()[1])
            if game_id in games:
                selected_game[chat_id] = games[game_id]
                bot.reply_to(message, f"تم اختيار اللعبة: {games[game_id]['name']}")
            else:
                bot.reply_to(message, "رقم اللعبة غير صحيح، الرجاء اختيار رقم صحيح.")
        except (IndexError, ValueError):
            bot.reply_to(message, "الرجاء إدخال رقم اللعبة بشكل صحيح. مثال: /game 1")
    elif message.text == '/promo':
        if chat_id in running and running[chat_id]:
            bot.reply_to(message, "التجميع قيد التشغيل بالفعل.")
        elif chat_id not in selected_game:
            bot.reply_to(message, "الرجاء اختيار لعبة أولاً باستخدام الأمر /game")
        else:
            user_chat_ids[chat_id] = chat_id
            running[chat_id] = True
            bot.reply_to(message, "بدء جمع الأكواد")
            def promo_thread():
                while running.get(chat_id):
                    threads = [threading.Thread(target=gen, args=(chat_id, selected_game[chat_id])) for _ in range(4)]
                    for thread in threads:
                        thread.start()
                    for thread in threads:
                        thread.join()
                    time.sleep(delay)  # وقت الانتظار بين التجميعات
            threading.Thread(target=promo_thread).start()
    elif message.text == '/stop':
        if chat_id in running and running[chat_id]:
            running[chat_id] = False
            bot.reply_to(message, "تم إيقاف جمع الأكواد")
        else:
            bot.reply_to(message, "التجميع موقوف بالفعل.")

@app.route('/')
def health_check():
    return "Bot is running!"

def start_flask_app():
    app.run(host='0.0.0.0', port=8000)

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    handle_telegram_command(message)

if __name__ == '__main__':
    # تشغيل خادم Flask في خيط منفصل
    flask_thread = threading.Thread(target=start_flask_app)
    flask_thread.start()

    # تشغيل بوت Telegram
    bot.polling()
