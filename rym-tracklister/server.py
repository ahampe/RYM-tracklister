from __future__ import print_function
import sys

from flask import Blueprint, request, render_template, jsonify
from . import tracklister as tlr


bp = Blueprint('server', __name__)


@bp.route('/', methods=['GET'])
def root():
    return render_template('index.html')


@bp.route('/background_process')
def background_process():
    try:
        caps = True if request.args['caps'] == 'true' else False
        tracks_in = tlr.parse_tracklist_str(request.args['tracklist'])
        # print(tracks_in, file=sys.stderr)
        tracks_out = u"\n".join(tlr.track_list_write(tracks_in, caps))
        return jsonify(result=tracks_out)
    except Exception as e:
        return str(e)
