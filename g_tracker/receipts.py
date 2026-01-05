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
import io
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


# TODO: Check if gemini can work with skewed images
# def deskew_image(image):
#     grayscale = rgb2gray(image)
#     angle = determine_skew(grayscale)
#     rotated = rotate(image, angle, resize=True) * 255
#     return rotated.astype(np.uint8)



# def preprocess_receipt_image(image_path):
#     """
#     Optimize image for OCR: denoise, enhance contrast, binarize
#     """
#     # Read image
#     img = cv2.imread(image_path)
    
#     # Convert to grayscale (faster processing)
#     gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
#     # Resize if too large (OCR is faster on smaller images)
#     height, width = gray.shape
#     max_dimension = 2000  # Optimal for receipts
#     if max(height, width) > max_dimension:
#         scale = max_dimension / max(height, width)
#         new_width = int(width * scale)
#         new_height = int(height * scale)
#         gray = cv2.resize(gray, (new_width, new_height), interpolation=cv2.INTER_AREA)
    
#     # Denoise (reduces OCR errors)
#     denoised = cv2.fastNlMeansDenoising(gray, h=10, templateWindowSize=7, searchWindowSize=21)
    
#     # Enhance contrast using CLAHE (better for receipts)
#     clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
#     enhanced = clahe.apply(denoised)
    
#     # Adaptive thresholding (better than simple threshold for varying lighting)
#     binary = cv2.adaptiveThreshold(
#         enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
#         cv2.THRESH_BINARY, 11, 2
#     )
    
#     return binary


def straighten_img(f_path):
    # Source: http://aishelf.org/bp-deskew/
    # with open(f_path, mode='rb') as f:
    #     data = f.read()

    # nparr = np.frombuffer(data, np.uint8)
    # image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    # Deskew
    # image_out = deskew_image(image)
    
    # Preprocess for OCR
    processed = preprocess_image_for_upload(f_path)
    # processed = preprocess_receipt_image_from_array(image_out)
    
    deskewed_f_path = f"{f_path.split('.')[0]}_processed.jpg"
    # cv2.imwrite(deskewed_f_path, processed)
    with open(deskewed_f_path, 'wb') as f:
        f.write(processed)
    return deskewed_f_path


# def preprocess_receipt_image_from_array(image_array):
#     """Preprocess image array (after deskew)"""
#     gray = cv2.cvtColor(image_array, cv2.COLOR_BGR2GRAY)
    
#     # Resize if needed
#     height, width = gray.shape
#     max_dimension = 2000
#     if max(height, width) > max_dimension:
#         scale = max_dimension / max(height, width)
#         gray = cv2.resize(gray, (int(width * scale), int(height * scale)), 
#                          interpolation=cv2.INTER_AREA)
    
#     # Denoise
#     denoised = cv2.fastNlMeansDenoising(gray, h=10)
    
#     # Enhance contrast
#     clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
#     enhanced = clahe.apply(denoised)
    
#     return enhanced
    

def shrink_image(f_path):
    jpeg_f_path = f"{f_path.split('.')[0]}.jpeg"
    foo = Image.open(f_path)
    foo.save(jpeg_f_path, optimize=True, quality=10)


def preprocess_image_for_upload(f_path, max_dim=2000):
    # img = Image.open(io.BytesIO(image_bytes))
    img = Image.open(f_path)

    # 1. Standardize Orientation (Fixes upside-down uploads)
    img = img.convert("RGB")
    
    # 2. Resize while maintaining aspect ratio
    w, h = img.size
    if max(w, h) > max_dim:
        scale = max_dim / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
    
    # 3. Compress to JPEG
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=85)
    return buffer.getvalue()


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
