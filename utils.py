import folium
import json
import pandas as pd
import pickle
import re
import tqdm
import numpy as np
import os
import matplotlib.pyplot as plt
from geopy.geocoders import Nominatim
geolocator = Nominatim(user_agent="geoapiExercises")


hourly_lookup = {
    'Year': 2080,
    'Hour': 1, 
    'Bi-Weekly': 80,
    'Month': 40 * 4 + 12,  # 172
    'Week': 40,
}

STATE_ABBREV_LOOKUP = {
    'Alabama': 'AL',
    'Alaska': 'AK',
    'American Samoa': 'AS',
    'Arizona': 'AZ',
    'Arkansas': 'AR',
    'California': 'CA',
    'Colorado': 'CO',
    'Connecticut': 'CT',
    'Delaware': 'DE',
    'District of Columbia': 'DC',
    'Florida': 'FL',
    'Georgia': 'GA',
    'Guam': 'GU',
    'Hawaii': 'HI',
    'Idaho': 'ID',
    'Illinois': 'IL',
    'Indiana': 'IN',
    'Iowa': 'IA',
    'Kansas': 'KS',
    'Kentucky': 'KY',
    'Louisiana': 'LA',
    'Maine': 'ME',
    'Maryland': 'MD',
    'Massachusetts': 'MA',
    'Michigan': 'MI',
    'Minnesota': 'MN',
    'Mississippi': 'MS',
    'Missouri': 'MO',
    'Montana': 'MT',
    'Nebraska': 'NE',
    'Nevada': 'NV',
    'New Hampshire': 'NH',
    'New Jersey': 'NJ',
    'New Mexico': 'NM',
    'New York': 'NY',
    'North Carolina': 'NC',
    'North Dakota': 'ND',
    'Northern Mariana Islands':'MP',
    'Ohio': 'OH',
    'Oklahoma': 'OK',
    'Oregon': 'OR',
    'Pennsylvania': 'PA',
    'Puerto Rico': 'PR',
    'Rhode Island': 'RI',
    'South Carolina': 'SC',
    'South Dakota': 'SD',
    'Tennessee': 'TN',
    'Texas': 'TX',
    'Utah': 'UT',
    'Vermont': 'VT',
    'Virgin Islands': 'VI',
    'Virginia': 'VA',
    'Washington': 'WA',
    'West Virginia': 'WV',
    'Wisconsin': 'WI',
    'Wyoming': 'WY'
}

def cleanup_zip(code):
    #if ';' in code:
    #    return code.split(';')[-1]
    #elif '-' in code:
    #    return code.split('-')[0]
    #elif ',' in code:
    #    return code.split(',')[-1]
    code = re.sub('[^0-9]', '', code)[:5]

    return code

def cleanup_soc_code(code):
    #if ';' in code:
    #    return code.split(';')[-1]
    #elif '-' in code:
    #    return code.split('-')[0]
    #elif ',' in code:
    #    return code.split(',')[-1]
    # code = re.sub('[^0-9]', '', code)[:5]
    code = code.split('.')[0]

    return code

def get_soc_title_lookup(dirty_soc_title):
    processed = re.sub('[^A-Za-z\s]', '', dirty_soc_title.strip())
    processed = re.sub('[Ss]$', '', processed.strip())
    processed = re.sub('\s+', ' ', processed.strip())
    return processed

def get_state_abbrev(state):
    if len(state) == 2:
        return state.upper()
    elif state.lower().title() in STATE_ABBREV_LOOKUP:
        return STATE_ABBREV_LOOKUP[state.lower().title()]
    elif state.lower().title() == 'District Of Columbia':
        return 'DC'
    else:
        #print(state)
        return ''

# RE_ADDR = re.compile(r"(one|[0-9]+)\,?\s+([nswe]?\.?\s+)?([\w\'\.\/]+\s)*([\w\.]+\s?)")
RE_CITY = re.compile(r"^([a-zA-Z\']+(\.|\,)(\s?|\-))?(([a-zA-Z\']+(\s+|\-))*)([a-zA-Z\']+)$")
def city_regex(string):
    string_new = string.replace('&nbsp;', '')
    string_new = string_new.replace(',', '')
    string_new = string_new.replace('D.C.', '')
    result = RE_CITY.search(string_new.strip())
    if result is not None:
        return result[0].title()
    return ''

# RE_ADDR = re.compile(r"(one|[0-9]+)\,?\s+([nswe]?\.?\s+)?([\w\'\.\/]+\s)*([\w\.]+\s?)")
RE_ADDR = re.compile(r"((one|two|three|four|five|[0-9]+)\s?\,?\-?\s*([nswe]?\.?\s+)?(([\w|\'|\.|\/]+\s+)*)((\w*[\'|'\.|\/]?[a-zA-Z]+\s?)|([a-zA-Z][0-9]+\s?)))($|\W)")
def address_regex(string):
    result = RE_ADDR.search(string)
    if result is not None:
        return result[1].title().replace('-', ' ')
    return None


def get_clean_street_address(addr1, addr2):
    
    parsed1 = address_regex(addr1.lower())
    parsed2 = address_regex(addr2.lower())
    
    if parsed2 == None and parsed1 != None:
        return parsed1
    elif parsed1 == None and parsed2 != None:
        return parsed2
    elif parsed1 != None and parsed2 != None:
        return parsed1
    else:
        if addr1 != 'nan' or addr2 != 'nan':
            #print(addr1, ' ----- ', addr2)
            pass
        return ''

def addr_abbrev_replace(string):
    string = string.strip()
    string = string.replace(',', '')
    
    string = re.sub(r'\s+Dr\.?$', ' Drive', string)
    string = re.sub(r'\s+Rd\.?$', ' Road', string)
    string = re.sub(r'\s+Ct\.?$', ' Court', string)
    string = re.sub(r'\s+Sq\.?$', ' Square', string)
    string = re.sub(r'\s+Ln\.?$', ' Lane', string)
    string = re.sub(r'\s+Blvd\.?$', ' Boulevard', string)
    string = re.sub(r'\s+Pl\.?$', ' Place', string)
    string = re.sub(r'\s+St\.?$', ' Street', string)
    string = re.sub(r'\s+Ave\.?$', ' Avenue', string)
    string = re.sub(r'\s+Ctr\.?$', ' Center', string)
    string = re.sub(r'\s+Pkwy\.?$', ' Parkway', string)
    string = re.sub(r'\sCentre\s$', ' Center ', string)
    
    string = re.sub(r'\s+', ' ', string)
    return string


def company_name_replace(candidate, n):
    
    def internal(string):
        string = string.lower().strip()
        string = re.sub(r'(\,\s*|\s+)p(\.)?l(\.)?l(\.)?c(\.)?$', '', string).strip()
        string = re.sub(r'(\,\s*|\s+)p(\.)?l(\.)?c(\.)?$', '', string).strip()
        string = re.sub(r'(\,\s*|\s+)l(\.)?l(\.)?c(\.)?$', '', string).strip()
        string = re.sub(r'(\,\s*|\s+)l(\.)?p(\.)?a(\.)?$', '', string).strip()
        string = re.sub(r'(\,\s*|\s+)a(\.)?p(\.)?c(\.)?$', '', string).strip()
        string = re.sub(r'(\,\s*|\s+)l(\.)?l(\.)?p(\.)?$', '', string).strip()
        string = re.sub(r'(\,\s*|\s+)l(\.)?l(\.)?o(\.)?$', '', string).strip()
        string = re.sub(r'(\,\s*|\s+)l(\.)?c(\.)?c(\.)?$', '', string).strip()
        string = re.sub(r'(\,\s*|\s+)u(\.)?s(\.)?a(\.)?$', '', string).strip()
        string = re.sub(r'(\,\s*|\s+)inc(\.)?($|\W)', '', string).strip()
        string = re.sub(r'(\,\s*|\s+)corp(\.)?($|\W)', '', string).strip()
        string = re.sub(r'(\,\s*|\s+)assc(\.)?($|\W)', ' associates', string).strip()
        string = re.sub(r'(\,\s*|\s+)l(\.)?t(\.)?d(\.)?$', '', string).strip()
        string = re.sub(r'(\,\s*|\s+)l(\.)?p(\.)?$', '', string).strip()
        string = re.sub(r'(\,\s*|\s+)p(\.)?a(\.)?$', '', string).strip()
        string = re.sub(r'(\,\s*|\s+)p(\.)?c(\.)?$', '', string).strip()
        string = re.sub(r'(\,\s*|\s+)o(\.)?d(\.)?$', '', string).strip()
        #string = re.sub(r'(\,)?\s+l(\.)$', '', string)
        #string = re.sub(r'(\,)?\s+p(\.)$', '', string)
        string = re.sub(r'(\(.*(\)|$))', '', string).strip()
        # string = re.sub(r'(\s+[a-zA-Z]\.\s+)', '', string).strip()
        string = re.sub(r'\.$', '', string).strip()
        string = re.sub(r'\-', ' ', string).strip()
        string = re.sub(r'group$', '', string).strip()
        string = re.sub(r'corporation$', '', string).strip()
        string = re.sub(r'incorporated$', '', string).strip()
        string = re.sub(r'group$', '', string).strip()
        string = re.sub(r'americas$', '', string).strip()
        string = re.sub(r'\s+us$', '', string).strip()
        string = re.sub(r'\&', 'and', string).strip()
        string = re.sub(r'\,\s+and\s+', ' and ', string).strip()
        string = re.sub(r'\s+([A-Za-z])\.?\s+', r' \1. ', string)
        string = re.sub(r'\s+', ' ', string).strip()

        return string.title().strip()
    
    result = candidate
    for i in range(n):
        result = internal(result)
    
    return result

def get_okay_hourly(h):
    def hourly_okay(v):
        return v > 7.25 and v < 5000

    h2 = h
    if hourly_okay(h2):
        return h2

    for schedule in ['Year', 'Month', 'Bi-Weekly', 'Week']:
        h2 = h / hourly_lookup[schedule]
        if hourly_okay(h2):
            return h2
    
    return 7.25

def get_okay_wage(wage, unit):    
    if unit in hourly_lookup:
        hourly = wage / hourly_lookup[unit]
    else:
        hourly = wage / hourly_lookup['Year']
    hourly = get_okay_hourly(hourly)

    yearly = hourly * hourly_lookup['Year']
    return yearly

def get_gps(string):
    location = geolocator.geocode(string)
    # print('Latitude = {}, Longitude = {}'.format(location.latitude, location.longitude))
    if location is not None:
        return location.latitude, location.longitude
    else:
        return None

def get_geojson(states):
    states = [s.lower() for s in states]
    
    json_data = {"type":"FeatureCollection","features": []}
    for fname in os.listdir('geojson'):
        if fname[:2] in states:
            data = json.load(open(f'geojson/{fname}', 'r'))
            json_data['features'].extend(data['features'])
    
    combined_json = 'geojson/combined.geojson'
    json.dump(json_data, open(combined_json, 'w'))
    
    return 'geojson/combined.geojson'

# https://stackoverflow.com/questions/48587997/matplotlib-pie-graph-with-all-other-categories
def gen_pie_chart_data(df, x_col, y_col, top):
    df = df.sort_values(y_col, ascending=False)
    df_new = df[:top].copy()
    new_row = pd.DataFrame(data = {
        x_col : ['others'],
        y_col : [df[y_col][top:].sum()]
    })
    df_new = pd.concat([df_new, new_row])
    return df_new

def find_soc_code(code_lookup, keywords):
    keywords = [kw.lower() for kw in keywords]
    good_codes = []
    for code in code_lookup:
        found = False
        for title in code_lookup[code]:
            title = title.lower()
            for kw in keywords:
                if kw in title:
                    found = True
                    good_codes.append(code)
                    break
            if found:
                break
    
    return good_codes