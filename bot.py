import os
import logging
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from textblob import TextBlob

# جلب التوكن من المتغير البيئي
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

if TOKEN is None:
    raise ValueError("الرجاء تعيين التوكن كمتحول بيئي باسم 'TELEGRAM_BOT_TOKEN'.")

# إعداد نظام التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# وظيفة /start
def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('مرحبًا! أنا بوت التدقيق اللغوي. أرسل لي أي نص وسأقوم بمراجعته من أجلك.')

# وظيفة /help
def help_command(update: Update, context: CallbackContext) -> None:
    help_text = (
        "/start - لبدء المحادثة معي\n"
        "/help - لعرض هذه الرسالة\n"
        "ما عليك سوى إرسال أي نص وسأقوم بتدقيقه لغويًا!"
    )
    update.message.reply_text(help_text)

# وظيفة التدقيق اللغوي
def check_text(update: Update, context: CallbackContext) -> None:
    text = update.message.text
    blob = TextBlob(text)
    corrected_text = blob.correct()

    if text != str(corrected_text):
        response = f"النص بعد التدقيق:\n{corrected_text}"
    else:
        response = "النص الذي أرسلته يبدو صحيحًا من الناحية اللغوية!"

    # تدوين الأخطاء في ملف نصي
    with open("errors_log.txt", "a", encoding="utf-8") as log_file:
        if text != str(corrected_text):
            log_file.write(f"Original: {text}\nCorrected: {corrected_text}\n\n")
        else:
            log_file.write(f"Original: {text} (No errors found)\n\n")

    update.message.reply_text(response)

# معالجة الأخطاء
def error(update: Update, context: CallbackContext) -> None:
    logger.warning(f'Update "{update}" caused error "{context.error}"')

def main() -> None:
    # إعداد الـ Updater واستخدام التوكن
    updater = Updater(TOKEN)

    # الحصول على الـ Dispatcher لتسجيل الـ Handlers
    dispatcher = updater.dispatcher

    # إضافة الـ Handlers للأوامر
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))

    # إضافة Handler للرسائل النصية التي تحتوي على نصوص
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, check_text))

    # تسجيل معالجة الأخطاء
    dispatcher.add_error_handler(error)

    # بدء البوت
    updater.start_polling()

    # إيقاف البوت عند الحاجة
    updater.idle()

if __name__ == '__main__':
    main()
