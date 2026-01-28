from flask import Flask, render_template, request, jsonify, redirect, url_for
from datetime import datetime
import sqlite3 
import os

app = Flask(__name__)
DATABASE = 'attendance.db'

def init_db():
    if not os.path.exists(DATABASE):
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute('''CREATE TABLE students
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      name TEXT NOT NULL,
                      roll_number TEXT UNIQUE NOT NULL)''')
        c.execute('''CREATE TABLE attendance
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      student_id INTEGER NOT NULL,
                      date TEXT NOT NULL,
                      status TEXT NOT NULL,
                      FOREIGN KEY(student_id) REFERENCES students(id))''')
        conn.commit()
        conn.close()

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/dashboard")
def dashboard():
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM students')
    students = c.fetchall()
    conn.close()
    return render_template("dashboard.html", students=students)

@app.route("/mark-attendance")
def mark_attendance():
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM students ORDER BY name')
    students = c.fetchall()
    conn.close()
    today = datetime.now().strftime("%Y-%m-%d")
    return render_template("mark_attendance.html", students=students, today=today)

@app.route("/add-student", methods=['POST'])
def add_student():
    data = request.json
    name = data.get('name')
    roll_number = data.get('roll_number')
    
    if not name or not roll_number:
        return jsonify({'error': 'Name and roll number required'}), 400
    
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute('INSERT INTO students (name, roll_number) VALUES (?, ?)',
                  (name, roll_number))
        conn.commit()
        return jsonify({'success': True, 'id': c.lastrowid})
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Roll number already exists'}), 400
    finally:
        conn.close()

@app.route("/save-attendance", methods=['POST'])
def save_attendance():
    data = request.json
    attendance_data = data.get('attendance', [])
    date = data.get('date')
    
    if not attendance_data or not date:
        return jsonify({'error': 'Invalid data'}), 400
    
    conn = get_db()
    c = conn.cursor()
    try:
        # Clear existing attendance for the date
        c.execute('DELETE FROM attendance WHERE date = ?', (date,))
        
        # Insert new attendance records
        for entry in attendance_data:
            c.execute('INSERT INTO attendance (student_id, date, status) VALUES (?, ?, ?)',
                      (entry['student_id'], date, entry['status']))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route("/view-attendance")
def view_attendance():
    conn = get_db()
    c = conn.cursor()
    c.execute('''SELECT a.date, s.name, s.roll_number, a.status
                 FROM attendance a
                 JOIN students s ON a.student_id = s.id
                 ORDER BY a.date DESC, s.name''')
    records = c.fetchall()
    
    # Group by date
    attendance_by_date = {}
    for record in records:
        date = record['date']
        if date not in attendance_by_date:
            attendance_by_date[date] = []
        attendance_by_date[date].append({
            'name': record['name'],
            'roll_number': record['roll_number'],
            'status': record['status']
        })
    
    conn.close()
    return render_template("view_attendance.html", attendance_by_date=attendance_by_date)

@app.route("/attendance-stats")
def attendance_stats():
    conn = get_db()
    c = conn.cursor()
    c.execute('''SELECT s.id, s.name, s.roll_number,
                        COUNT(CASE WHEN a.status = 'Present' THEN 1 END) as present,
                        COUNT(CASE WHEN a.status = 'Absent' THEN 1 END) as absent,
                        COUNT(a.id) as total
                 FROM students s
                 LEFT JOIN attendance a ON s.id = a.student_id
                 GROUP BY s.id
                 ORDER BY s.name''')
    stats = c.fetchall()
    conn.close()
    return render_template("stats.html", stats=stats)

if __name__ == "__main__":
    init_db()
    app.run(debug=True,host='0.0.0.0',port=5000)
    

    