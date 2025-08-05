from flask import Flask, render_template, request, redirect, url_for, send_from_directory, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import os

# --- App Config ---
app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}
ADMIN_PASSWORD = 'admin123'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///notes.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- Ensure upload folder exists ---
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# --- Allowed file check ---
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Model ---
class Notes(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course = db.Column(db.String(100))
    semester = db.Column(db.String(100))
    subject = db.Column(db.String(100))
    material_type = db.Column(db.String(100))
    filename = db.Column(db.String(200))

# --- Create DB Table (Run once on startup) ---
with app.app_context():
    db.create_all()

# --- Home/Search Page ---
@app.route("/", methods=["GET", "POST"])
def index():
    files = []
    if request.method == "POST":
        course = request.form.get("course")
        semester = request.form.get("semester")
        subject = request.form.get("subject")
        material_type = request.form.get("material_type")

        files = Notes.query.filter_by(
            course=course,
            semester=semester,
            subject=subject,
            material_type=material_type
        ).all()

    return render_template("index.html", files=files)

# --- Upload File ---
@app.route("/upload", methods=["GET", "POST"])
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

            new_note = Notes(course=course, semester=semester, subject=subject,
                             material_type=material_type, filename=filename)
            db.session.add(new_note)
            db.session.commit()

            flash("File uploaded successfully.")
            return redirect(url_for('upload'))

    return render_template('upload.html')

# --- File Download ---
@app.route('/download/<filename>')
def download(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

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

    files = Notes.query.all()
    return render_template('admin_files.html', files=files)

# --- Delete File ---
@app.route('/delete/<int:id>')
def delete_file(id):
    if not session.get('admin'):
        return redirect(url_for('admin'))

    note = Notes.query.get(id)
    if note:
        filepath = os.path.join(UPLOAD_FOLDER, note.filename)
        if os.path.exists(filepath):
            os.remove(filepath)
        db.session.delete(note)
        db.session.commit()
    return redirect(url_for('view_files'))

# --- Edit File Metadata ---
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_file(id):
    if not session.get('admin'):
        return redirect(url_for('admin'))

    note = Notes.query.get(id)
    if request.method == 'POST':
        note.course = request.form['course']
        note.semester = request.form['semester']
        note.subject = request.form['subject']
        note.material_type = request.form['type']
        db.session.commit()
        return redirect(url_for('view_files'))

    return render_template('edit.html', id=id, data=note)

# --- For Render Deployment ---
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, debug=True)
