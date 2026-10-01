from flask import Blueprint, request, redirect, url_for, flash, current_app, session
from flask_login import login_required, current_user
from g_tracker.helpers import *
from g_tracker.extensions import limiter
from g_tracker.forms import RegisterShopForm
from g_tracker.llm_quota import (
    RECEIPT_SCAN,
    QuotaExceeded,
    check_usage_allowed,
    quota_status,
    record_usage_attempt,
)
from g_tracker.shops import UNKNOWN, register_or_resolve_shop, shops_for_prompt
from g_tracker.models import Receipt
from g_tracker import db
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from werkzeug.utils import secure_filename
from main import process_receipt_from_fpath, save_receipt_to_db
from uuid import uuid4
import numpy as np
from skimage.transform import rotate
from skimage.color import rgb2gray
from deskew import determine_skew
import cv2
import os
from PIL import Image, ImageOps
import io
bp = Blueprint('receipt', __name__)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}  # HEIC files aren't supported yet
SHOP_GUESS_SESSION_KEY = 'pending_shop_guess'


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def process_file(f_path, shrunk_f_name):
    """Scan and save a receipt.

    Returns (ok, message, meta). meta is None on failure; on success it has
    receipt_id, shop_name, shop_guess.
    """
    person_id = int(current_user.get_id())
    try:
        check_usage_allowed(person_id, RECEIPT_SCAN)
    except QuotaExceeded as exc:
        return False, exc.message, None

    record_usage_attempt(person_id, RECEIPT_SCAN)
    allowed_shops = shops_for_prompt(person_id)
    receipt, status_message = process_receipt_from_fpath(
        f_path, allowed_shops=allowed_shops)
    if receipt:
        receipt_id = save_receipt_to_db(receipt, person_id, shrunk_f_name)
        current_app.config['RECEIPT_ID'] = receipt_id
        return True, status_message, {
            'receipt_id': receipt_id,
            'shop_name': receipt.shop,
            'shop_guess': getattr(receipt, 'shop_guess', '') or '',
        }
    return False, status_message, None


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
    foo = ImageOps.exif_transpose(Image.open(f_path))
    foo.save(jpeg_f_path, optimize=True, quality=10)


def preprocess_image_for_upload(f_path, max_dim=2000):
    # img = Image.open(io.BytesIO(image_bytes))
    img = ImageOps.exif_transpose(Image.open(f_path))

    # 1. Standardize color (EXIF orientation already baked into pixels above)
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


def _owned_unknown_receipt(receipt_id: int):
    person_id = int(current_user.get_id())
    return db.session.execute(
        select(Receipt).where(
            Receipt.receipt_id == receipt_id,
            Receipt.person_id == person_id,
            Receipt.shop_name == UNKNOWN,
        )
    ).scalar_one_or_none()


@bp.route("/scan/register-shop/<int:receipt_id>", methods=["GET", "POST"])
@login_required
def register_shop(receipt_id):
    receipt = _owned_unknown_receipt(receipt_id)
    if receipt is None:
        flash('Receipt not found or shop already set.')
        return redirect(url_for('item_table.items'))

    form = RegisterShopForm()
    if request.method == "GET":
        form.shop_name.data = session.get(SHOP_GUESS_SESSION_KEY, '')

    if form.validate_on_submit():
        if form.skip.data:
            session.pop(SHOP_GUESS_SESSION_KEY, None)
            return redirect(url_for('item_table.items'))

        resolved = register_or_resolve_shop(
            int(current_user.get_id()), form.shop_name.data or '')
        if resolved is None:
            flash('Please enter a shop name (not "Unknown").')
            return render_template("register_shop.html", form=form)

        receipt.shop_name = resolved
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash(
                f'Could not rename this receipt (another already has that '
                f'shop, date, and total). "{resolved}" is available for future scans.'
            )
            session.pop(SHOP_GUESS_SESSION_KEY, None)
            return redirect(url_for('item_table.items'))

        session.pop(SHOP_GUESS_SESSION_KEY, None)
        flash(f'Shop registered as "{resolved}".')
        return redirect(url_for('item_table.items'))

    return render_template("register_shop.html", form=form)


@bp.route("/scan", methods=["GET", "POST"])
@login_required
@limiter.limit(lambda: current_app.config.get('SCAN_RATE_LIMIT', '5 per minute'), methods=['POST'])
def index():
    scan_quota = quota_status(int(current_user.get_id()), RECEIPT_SCAN)
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

            ok, status_message, meta = process_file(
                deskewed_f_path, os.path.basename(shrinked_f_path))
            if ok:
                # SHRINK IMAGE
                shrink_image(deskewed_f_path)
                if shrinked_f_path != deskewed_f_path:
                    os.remove(deskewed_f_path)

                if meta['shop_name'] == UNKNOWN:
                    session[SHOP_GUESS_SESSION_KEY] = meta.get('shop_guess') or ''
                    return redirect(url_for(
                        'receipt.register_shop', receipt_id=meta['receipt_id']))
                return redirect(url_for('item_table.items'))

            flash(status_message)

    return render_template("receipt.html", scan_quota=scan_quota)
