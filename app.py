from flask import Flask, render_template, request, redirect, url_for, send_from_directory, session, flash
import os
import sqlite3
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key'

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

DATABASE = 'notes.db'

# Ensure database and table exist
def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        course TEXT,
        semester TEXT,
        subject TEXT,
        type TEXT,
        filename TEXT
    )''')
    conn.commit()
    conn.close()

init_db()

# Admin login
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        if request.form['password'] == 'admin123':
            session['admin'] = True
            return redirect(url_for('view_files'))
        else:
            flash('Incorrect password')
    return render_template('admin.html')

# Admin logout
@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('admin'))

# Admin view
@app.route('/admin/files')
def view_files():
    if not session.get('admin'):
        return redirect(url_for('admin'))

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT id, course, semester, subject, type, filename FROM notes")
    files = c.fetchall()
    conn.close()
    return render_template('admin_files.html', files=files)

# File upload
@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        course = request.form['course']
        semester = request.form['semester']
        subject = request.form['subject']
        material_type = request.form['type']
        file = request.files['file']

        if file and file.filename.endswith('.pdf'):
            filename = secure_filename(file.filename)
            file.save(os.path.join(UPLOAD_FOLDER, filename))

            conn = sqlite3.connect(DATABASE)
            c = conn.cursor()
            c.execute("INSERT INTO notes (course, semester, subject, type, filename) VALUES (?, ?, ?, ?, ?)",
                      (course, semester, subject, material_type, filename))
            conn.commit()
            conn.close()
            return redirect(url_for('upload_file'))

    return render_template('upload.html')

# File search
@app.route('/', methods=['GET', 'POST'])
def index():
    results = []
    if request.method == 'POST':
        course = request.form['course']
        semester = request.form['semester']
        subject = request.form['subject']
        material_type = request.form['type']

        query = "SELECT filename FROM notes WHERE 1=1"
        params = []

        if course:
            query += " AND course=?"
            params.append(course)
        if semester:
            query += " AND semester=?"
            params.append(semester)
        if subject:
            query += " AND subject=?"
            params.append(subject)
        if material_type:
            query += " AND type=?"
            params.append(material_type)

        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute(query, params)
        results = c.fetchall()
        conn.close()

    return render_template('index.html', results=results)

# Download file
@app.route('/download/<filename>')
def download(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)

# Delete file
@app.route('/delete/<int:id>')
def delete_file(id):
    if not session.get('admin'):
        return redirect(url_for('admin'))

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT filename FROM notes WHERE id=?", (id,))
    file = c.fetchone()
    if file:
        filepath = os.path.join(UPLOAD_FOLDER, file[0])
        if os.path.exists(filepath):
            os.remove(filepath)
        c.execute("DELETE FROM notes WHERE id=?", (id,))
        conn.commit()
    conn.close()
    return redirect(url_for('view_files'))

# Edit file metadata
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_file(id):
    if not session.get('admin'):
        return redirect(url_for('admin'))

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    if request.method == 'POST':
        course = request.form['course']
        semester = request.form['semester']
        subject = request.form['subject']
        material_type = request.form['type']
        c.execute("UPDATE notes SET course=?, semester=?, subject=?, type=? WHERE id=?",
                  (course, semester, subject, material_type, id))
        conn.commit()
        conn.close()
        return redirect(url_for('view_files'))

    c.execute("SELECT course, semester, subject, type FROM notes WHERE id=?", (id,))
    data = c.fetchone()
    conn.close()
    return render_template('edit.html', id=id, data=data)

if __name__ == '__main__':
    app.run(debug=True)