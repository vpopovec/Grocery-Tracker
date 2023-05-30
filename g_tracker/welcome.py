from flask import Blueprint
from g_tracker.helpers import *

bp = Blueprint('welcome', __name__)


@bp.route("/", methods=["GET"])
def index():
    return render_template("index.html")
