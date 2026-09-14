from math import isfinite
from flask import Flask, abort, render_template, request
import transit

app = Flask(__name__, template_folder='templates')
app.config['MAX_CONTENT_LENGTH'] = 4096


@app.before_request
def protect_legacy_history():
    filename = (request.view_args or {}).get('filename', '').replace('\\', '/')
    if request.endpoint == 'static' and filename.split('/')[-1] == 'coordinates.json':
        abort(404)

@app.after_request
def add_header(r):
    """Keep submitted coordinates out of shared response caches."""
    if request.endpoint in {'findabus', 'coordinates'} or request.method not in {'GET', 'HEAD'} or r.status_code != 200:
        r.headers['Cache-Control'] = 'private, no-store'
    else:
        # These GET pages contain no submitted coordinates or user-specific data.
        r.headers['Cache-Control'] = 'public, max-age=0, s-maxage=86400'
        r.headers['Vercel-CDN-Cache-Control'] = 'public, max-age=86400'
    return r


@app.route('/', methods=['POST','GET'])
def home():
    return render_template('laobu.html')


@app.route('/getyourlocation', methods=['POST','GET'])
def getyourlocation():
    if request.method == "POST":
        if request.form.get("slider") is not None:
            ra = request.form.get("slider") #type: string
            return render_template('getyourlocation.html', ra=ra)
        ra = '0.2'
        return render_template('getyourlocation.html', ra=ra)
    else:
        ra = '0.2'
        return render_template('getyourlocation.html', ra=ra)


@app.route('/learnbusfacts', methods=['GET'])
def learnbusfacts():
    try:
        return render_template('learnbusfacts.html', **transit.facts())
    except transit.TransitUnavailable:
        return render_template('getyourlocation.html', ra='0.2',
                               error='Bus facts are temporarily unavailable. Please try again later.'), 503


@app.route('/findabus', methods=['POST'])
def findabus():
    manual_lat = request.form.get('latitude1', '').strip()
    manual_lon = request.form.get('longitude1', '').strip()
    userlat = manual_lat if manual_lat or manual_lon else request.form.get('latitude')
    userlon = manual_lon if manual_lat or manual_lon else request.form.get('longitude')
    try:
        ra, userlat, userlon = float(request.form.get('slider')), float(userlat), float(userlon)
        if not all(isfinite(value) for value in (ra, userlat, userlon)):
            raise ValueError('Non-finite input')
        if not (-90 <= userlat <= 90 and -180 <= userlon <= 180 and 0.1 <= ra <= 1.0):
            raise ValueError('Outside supported bounds')
    except (TypeError, ValueError):
        return render_template('getyourlocation.html', ra='0.2',
                               error='Enter valid latitude and longitude, and a radius between 0.1 and 1 km.',
                               latitude=manual_lat, longitude=manual_lon), 400

    try:
        result = transit.search(userlat, userlon, ra)
    except transit.TransitUnavailable:
        return render_template('getyourlocation.html', ra=str(ra),
                               error='Bus search is temporarily unavailable. Please try again later.',
                               latitude=manual_lat, longitude=manual_lon), 503
    return render_template('findabus.html', userlon=userlon, userlat=userlat,
                           data=result['results'], has_more=result['has_more'], ra=ra)


@app.route('/help', methods=['GET'])
def help():
    return render_template('help.html')


@app.route('/coordinates', methods=['GET'])
def coordinates():
    return render_template('coordinates.html'), 410


if __name__ == '__main__':
    app.run("127.0.0.1", debug=False)
