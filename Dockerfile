# استخدم صورة Python الرسمية كصورة أساسية
FROM python:3.9-slim

# تعيين دليل العمل داخل الحاوية
WORKDIR /app

# نسخ ملف requirements.txt إلى دليل العمل
COPY requirements.txt .

# تثبيت الحزم المطلوبة
RUN pip install --no-cache-dir -r requirements.txt

# نسخ ملف السكربت إلى دليل العمل
COPY bot.py .

# تعيين الأمر الافتراضي لتشغيل السكربت
CMD ["python", "bot.py"]
