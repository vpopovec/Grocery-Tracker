import numpy as np
from skimage import io
from skimage.transform import rotate
from skimage.color import rgb2gray
from deskew import determine_skew
# import jsonpickle
import cv2
from flask import Flask, request, Response

app = Flask(__name__)


# deskew image
def deskew_image(image):
    grayscale = rgb2gray(image)
    angle = determine_skew(grayscale)
    rotated = rotate(image, angle, resize=True) * 255
    return rotated.astype(np.uint8)


def deskew_func(targetfile):
    # Source: http://aishelf.org/bp-deskew/
    with open(targetfile, mode='rb') as f:
        data = f.read()
    nparr = np.frombuffer(data, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    image_out = deskew_image(image)
    cv2.imwrite(targetfile[:-4] + "deskewed.jpgg", image_out)


if __name__ == '__main__':
    # app.run(debug=True, host='127.0.0.1', port=8090)
    deskew_func('Foto 8.8.2023, 16 05 31.jpg')
