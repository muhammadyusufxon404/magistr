from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import requests

app = Flask(__name__)
DATABASE = 'crm.db'
TOKEN = '6730091039:AAH-XJ7CyjOGOSkFDYMbAuifpsREMLm2zd8'        # Replace with your Telegram Bot Token
CHAT_ID = '6855997739'       # Replace with the admin Telegram chat ID

def init_db():
    with sqlite3.connect(DATABASE) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS applicants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                course TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                note TEXT
            )
        """)

def send_telegram_notification(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={'chat_id': CHAT_ID, 'text': message})

@app.route('/')
def index():
    with sqlite3.connect(DATABASE) as conn:
        applicants = conn.execute("SELECT * FROM applicants").fetchall()
    return render_template('dashboard.html', applicants=applicants)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        course = request.form['course']
        note = request.form['note']
        with sqlite3.connect(DATABASE) as conn:
            conn.execute(
                "INSERT INTO applicants (name, phone, course, note) VALUES (?, ?, ?, ?)",
                (name, phone, course, note)
            )
        send_telegram_notification(f"Yangi o‘quvchi ro‘yxatdan o‘tdi:\nIsm: {name}\nTelefon: {phone}\nKurs: {course}")
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
