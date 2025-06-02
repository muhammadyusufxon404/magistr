from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import requests
from datetime import datetime, timedelta
import pytz

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
                created_at TEXT
            )
        """)

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
        phone2 = request.form.get('phone2', '')  # ixtiyoriy
        course = request.form['course']
        note = request.form['note']

        tz = pytz.timezone('Asia/Tashkent')
        created_at = datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')

        with sqlite3.connect(DATABASE) as conn:
            conn.execute(
                "INSERT INTO applicants (name, phone1, phone2, course, note, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (name, phone1, phone2, course, note, created_at)
            )
        send_telegram_notification(
            f"Yangi o‘quvchi ro‘yxatdan o‘tdi:\nIsm: {name}\nTelefon 1: {phone1}\nTelefon 2: {phone2}\nKurs: {course}"
        )
        return redirect(url_for('index'))
    return render_template('register.html')

@app.route('/accept/<int:id>')
def accept(id):
    with sqlite3.connect(DATABASE) as conn:
        conn.execute("UPDATE applicants SET status='accepted' WHERE id=?", (id,))
        row = conn.execute("SELECT name, course FROM applicants WHERE id=?", (id,)).fetchone()
    send_telegram_notification(f"O‘quvchi qabul qilindi:\nID: {id}\nIsm: {row[0]}\nKurs: {row[1]}")
    return redirect(url_for('index'))

@app.route('/reject/<int:id>')
def reject(id):
    with sqlite3.connect(DATABASE) as conn:
        conn.execute("UPDATE applicants SET status='rejected' WHERE id=?", (id,))
        row = conn.execute("SELECT name, course FROM applicants WHERE id=?", (id,)).fetchone()
    send_telegram_notification(f"O‘quvchi rad etildi:\nID: {id}\nIsm: {row[0]}\nKurs: {row[1]}")
    return redirect(url_for('index'))

@app.route('/delete/<int:id>')
def delete(id):
    with sqlite3.connect(DATABASE) as conn:
        conn.execute("DELETE FROM applicants WHERE id=?", (id,))
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)

