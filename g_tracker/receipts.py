from flask import Blueprint
from g_tracker.helpers import *

bp = Blueprint('receipt', __name__)


@bp.route("/scan", methods=["GET", "POST"])
def index():
    if request.
    return render_template("receipt.html")
