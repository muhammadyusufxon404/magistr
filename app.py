from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import requests
from datetime import datetime
import pytz
import threading
import time

app = Flask(__name__)
DATABASE = 'crm.db'
TOKEN = '6730091039:AAH-XJ7CyjOGOSkFDYMbAuifpsREMLm2zd8'
CHAT_ID = '6855997739'

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

def send_telegram_notification(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, data={'chat_id': CHAT_ID, 'text': message})
    except Exception as e:
        print("Telegramga xabar yuborishda xatolik:", e)

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
        # Yangi o'quvchi qo'shilganda adminga xabar yuborilmaydi
        return redirect(url_for('index'))
    return render_template('register.html')

@app.route('/accept/<int:id>')
def accept(id):
    tz = pytz.timezone('Asia/Tashkent')
    now = datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')
    with sqlite3.connect(DATABASE) as conn:
        conn.execute("UPDATE applicants SET status='accepted', status_updated_at=? WHERE id=?", (now, id))
    # Qabul qilinganda adminga xabar yuborilmaydi
    return redirect(url_for('index'))

@app.route('/reject/<int:id>')
def reject(id):
    tz = pytz.timezone('Asia/Tashkent')
    now = datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')
    with sqlite3.connect(DATABASE) as conn:
        conn.execute("UPDATE applicants SET status='rejected', status_updated_at=? WHERE id=?", (now, id))
    # Rad etilganda adminga xabar yuborilmaydi
    return redirect(url_for('index'))

@app.route('/delete/<int:id>')
def delete(id):
    with sqlite3.connect(DATABASE) as conn:
        conn.execute("DELETE FROM applicants WHERE id=?", (id,))
    # O'chirilganda ham adminga xabar yuborilmaydi
    return redirect(url_for('index'))

def check_pending_applicants():
    tz = pytz.timezone('Asia/Tashkent')
    while True:
        now = datetime.now(tz)
        with sqlite3.connect(DATABASE) as conn:
            rows = conn.execute("SELECT id, name, phone1, course, status, status_updated_at FROM applicants WHERE status='pending'").fetchall()
            for row in rows:
                id, name, phone1, course, status, status_updated_at = row
                status_time_naive = datetime.strptime(status_updated_at, '%Y-%m-%d %H:%M:%S')
                status_time = tz.localize(status_time_naive)
                delta = now - status_time
                if delta.total_seconds() > 30:  # 30 soniya test uchun
                    message = (
                        f"🕒 30 soniya davomida o'quvchining statusi o'zgarmadi!\n"
                        f"Ismi: {name}\n"
                        f"Telefon: {phone1}\n"
                        f"Kurs: {course}\n"
                        f"❗ Guruhga joylashtiring!"
                    )
                    send_telegram_notification(message)
        time.sleep(10)  # Har 10 soniyada tekshiradi

if __name__ == '__main__':
    thread = threading.Thread(target=check_pending_applicants, daemon=True)
    thread.start()
    app.run(debug=True)
