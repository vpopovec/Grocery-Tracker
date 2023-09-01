from flask import Blueprint, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from g_tracker.helpers import *
from werkzeug.utils import secure_filename
from main import process_receipt_from_fpath, save_receipt_to_db
from uuid import uuid4
import numpy as np
from skimage.transform import rotate
from skimage.color import rgb2gray
from deskew import determine_skew
import cv2
import os
from PIL import Image

bp = Blueprint('receipt', __name__)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}  # HEIC files aren't supported yet


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def process_file(f_path, shrunk_f_name):
    person_id = int(current_user.get_id())
    receipt = process_receipt_from_fpath(f_path)
    # TODO: Save to db
    receipt_id = save_receipt_to_db(receipt, person_id, shrunk_f_name)
    # TODO: Add manual check by client
    current_app.config['RECEIPT_ID'] = receipt_id


def deskew_image(image):
    grayscale = rgb2gray(image)
    angle = determine_skew(grayscale)
    rotated = rotate(image, angle, resize=True) * 255
    return rotated.astype(np.uint8)


def straighten_img(f_path):
    # Source: http://aishelf.org/bp-deskew/
    with open(f_path, mode='rb') as f:
        data = f.read()

    nparr = np.frombuffer(data, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    image_out = deskew_image(image)

    deskewed_f_path = f"{f_path.split('.')[0]}.jpg"
    cv2.imwrite(deskewed_f_path, image_out)
    return deskewed_f_path


def shrink_image(f_path):
    jpeg_f_path = f"{f_path.split('.')[0]}.jpeg"
    foo = Image.open(f_path)
    foo.save(jpeg_f_path, optimize=True, quality=10)


@bp.route("/scan", methods=["GET", "POST"])
@login_required
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
        elif not allowed_file(file.filename):
            flash(f'File type not allowed, please use: {", ".join(ALLOWED_EXTENSIONS)}')
            return redirect(request.url)

        if file and allowed_file(file.filename):
            file_ext = secure_filename(file.filename).split('.')[-1]
            filename = f"{uuid4()}.{file_ext}"
            print(f'saving {filename=}')
            # TODO: Save filename to DB (person can later view/delete their scanned receipts)
            # TODO: Save cached json instead of the file
            f_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            print(f"{f_path=}")
            file.save(f_path)

            # STRAIGHTEN IMAGE
            deskewed_f_path = straighten_img(f_path)

            shrinked_f_path = f"{deskewed_f_path.split('.')[0]}.jpeg"

            process_file(deskewed_f_path, os.path.basename(shrinked_f_path))

            # SHRINK IMAGE
            shrink_image(deskewed_f_path)
            if shrinked_f_path != deskewed_f_path:
                os.remove(deskewed_f_path)

            return redirect(url_for('item_table.items'))

    return render_template("receipt.html")
