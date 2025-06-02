from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import requests
from datetime import datetime, timedelta
import pytz
import threading
import time

app = Flask(__name__)
DATABASE = 'crm.db'
TOKEN = '6730091039:AAH-XJ7CyjOGOSkFDYMbAuifpsREMLm2zd8'  # Telegram Bot Token
CHAT_ID = '6855997739'  # Admin Telegram chat ID

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
                updated_at TEXT
            )
        """)

init_db()

def send_telegram_notification(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={'chat_id': CHAT_ID, 'text': message})

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
        now_str = datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')

        with sqlite3.connect(DATABASE) as conn:
            conn.execute(
                "INSERT INTO applicants (name, phone1, phone2, course, note, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (name, phone1, phone2, course, note, now_str, now_str)
            )
        # Eslatma: ro'yxatdan o'tishda adminga xabar yuborilmasin (so‘rov bo‘yicha)
        return redirect(url_for('index'))
    return render_template('register.html')

@app.route('/accept/<int:id>')
def accept(id):
    tz = pytz.timezone('Asia/Tashkent')
    now_str = datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')
    with sqlite3.connect(DATABASE) as conn:
        conn.execute("UPDATE applicants SET status='accepted', updated_at=? WHERE id=?", (now_str, id))
        row = conn.execute("SELECT name, course FROM applicants WHERE id=?", (id,)).fetchone()
    # Adminga xabar yubilmaydi, shart bo‘lsa o‘zgartiring
    return redirect(url_for('index'))

@app.route('/reject/<int:id>')
def reject(id):
    tz = pytz.timezone('Asia/Tashkent')
    now_str = datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')
    with sqlite3.connect(DATABASE) as conn:
        conn.execute("UPDATE applicants SET status='rejected', updated_at=? WHERE id=?", (now_str, id))
        row = conn.execute("SELECT name, course FROM applicants WHERE id=?", (id,)).fetchone()
    # Adminga xabar yuborilmaydi
    return redirect(url_for('index'))

@app.route('/delete/<int:id>')
def delete(id):
    with sqlite3.connect(DATABASE) as conn:
        conn.execute("DELETE FROM applicants WHERE id=?", (id,))
    # Adminga xabar yuborilmaydi
    return redirect(url_for('index'))

def check_inactive_applicants():
    tz = pytz.timezone('Asia/Tashkent')
    now = datetime.now(tz)
    three_minutes_ago = now - timedelta(minutes=3)

    with sqlite3.connect(DATABASE) as conn:
        rows = conn.execute(
            "SELECT id, name, phone1, phone2, course, updated_at FROM applicants WHERE status='pending'"
        ).fetchall()

    for r in rows:
        updated_at = datetime.strptime(r[5], '%Y-%m-%d %H:%M:%S')
        if updated_at < three_minutes_ago:
            message = (
                f"O‘quvchini guruhga joylashtiring:\n"
                f"Ism: {r[1]}\nTelefon 1: {r[2]}\nTelefon 2: {r[3]}\nKurs: {r[4]}"
            )
            send_telegram_notification(message)

def background_task():
    while True:
        check_inactive_applicants()
        time.sleep(180)  # 3 minut

if __name__ == '__main__':
    threading.Thread(target=background_task, daemon=True).start()
    app.run(debug=True)
