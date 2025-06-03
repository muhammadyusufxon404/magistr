import sqlite3
import requests
from datetime import datetime, timedelta
import pytz
import time

DATABASE = 'crm.db'
TOKEN = '6730091039:AAH-XJ7CyjOGOSkFDYMbAuifpsREMLm2zd8'
CHAT_ID = '6855997739'

def send_telegram_notification(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    resp = requests.post(url, data={'chat_id': CHAT_ID, 'text': message})
    return resp.ok

def check_status_updates():
    tz = pytz.timezone('Asia/Tashkent')
    now = datetime.now(tz)
    limit_time = now - timedelta(minutes=3)  # 3 minut oldingi vaqt (test uchun)

    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        # status_updated_at datetime formatda saqlangan deb faraz qilamiz
        cursor.execute("SELECT id, name, phone1, course, status, status_updated_at FROM applicants WHERE status_updated_at IS NOT NULL")
        rows = cursor.fetchall()

        for row in rows:
            id_, name, phone1, course, status, status_updated_at_str = row
            status_updated_at = datetime.strptime(status_updated_at_str, '%Y-%m-%d %H:%M:%S')
            status_updated_at = tz.localize(status_updated_at)

            # Agar 3 minutdan oshgan bo'lsa va hali xabar yuborilmagan bo'lsa (oddiy tekshiruv)
            if status_updated_at < limit_time:
                msg = (
                    f"O'quvchi statusi 3 minut ichida o'zgarmadi:\n"
                    f"ID: {id_}\n"
                    f"Ismi: {name}\n"
                    f"Telefon: {phone1}\n"
                    f"Kurs: {course}\n"
                    f"Status: {status}\n\n"
                    f"Guruhga joylashtiring!"
                )
                send_telegram_notification(msg)

if __name__ == '__main__':
    while True:
        check_status_updates()
        time.sleep(60)  # har 1 daqiqada tekshiradi
