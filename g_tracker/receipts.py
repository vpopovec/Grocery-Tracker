from flask import Blueprint, request, redirect, url_for, flash, current_app, send_file
from g_tracker.helpers import *
from werkzeug.utils import secure_filename
from person import Person
from main import process_receipt_from_fpath, save_receipt_to_db
from uuid import uuid4

bp = Blueprint('receipt', __name__)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


@bp.route('/scan')
def get_image():
    if f_name := request.args.get('f_name'):
        f_path = os.path.join(current_app.config['UPLOAD_FOLDER'], f_name)
        return send_file(f_path)
    return "Sorry, no f_name specified in url"


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def process_file(f_path):
    # TODO: Get person's details (register to DB)
    person = Person('000')
    receipt = process_receipt_from_fpath(f_path)
    # TODO: Save to db
    receipt_id = save_receipt_to_db(receipt, person)
    # TODO: Add manual check by client
    current_app.config['RECEIPT_ID'] = receipt_id


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
            file_ext = secure_filename(file.filename).split('.')[-1]
            filename = f"{uuid4()}.{file_ext}"
            # TODO: Save filename to DB (person can later view/delete their scanned receipts)
            # TODO: Save cached json instead of the file
            f_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            print(f"{f_path=}")
            file.save(f_path)
            process_file(f_path)

            return redirect(url_for('item_table.items'))

    return render_template("receipt.html")
