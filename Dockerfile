# استخدام صورة Python رسمية
FROM python:3.9-slim

# تعيين دليل العمل
WORKDIR /app

# نسخ ملفات المتطلبات إلى داخل الصورة
COPY requirements.txt .

# تثبيت المتطلبات
RUN pip install --no-cache-dir -r requirements.txt

# نسخ كود البوت إلى داخل الصورة
COPY bot.py .

# تعيين متغير البيئة (يمكنك تعيينه عند التشغيل أيضًا)
ENV TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# تشغيل البوت عند بدء تشغيل الحاوية
CMD ["python", "bot.py"]

