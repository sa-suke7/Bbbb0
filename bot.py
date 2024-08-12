import os
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from googletrans import Translator

# قراءة التوكن من متغير بيئة
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# إعداد المترجم
translator = Translator()

def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('أرسل النص الذي تريد ترجمته متبوعًا بلغة الترجمة، مثل "Hello|ar" (ترجم "Hello" إلى العربية).')

def translate(update: Update, context: CallbackContext) -> None:
    # الحصول على النص من الرسالة
    text = update.message.text
    
    # التحقق من وجود " | " للفصل بين النص واللغة
    if '|' in text:
        text_to_translate, target_language = text.split('|', 1)
        
        # محاولة ترجمة النص
        try:
            translated = translator.translate(text_to_translate, dest=target_language)
            update.message.reply_text(f'الترجمة إلى {target_language}: {translated.text}')
        except Exception as e:
            update.message.reply_text(f'حدث خطأ: {e}')
    else:
        update.message.reply_text('الرجاء استخدام الصيغة الصحيحة: "النص|لغة"')

def main() -> None:
    # إعداد Updater وربطه بالتوكن
    updater = Updater(TOKEN)

    # الحصول على موزع الرسائل لتسجيل المعالجات
    dispatcher = updater.dispatcher

    # إضافة معالج لأمر /start
    dispatcher.add_handler(CommandHandler("start", start))

    # إضافة معالج للترجمة
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, translate))

    # بدء تشغيل البوت
    updater.start_polling()

    # تشغيل البوت حتى يتم إيقافه
    updater.idle()

if __name__ == '__main__':
    main()
