from collections import defaultdict
from math import isfinite
from flask import Flask, render_template, request

from functions import BusStops, BusCompanies, DATA_DIR
from sqlcommands import commands

#-------------------------------------

'''Initiating instance objects needed'''

stops = BusStops()
companies = BusCompanies(str(DATA_DIR / 'json' / 'bus_services.json'))

'''Creating static mrt data for displaying'''

allmrtbusstops = stops.getmrtbusstops(commands["selectfromdatabase"])

'''Creating static bus data for displaying'''

smrt_numberofservices = len(companies.getbusservices("SMRT"))
sbst_numberofservices = len(companies.getbusservices("SBST"))
tts_numberofservices = len(companies.getbusservices("TTS"))
gas_numberofservices = len(companies.getbusservices("GAS"))

smrt_categories = companies.getcategories("SMRT")
sbst_categories = companies.getcategories("SBST")
tts_categories = companies.getcategories("TTS")
gas_categories = companies.getcategories("GAS")

smrt = companies.countcategories(smrt_categories)
sbst = companies.countcategories(sbst_categories)
tts = companies.countcategories(tts_categories)
gas = companies.countcategories(gas_categories)

'''Creating and inserting relevant data from JSON files to Database file'''

# json_2_db('json/bus_routes.json', 'database/main.db', commands["createbusroutestable"], commands["insertbusroutes"])

# json_2_db('json/bus_services.json', 'database/main.db', commands["createbusservicestable"], commands["insertbusservices"])

# json_2_db('json/bus_stops.json', 'database/main.db', commands["createbusstopstable"], commands["insertbusstops"])

'''Start of Flask WebApp'''

app = Flask(__name__, template_folder='templates')

@app.after_request
def add_header(r):
    """Keep submitted coordinates out of shared response caches."""
    if request.endpoint in {'findabus', 'coordinates'} or request.method != 'GET':
        r.headers['Cache-Control'] = 'private, no-store'
    else:
        r.headers['Cache-Control'] = 'public, max-age=0'
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
    return render_template('learnbusfacts.html', gas = gas, gas_len = gas_numberofservices, smrt = smrt, smrt_len = smrt_numberofservices, sbst = sbst, sbst_len = sbst_numberofservices, tts = tts, tts_len = tts_numberofservices)


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

    nearby = stops.getbusstopdistance(commands['selectfromdatabase'], userlat=userlat, userlon=userlon, radius=ra)
    destinations = defaultdict(list)
    for station_stop in allmrtbusstops:
        destinations[(station_stop['ServiceNo'], station_stop['Direction'])].append(station_stop)

    data = []
    for busstop in nearby:
        for station_stop in destinations[(busstop['ServiceNo'], busstop['Direction'])]:
            numberofstops = int(station_stop['StopSequence']) - int(busstop['StopSequence'])
            if numberofstops <= 0:
                continue
            station = stops.description_2_mrtname(station_stop['Description'])
            if station is None:
                continue
            mrtstation, mrtline = station
            if 'North-South' in mrtline: mrt_color = '#d42e12'
            elif 'East-West' in mrtline: mrt_color = '#009645'
            elif 'North-East' in mrtline: mrt_color = '#9900aa'
            elif 'Circle' in mrtline: mrt_color = '#fa9e0d'
            elif 'Downtown' in mrtline: mrt_color = '#005ec4'
            elif 'Thomson' in mrtline: mrt_color = '#9d5b25'
            else: mrt_color = '#64748b'
            data.append({
                'mrt_station': mrtstation, 'mrt_line': mrtline, 'mrt_color': mrt_color,
                'walkdistance': f"{int(busstop['Distance'] * 1000)}m",
                'board_busstopdescription': busstop['Description'].title(),
                'busstopcode': busstop['BusStopCode'], 'busservice': busstop['ServiceNo'],
                'numberofstops': numberofstops,
                'alight_busstopdescription': station_stop['Description'].title(),
                'busstoplat': busstop['BusStopLat'], 'busstoplon': busstop['BusStopLon'],
            })
    data.sort(key=lambda item: int(item['walkdistance'][:-1]))
    return render_template('findabus.html', userlon=userlon, userlat=userlat, data=data, ra=ra)


@app.route('/help', methods=['GET'])
def help():
    return render_template('help.html')


@app.route('/coordinates', methods=['GET'])
def coordinates():
    try:
        with open('data/txt/coordinates.txt', 'r') as f:
            data = f.readlines()
            if data:  # Only pop if there's data
                data.pop(0)
        return render_template('coordinates.html', data=data)
    except IOError:
        return render_template('coordinates.html', data=[])


if __name__ == '__main__':
    app.run("0.0.0.0", debug=True)
