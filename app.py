from flask import Flask, render_template, request, redirect, url_for, send_from_directory, session, flash
import os
import sqlite3
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}
ADMIN_PASSWORD = 'admin123'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# --- Check if file is allowed ---
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Home/Search Page ---
@app.route("/", methods=["GET", "POST"])
def index():
    files = []

    if request.method == "POST":
        course = request.form.get("course")
        semester = request.form.get("semester")
        subject = request.form.get("subject")
        material_type = request.form.get("material_type")

        files = db.session.query(YourModel).filter_by(
            course=course,
            semester=semester,
            subject=subject,
            material_type=material_type
        ).all()

    return render_template("index.html", files=files)


# --- File Download Route ---
@app.route('/uploads/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# --- Upload Route ---
@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        course = request.form['course']
        semester = request.form['semester']
        subject = request.form['subject']
        material_type = request.form['type']
        file = request.files['file']

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            conn = sqlite3.connect('notes.db')
            c = conn.cursor()
            c.execute('''INSERT INTO notes (course, semester, subject, type, filename) 
                         VALUES (?, ?, ?, ?, ?)''',
                      (course, semester, subject, material_type, filename))
            conn.commit()
            conn.close()
            flash("File uploaded successfully.")
            return redirect(url_for('upload'))
    return render_template('upload.html')

# --- Admin Login ---
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        password = request.form['password']
        if password == ADMIN_PASSWORD:
            session['admin'] = True
            return redirect(url_for('view_files'))
        else:
            flash("Incorrect password.")
    return render_template('admin_login.html')

# --- View All Uploaded Files ---
@app.route('/admin/files')
def view_files():
    if not session.get('admin'):
        return redirect(url_for('admin'))

    conn = sqlite3.connect('notes.db')
    c = conn.cursor()
    c.execute("SELECT id, course, semester, subject, type, filename FROM notes")
    files = c.fetchall()
    conn.close()
    return render_template('admin_files.html', files=files)

# --- Delete File ---
@app.route('/delete/<int:id>')
def delete_file(id):
    if not session.get('admin'):
        return redirect(url_for('admin'))

    conn = sqlite3.connect('notes.db')
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

# --- Edit File Metadata ---
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_file(id):
    if not session.get('admin'):
        return redirect(url_for('admin'))

    conn = sqlite3.connect('notes.db')
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

@app.route('/download/<filename>')
def download(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

# --- Run for Render ---
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))  # Default port if not on Render
    app.run(host='0.0.0.0', port=port, debug=True)
