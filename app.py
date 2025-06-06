from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import requests
from datetime import datetime
import pytz
import threading
import time

app = Flask(__name__)

DATABASE = 'crm.db'

# Telegram bot token va chat ID ni o'zingizning ma'lumotlaringizga almashtiring
TOKEN = '6730091039:AAGv2ADImmqtJsLBHbcpHYGcmHK9-FuILGE'
CHAT_ID = '6855997739'

# DB ni yaratish uchun funksiya
def init_db():
    with sqlite3.connect(DATABASE) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS applicants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone1 TEXT NOT NULL,
                phone2 TEXT,
                course TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                note TEXT,
                created_at TEXT,
                status_updated_at TEXT
            )
        """)

init_db()

# Telegramga xabar yuborish funksiyasi
def send_telegram_notification(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        response = requests.post(url, data={'chat_id': CHAT_ID, 'text': message})
        print("Telegram javobi:", response.text)
    except Exception as e:
        print("Telegramga xabar yuborishda xatolik:", e)

# Bosh sahifa - ro'yxatni ko'rsatadi
@app.route('/')
def index():
    with sqlite3.connect(DATABASE) as conn:
        applicants = conn.execute("SELECT * FROM applicants").fetchall()

    status_dict = {
        'pending': ('Kutmoqda', 'status-pending'),
        'accepted': ('Qabul qilindi', 'status-accepted'),
        'rejected': ('Rad etildi', 'status-rejected')
    }

    applicants_uz = []
    for a in applicants:
        a_list = list(a)
        uzbek_status, css_class = status_dict.get(a_list[5], (a_list[5], ''))
        a_list[5] = uzbek_status
        a_list.append(css_class)
        applicants_uz.append(a_list)

    return render_template('dashboard.html', applicants=applicants_uz)

# Yangi arizachi qo'shish
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        phone1 = request.form['phone1']
        phone2 = request.form.get('phone2', '')
        course = request.form['course']
        note = request.form['note']

        tz = pytz.timezone('Asia/Tashkent')
        now = datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')

        with sqlite3.connect(DATABASE) as conn:
            conn.execute(
                "INSERT INTO applicants (name, phone1, phone2, course, note, created_at, status_updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (name, phone1, phone2, course, note, now, now)
            )
        return redirect(url_for('index'))

    return render_template('register.html')

# Qabul qilish
@app.route('/accept/<int:id>')
def accept(id):
    tz = pytz.timezone('Asia/Tashkent')
    now = datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')

    with sqlite3.connect(DATABASE) as conn:
        conn.execute("UPDATE applicants SET status='accepted', status_updated_at=? WHERE id=?", (now, id))

    # Telegramga qabul qilindi haqida xabar (xohlasangiz)
    # applicant = conn.execute("SELECT name FROM applicants WHERE id=?", (id,)).fetchone()
    # if applicant:
    #     send_telegram_notification(f"{applicant[0]} qabul qilindi!")

    return redirect(url_for('index'))

# Rad etish
@app.route('/reject/<int:id>')
def reject(id):
    tz = pytz.timezone('Asia/Tashkent')
    now = datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')

    with sqlite3.connect(DATABASE) as conn:
        conn.execute("UPDATE applicants SET status='rejected', status_updated_at=? WHERE id=?", (now, id))

    return redirect(url_for('index'))

# O'chirish
@app.route('/delete/<int:id>')
def delete(id):
    with sqlite3.connect(DATABASE) as conn:
        conn.execute("DELETE FROM applicants WHERE id=?", (id,))

    return redirect(url_for('index'))

# Fonli ish: pending holatdagi arizalarni 30 soniyadan ortiq tekshirib Telegramga xabar yuboradi
def check_pending_applicants():
    tz = pytz.timezone('Asia/Tashkent')
    while True:
        now = datetime.now(tz)
        with sqlite3.connect(DATABASE) as conn:
            rows = conn.execute("SELECT id, name, phone1, course, status_updated_at FROM applicants WHERE status='pending'").fetchall()
            for row in rows:
                id, name, phone1, course, status_updated_at = row
                status_time_naive = datetime.strptime(status_updated_at, '%Y-%m-%d %H:%M:%S')
                status_time = tz.localize(status_time_naive)
                delta = now - status_time
                if delta.total_seconds() > 30:  # 30 soniya
                    message = (
                        f"🕒 30 soniya davomida o'quvchining statusi o'zgarmadi!\n"
                        f"Ismi: {name}\n"
                        f"Telefon: {phone1}\n"
                        f"Kurs: {course}\n"
                        f"❗ Guruhga joylashtiring!"
                    )
                    send_telegram_notification(message)
        time.sleep(10)

if __name__ == '__main__':
    # Fonli ishni threadda ishga tushuramiz
    thread = threading.Thread(target=check_pending_applicants, daemon=True)
    thread.start()
    # Appni 0.0.0.0:8080 portda ishga tushuramiz
    app.run(host='0.0.0.0', port=8080)
