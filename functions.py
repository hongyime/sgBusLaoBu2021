import json
import csv
import sqlite3
from contextlib import closing
from functools import lru_cache
from pathlib import Path
from math import radians, cos, sin, asin, sqrt

DATA_DIR = Path(__file__).resolve().parent / 'data'
DATABASE_PATH = DATA_DIR / 'database' / 'main.db'


def _read_bus_rows(command: str, parameters: tuple = ()) -> list[sqlite3.Row]:
    """Read packaged route data without creating or writing a database."""
    with closing(sqlite3.connect(DATABASE_PATH.as_uri() + '?mode=ro', uri=True)) as con:
        con.row_factory = sqlite3.Row
        return con.execute(command, parameters).fetchall()


@lru_cache(maxsize=1)
def _station_lookup() -> dict[str, tuple[str, str]]:
    """The station CSV is static for a deployment; read it once per process."""
    stations = {}
    with open(DATA_DIR / 'csv' / 'stations.csv', newline='', encoding='utf-8') as handle:
        for row in csv.DictReader(handle):
            stations.setdefault(row['mrtbusstopdescription'], (row['mrtstation'], row['mrtline']))
    return stations

def coordinates_2_txt(userlon=None, userlat=None):
    '''
    stores user's coordiantes into a txt file for easy debugging
    '''
    try:
        with open("data/txt/coordinates.txt", 'a') as f:
            coordinates = f"({str(userlon)}, {str(userlat)})"
            f.write(coordinates)
            f.write("\n")
    except IOError as e:
        print(f"Error writing to coordinates file: {e}")

def export_json(data):
    if type(data) != list:
        print('please input data as a list of dictionaries')
    elif type(data) is list:
        try:
            with open('static/coordinates.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
        except IOError as e:
            print(f"Error writing to JSON file: {e}")

def import_json():
    try:
        with open('static/coordinates.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except (IOError, json.JSONDecodeError) as e:
        print(f"Error reading JSON file: {e}")
        return []

def json_2_db(jsonfile=None, dbfile=None, create=None, insert=None):
    '''
    stores data from json file into database, creates if does not exist
    '''
    if type(jsonfile) is not str or type(dbfile) is not str or type(create) is not str or type(insert) is not str:
        print('Please input jsonfile & dbfile & create & insert as strings.')

    else:
        with open (jsonfile, 'r', encoding = "utf-8") as f:
            data = json.load(f)

        con = sqlite3.connect(dbfile)
        c = con.cursor()

        c.execute(create)

        # insertinto Bus Routes table
        if 'Bus_Routes' in insert:
            for d in data:
                c.execute(insert, (d['ServiceNo'], d['Direction'], d['StopSequence'], d['BusStopCode'], d['WD_FirstBus'], d['WD_LastBus'], d['SAT_FirstBus'], d['SAT_LastBus'], d['SUN_FirstBus'], d['SUN_LastBus']))

        # insertinto Bus Services table
        elif 'Bus_Services' in insert:
            for d in data:
                c.execute(insert, (d['ServiceNo'], d['Direction'], d['AM_Peak_Freq'], d['AM_Offpeak_Freq'], d['PM_Peak_Freq'], d['PM_Offpeak_Freq']))

        # insertinto Bus Stops table
        elif 'Bus_Stops' in insert:
            print('stops')
            for d in data:
                c.execute(insert, (d['BusStopCode'], d['Description'], d['Latitude'], d['Longitude']))

        con.commit()
        con.close()

def haversine(lat1,lon1,lat2,lon2):
    """
    Calculates the distance between 2 coordinates
    """
    #validate input
    if not all(isinstance(coord, (int, float)) for coord in [lat1, lon1, lat2, lon2]):
        print('Please input coordinates as float')
        return None
    #convert to radians
    lat1,lon1,lat2,lon2 = map(radians, (lat1,lon1,lat2,lon2))

    #haversine formula
    delta_lon = lon2 - lon1
    delta_lat = lat2 - lat1
    a = sin(delta_lat/2)**2 + cos(lat1) * cos(lat2) * sin(delta_lon/2)**2
    c = 2 * asin(sqrt(min(1.0, max(0.0, a))))
    r = 6371 # Radius of earth in kilometers. Use 3956 for miles
    return c * r

def quickSort(array): 
    '''
    returns a sorted array
    '''
    if len(array) <= 1:
        return array
    pivot = array[-1]
    ltearray = [el for el in array[:-1] if el["Distance"] <= pivot['Distance']]
    gtarray = [el for el in array[:-1] if el['Distance'] > pivot['Distance']]
    ltearray = quickSort(ltearray)
    gtarray = quickSort(gtarray)
    return ltearray + [pivot] + gtarray

#--------------------------------------

class BusStops:
    def __init__(self):
        pass

    @staticmethod
    def description_2_mrtname(description=None):
        '''
        input description of mrt bus stop, returns mrt station and mrt line
        '''
        if type(description) is not str:
            print("Please input description as a string.")
        else:
            return _station_lookup().get(description)

    @staticmethod
    def getbusstopdistance(command=None,userlon=None,userlat=None,radius=None):
        '''
        calculates the distance between each bus stop and user location, returns all bus stops within specified distance (in km) 
        '''
        if (type(command) is not str) or (type(userlon) is not float) or (type(userlat) is not float) or (type(radius) is not float):
            print('Please input command as a string, radius as float, and coordinates as floats.')
        else:
            allbusstops = []
            rows = _read_bus_rows(command)
            distances = {}

            for busstop in rows:
                busstoplon = busstop['Longitude']
                busstoplat = busstop['Latitude']

                stop_code = busstop['BusStopCode']
                if stop_code not in distances:
                    distances[stop_code] = haversine(lat1=userlat, lon1=userlon, lat2=busstoplat, lon2=busstoplon)
                distance = distances[stop_code]
                if distance <= radius:

                    d = {
                        "BusStopCode": busstop['BusStopCode'],
                        "Distance": distance,
                        "Description": busstop['Description'],
                        "ServiceNo": busstop['ServiceNo'],
                        "Direction": busstop['Direction'],
                        "StopSequence": busstop['StopSequence'],
                        "BusStopLat": busstoplat,
                        "BusStopLon": busstoplon
                    }

                    allbusstops.append(d)
                else:
                    pass
            return allbusstops

    @staticmethod
    def getmrtbusstops(command=None):
        '''
        find and returns all bus stops outside an mrt station
        '''
        if type(command) is not str:
            print("Please input command as a string.")
        else:
            allmrtbusstops = []
            rows = _read_bus_rows(command)

            for mrtbusstop in rows:
                if ('Stn' in mrtbusstop['Description']) or ('STN' in mrtbusstop['Description']) or ('stn' in mrtbusstop['Description']):
                    if ('Aft' in mrtbusstop['Description']) or ('Bef' in mrtbusstop['Description']) or ('AFT' in mrtbusstop['Description']) or ('BEF' in mrtbusstop['Description']) or ('aft' in mrtbusstop['Description']) or ('bef' in mrtbusstop['Description']) or ('Police' in mrtbusstop['Description']) or ('PUB' in mrtbusstop['Description']) or ('Instn' in mrtbusstop['Description']) or ('Railway' in mrtbusstop['Description']) or ('Power' in mrtbusstop['Description']) or ('SPC' in mrtbusstop['Description']) or ('Sq/Bef' in mrtbusstop['Description']) or ('Fire' in mrtbusstop['Description']):
                        pass
                    else:
                        d = {
                            "BusStopCode": mrtbusstop['BusStopCode'],
                            "Description": mrtbusstop['Description'],
                            "ServiceNo": mrtbusstop['ServiceNo'],
                            "Direction": mrtbusstop['Direction'],
                            "StopSequence": mrtbusstop['StopSequence']
                        }
                        allmrtbusstops.append(d)
                else:
                    pass
            return allmrtbusstops

    @staticmethod
    def findstopsequence(command=None,serviceno=None,direction=None,busstopcode=None):
        '''
        returns the bus stop number of a bus service in its route given its direction
        '''
        if type(command) is not str or type(serviceno) is not str or type(direction) is not str or type(busstopcode) is not str:
            print("Please input all inputs as a string.")
        else:
            rows = _read_bus_rows(command, (serviceno, direction, busstopcode))
            return rows[0]['StopSequence'] if rows else None

#--------------------------------------

class BusCompanies():
    def __init__(self, filename=None):
        '''
        opens and reads json file and stores the data in a variable
        '''
        if filename is None:
            print('Please input filename as a string')
        elif type(filename) is str:
            with open (filename, 'r', encoding = "utf-8") as f:
                data = json.load(f)
        else:
            print('Please input filename as a string')

    @staticmethod
    def getbusservices(company=None):
        '''
        returns a list of bus services a company operates
        '''
        if company is None:
            print('Please input a bus company name as a string')
        elif type(company) is str:
            services = []
            with open (DATA_DIR / 'json' / 'bus_services.json', 'r', encoding = "utf-8") as f:
                data = json.load(f)
            for d in data:
                if company == d['Operator']:
                    services.append(d['ServiceNo'])
                else:
                    pass
            return services
        else:
            print('Please input a bus company name as a string')

    @staticmethod
    def getcategories(company=None):
        '''
        returns a list of bus categories which company operates
        '''
        if company is None:
            print('Please input a bus company name as a string')
        elif type(company) is str:
            categories = []
            with open (DATA_DIR / 'json' / 'bus_services.json', 'r', encoding = "utf-8") as f:
                data = json.load(f)
            for d in data:
                if company == d['Operator']:
                    categories.append(d['Category'])
                else:
                    pass
            return categories
        else:
            print('Please input a bus company name as a string')

    @staticmethod
    def countcategories(categories=None):

        '''
        count and return the number of each category of bus a company operates
        '''
        if categories is None:
            print('Please input category as a list')
        elif type(categories) is list:
            counted = {
                "Trunk": categories.count("TRUNK"),
                "Express": categories.count("EXPRESS"),
                "Feeder": categories.count("FEEDER"),
                "Townlink": categories.count("TOWNLINK"),
                "Citylink": categories.count("CITYLINK"),
                "2-Tier Flat Fare": categories.count("2-TIER FLAT FARE"),
                "Industrial": categories.count("INDUSTRIAL"),
                "Night Rider": categories.count("NIGHT RIDER")
            }
            return counted
        else:
            print('Please input category as a list')

#-------------------------------------

if __name__ == "__main__":
    json_2_db()
    coordinates_2_txt()
    export_json()
    import_json()
    BusStops()
    BusCompanies()
    quickSort()
    haversine()

    # getbusservices()
    # getcategories()
    # countcategories()
    # getmrtbusstops()
    # getbusstopdistance()
    # description_2_mrtname()
    # findstopsequence()
