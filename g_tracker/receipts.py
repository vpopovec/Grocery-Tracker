from flask import Blueprint, request, redirect, url_for, flash, current_app
from g_tracker.helpers import *
from werkzeug.utils import secure_filename
from person import Person
from main import process_receipt_from_fpath

bp = Blueprint('receipt', __name__)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def process_file(f_path):
    person = Person('000')
    receipt = process_receipt_from_fpath(f_path)
    # TODO: Add manual check by client
    # TODO: Save to db


@bp.route("/scan", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # TODO: Save cached json instead of the file
            f_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(f_path)


            # return redirect(url_for('scan', name=filename))

    return render_template("receipt.html")
