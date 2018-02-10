from flask import Flask, request, render_template, jsonify

from tracklistwriter import TrackListWrite, parse_tracklist_str

app = Flask(__name__)

@app.route('/', methods=['GET'])
def root():
    return render_template('index.html')

@app.route('/api/write-tracks', methods=['POST', 'GET'])
def write_tracks():
    # print request.form
    tracklist = parse_tracklist_str(request.form['tracklist'])
    options = {
        'source': request.form['options[source]'],
        'va': request.form['options[va]'],
        'merge': request.form['options[merge]'],
        'isClass': request.form['options[isClass]'],
        'mvlang': request.form['options[mvlang]'],
        'lang': request.form['options[lang]'],
        'toClear': []
    }
    return TrackListWrite(tracklist, options)

if __name__ == '__main__':
    app.run()
