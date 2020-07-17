from flask import Flask, jsonify, request, render_template, flash
import json
import numpy as np
import pandas as pd
import string
import pickle
import random as rand
import googlemaps

class GoogleDistanceMatrix:
    """
    A class to get distance and duration between origin and destination using google distance matrix api
    """
    
    def __init__(self):
        self.key = 'AIzaSyC9Tgj8sS2BprdRrMUZB1XEMETOxWrr8vw'
        self.client = googlemaps.Client(self.key)
    
    def getDistance(self, origin, destination):
        matrix = self.client.distance_matrix(origin, destination, units = "imperial")
        status = matrix['rows'][0]['elements'][0]['status']
        if status != 'OK': 
            # return a very large distance if status not ok
            return 10000
        else:
            distance =  matrix['rows'][0]['elements'][0]['distance']['text']#.strip('mi').strip()
            if ('ft' in distance):
                return float(distance.strip('ft').strip())/5280
            return float(distance.strip('mi').strip())
        
    def getDuration(self, origin, destination):
        matrix = self.client.distance_matrix(origin, destination, units = "imperial")
        status = matrix['rows'][0]['elements'][0]['status']
        if status != 'OK':
            # return a very large time interval if status not ok
            result = 10000
        else:
            interval =  matrix['rows'][0]['elements'][0]['duration']['text'] #.strip("mins").strip()
            if 'day' in interval:
                result = 10000
            else:
                if 'hours' in interval:
                    res = interval.strip('mins').split('hours')
                    result =  float(res[0])*60 + float(res[1])
                elif 'hour' in interval:
                    res = interval.strip('mins').split('hour')
                    result =  60 + float(res[1])
                else:
                    result = float(interval.strip('mins').strip())
        return result

def findNearestByDistance(address, isAddressGPS, index, df, distance = 10):
    '''
    Return the dataframe indices of all parks within a distance from provided address.
    Inputs: index of the target trail in park dataframe, distance in miles, and  park dataframe.
    Output: a list containing indexes of all parks within the distance from provided location
    '''
    indices = []
    gmd = GoogleDistanceMatrix()
    origin = address
    for ind, row in df.iterrows():
        if isAddressGPS:
            destination = (row.GPS_latitude, row.GPS_longitude)
        else:
            destination = row.address
        if  ind != index and gmd.getDistance(origin, destination) <= distance:
            indices.append(ind)
    return indices    

def findNearestByTime(address, isAddressGPS, index, df, duration = 30):
    '''
    Return the dataframe indices of all parks within 'duration' mins of drive from current location
    Inputs: index of the target trail in park dataframe, distance in miles, and  park dataframe.
    Output: a list containing indexes of all parks within 'duration' mins of drive from current location
    '''
    indices = []
    gmd = GoogleDistanceMatrix()
    origin = address
    for ind, row in df.iterrows():
        if isAddressGPS:
            destination = (row.GPS_latitude, row.GPS_longitude)
        else:
            destination = row.address
        if ind != index and gmd.getDuration(origin, destination) <= duration:
            indices.append(ind)
    return indices      

def findSimilarParkByDistance(city, name, k = 3, distance = 10):
    '''
    Find top k parks based on user inputs.
    Function will prbased int out the top parks names and their yelp links.
    Function will return a dataframe with information of the top parks.
    '''

    # find the row index of the park in original dataframe df
    # please make sure that the index of the dataframe df is 0, 1, 2, 3...
    if city in list(data["parks"]["park"].city) and name in list(data["parks"]["park"].name):
        i = list(data["parks"]["park"][(data["parks"]["park"].city == city) & (data["parks"]["park"].name == name)].index)[0]
        candidates = findNearestByDistance(data["parks"]["park"].address[i], False, i, data["parks"]["park"], distance)
        similarity = pd.DataFrame(data["parks"]["similarity"][i], columns = ['score'])
        similarity = similarity.iloc[candidates].nlargest(k, ['score'])
        top_parks = data["parks"]["park"].iloc[list(similarity.index)]

    # n = 1
    # for ind, row in top_parks.iterrows():
    #     print(str(n) + '. ' + row['name'])
    #     print('   ' + row['address'])
    #     print('   ' + row['link'])
    #     n += 1
    
    return top_parks

def findSimilarParkByTime(city, name, k = 4, duration = 20):
    '''
    Find top k trails based on user inputs.
    Function will prbased int out the top trail names and their web links.
    Function will return a dataframe with information of the top trails.
    '''

    # find the row index of the trail in original dataframe df
    # please make sure that the index of the dataframe df is 0, 1, 2, 3...
    if city in list(data["parks"]["park"].city) and name in list(data["parks"]["park"].name):
        i = list(data["parks"]["park"][(data["parks"]["park"].city == city) & (data["parks"]["park"].name == name)].index)[0]
        candidates = findNearestByTime(data["parks"]["park"].address[i], False, i, data["parks"]["park"], duration)
        similarity = pd.DataFrame(data["parks"]["similarity"][i], columns = ['score'])
        similarity = similarity.iloc[candidates].nlargest(k, ['score'])
        top_parks = data["parks"]["park"].iloc[list(similarity.index)]

    # n = 1
    # for ind, row in top_parks.iterrows():
    #     print(str(n) + '. ' + row['name'])
    #     print('   ' + row['address'])
    #     print('   ' + row['link'])
    #     n += 1
    
    return top_parks


def findParkByUserInputs(city, how_popular = 'l', how_features = 'mountain', how_shade = 'y', how_far_long = 10, isDistance = True, k = 10):
    '''
    Find top k parks within a distance/duration from target park.
    Function will print out the top park names and their web links sorted by user rating.
    Function will return a dataframe with information of the top parks.
    '''

    # address for the city
    origin = city + ', CA'

    # how far
    indexes = []
    gmd = GoogleDistanceMatrix()
    if isDistance:
        for ind, row in park.iterrows():       
            if gmd.getDistance(origin, data["parks"]["park"]['address'][ind]) <= how_far_long:
                indexes.append(ind)
        tops = data["parks"]["park"].iloc[indexes]
    else:
        for ind, row in park.iterrows():       
            if gmd.getDuration(origin, data["parks"]["park"]['address'][ind]) <= how_far_long:
                indexes.append(ind)
        tops = data["parks"]["park"].iloc[indexes]

    # popularity
    midpoint = tops.review_count.median()
    if how_popular == 'l':
        tops = tops[tops.review_count < midpoint]
    else:
        tops = tops[tops.review_count >= midpoint]

    # feature
    tops['feature_count'] = tops.reviews.apply(lambda x: x.count(how_features) if type(x) == str else 0)
    if tops.feature_count.max() < 2:
        print()
        print('"' + how_features + '"' + ' is not found and is ignored.')
    else:
        tops = tops[tops.feature_count >= 2]

    # shades
    if how_shade == 'y':
        tops['shade_count'] =  tops.reviews.apply(lambda x: x.count('shade') if type(x) == str else 0)
        if tops.shade_count.max() < 2:
            print()
            print('shade' + ' is not found and is ignored.')
        else:
            tops = tops[tops.shade_count >= 2]

    tops.sort_values(by = 'rating', ascending = False, inplace = True) 
    # n = 1

    # for ind, row in tops.iterrows():
    #     print(str(n) + '. ' + row['name'] + ', rated ' + str(row.rating))
    #     print('   ' + row['address'])
    #     print('   ' + row['link'])
    #     n += 1
    #     if n > k:
    #         break
    
    return tops


def findSimilarTrailByDistance(city, name, k = 6, distance = 10):
    '''
    Find top k trails based on user inputs.
    Function will prbased int out the top trail names and their web links.
    Function will return a dataframe with information of the top trails.
    '''

    # find the row index of the trail in original dataframe df
    # please make sure that the index of the dataframe df is 0, 1, 2, 3...
    if city in list(data["trails"]["trail_review_only"].city) and name in list(data["trails"]["trail_review_only"].name):
        # target trail has review and belongs to df_review_only
        i = list(data["trails"]["trail_review_only"][(data["trails"]["trail_review_only"].city == city) & (data["trails"]["trail_review_only"].name == name)].index)[0]
        address = (data["trails"]["trail_review_only"]['GPS_latitude'][i], data["trails"]["trail_review_only"]['GPS_longitude'][i])
        candidates = findNearestByDistance(address, True, i, data["trails"]["trail_review_only"], distance)
        similarity = pd.DataFrame(data["trails"]["similarity_with_review_only"][i], columns = ['score'])
        similarity = similarity.iloc[candidates].nlargest(k, ['score'])
        tops = data["trails"]["trail_review_only"].iloc[list(similarity.index)]

    else:
        # target trail has no review and belongs to df
        i = list([(data["trails"]["trail"].city == city) & (data["trails"]["trail"].name == name)].index)[0]
        address = (data["trails"]["trail"]['GPS_latitude'][i], data["trails"]["trail"]['GPS_longitude'][i])
        candidates = findNearestByDistance(address, True, i, data["trails"]["trail"], distance)
        similarity = pd.DataFrame(data["trails"]["trail"]["similarity_no_review"][i], columns = ['score'])
        similarity = similarity.iloc[candidates].nlargest(k, ['score'])
        tops = data["trails"]["trail"].iloc[list(similarity.index)]

    # n = 1

    # for ind, row in tops.iterrows():
    #     print(str(n) + '. ' + row['name'])
    #     print('   ' + row['link'])
    #     n += 1
    
    return tops


def findSimilarTrailByTime(city, name, k = 6, duration = 20):
    '''
    Find top k trails based on user inputs.
    Function will prbased int out the top trail names and their web links.
    Function will return a dataframe with information of the top trails.
    '''

    # find the row index of the trail in original dataframe df
    # please make sure that the index of the dataframe df is 0, 1, 2, 3...
    if city in list(data["trails"]["trail_review_only"].city) and name in list(data["trails"]["trail_review_only"].name):
        # target trail has review and belongs to df_review_only
        i = list(data["trails"]["trail_review_only"][(data["trails"]["trail_review_only"].city == city) & (data["trails"]["trail_review_only"].name == name)].index)[0]
        address = (data["trails"]["trail_review_only"]['GPS_latitude'][i], data["trails"]["trail_review_only"]['GPS_longitude'][i])
        candidates = findNearestByTime(address, True, i, data["trails"]["trail_review_only"], duration)
        similarity = pd.DataFrame(data["trails"]["similarity_with_review_only"][i], columns = ['score'])
        similarity = similarity.iloc[candidates].nlargest(k, ['score'])
        tops = data["trails"]["trail_review_only"].iloc[list(similarity.index)]

    else:
        # target trail has no review and belongs to df
        i = list([(data["trails"]["trail"].city == city) & (data["trails"]["trail"].name == name)].index)[0]
        address = (data["trails"]["trail"]['GPS_latitude'][i], data["trails"]["trail"]['GPS_longitude'][i])
        candidates = findNearestByTime(address, True, i, data["trails"]["trail"], duration)
        similarity = pd.DataFrame(data["trails"]["trail"]["similarity_no_review"][i], columns = ['score'])
        similarity = similarity.iloc[candidates].nlargest(k, ['score'])
        tops = data["trails"]["trail"].iloc[list(similarity.index)]

    # n = 1

    # for ind, row in tops.iterrows():
    #     print(str(n) + '. ' + row['name'])
    #     print('   ' + row['link'])
    #     n += 1
    
    return tops


def findTrailByUserInputs(city, how_difficult = 'e', how_popular = 'l', how_shades = 'y', 
                    how_features = 'mountain', how_far_long = 10, isDistance = True, k = 10):
# findTrailByUserInputs(city_to_go, how_difficult, how_popular, how_shades, 
#                     how_features, how_long, False)
    '''
    Find top k trails within a distance from target trail.
    Function will print out the top trail names and their web links sorted by user rating.
    Function will return a dataframe with information of the top trails.
    '''
    # find city GPS coordinates by averaging all trails that belong to the city
    city_lon = data["trails"]["trail"][data["trails"]["trail"].city == city].GPS_longitude.mean()
    city_lat = data["trails"]["trail"][data["trails"]["trail"].city == city].GPS_latitude.mean()
    origin = (city_lat, city_lon)

    # how far
    indexes = []
    gmd = GoogleDistanceMatrix()
    if isDistance:
        for ind, row in data["trails"]["trail"].iterrows():       
            if gmd.getDistance(origin, (data["trails"]["trail"]["GPS_latitude"][ind],data["trails"]["trail"]["GPS_longitude"][ind])) <= how_far_long:
                indexes.append(ind)
        tops = data["trails"]["trail"].iloc[indexes]
    else:
        for ind, row in data["trails"]["trail"].iterrows():       
            if gmd.getDuration(origin, (data["trails"]["trail"]["GPS_latitude"][ind],data["trails"]["trail"]["GPS_longitude"][ind])) <= how_far_long:
                indexes.append(ind)
        tops = data["trails"]["trail"].iloc[indexes]
    if tops.shape[0] < 3:
        print('\nToo few places satisfy the criteria of distance, search criteria expanded.')
        indexes = []      
        if isDistance:
            for ind, row in data["trails"]["trail"].iterrows():       
                if gmd.getDistance(origin, (data["trails"]["trail"]["GPS_latitude"][ind],data["trails"]["trail"]["GPS_longitude"][ind])) <= 15:
                    indexes.append(ind)
            tops = data["trails"]["trail"].iloc[indexes]
        else:
            for ind, row in data["trails"]["trail"].iterrows():       
                if gmd.getDuration(origin, (data["trails"]["trail"]["GPS_latitude"][ind],data["trails"]["trail"]["GPS_longitude"][ind])) <= 30:
                    indexes.append(ind)
            tops = data["trails"]["trail"].iloc[indexes]

    # difficulty
    tmp = tops.copy()
    if how_difficult == 'e':
        tops = tops[tops.difficulty == 'easy']
    elif how_difficult == 'm':
        tops = tops[tops.difficulty == 'moderate']
    elif how_difficult == 'h':
        tops = tops[tops.difficulty == 'hard']
    if tops.shape[0] < 3:
        print('\nToo few places satisfy the criteria of difficulty, search criteria expanded.')
        tops = tmp.copy()

    # # popularity
    tmp = tops.copy()
    midpoint = tops.reviewCount.median()
    if how_popular == 'l':
        tops = tops[tops.reviewCount < midpoint]
    elif how_popular == 'm':
        tops = tops[tops.reviewCount >= midpoint]
    if tops.shape[0] < 3:
        tops = tmp.copy()

    # shades
    tmp = tops.copy()
    if how_shades == 'y':
        tops = tops[tops.shades_mentions >= 3]
    elif how_shades == 'n':
        tops = tops[tops.shades_mentions < 3]
    if tops.shape[0] < 3:
        print('\nToo few places satisfy the criteria of shades, search criteria expanded.')
        tops = tmp.copy()

    # feature
    if how_features != 'no preference':
        tmp = tops.copy()
        # first check features column
        tops['user_feature'] = tops.features.apply(lambda x: how_features in x)
        if tops.user_feature.sum() > 0:
            tops = tops[tops.user_feature == True]
        # then try to search in review texts
        else:
            tops.drop(columns = ['user_feature'])
            tops['featureCount'] = tops.reviews.apply(lambda x: x.count(how_features) if type(x) == str else 0)
            if tops.featureCount.max() < 2:
                print('\nToo few places satisfy the criteria '  + '"' + how_features + '"' + ', search criteria expanded.')
            else:
                tops = tops[tops.featureCount >= 2]    
        if tops.shape[0] < 1:
            print('\nToo few places satisfy the criteria '  + '"' + how_features + '"' + ', search criteria expanded.')
            tops = tmp.copy()

    # print results
    tops = tops.sort_values(by = 'rating', ascending = False) 
    # n = 1
    # print('\nHere are the top trails near your location, sorted by user ratings:\n')
    # for ind, row in tops.iterrows():
    #     print(str(n) + '. ' + row['name'] + ', rated ' + str(row.rating))
    #     print('   ' + row['link'])
    #     n += 1
    #     if n > k:
    #         break

    return tops


# read trail data
trail = pd.read_pickle('../data/trails_bayarea')
trail_review_only = pd.read_pickle('../data/df_review_only')
similarity_with_review_only = np.loadtxt('../data/similarity_with_review_only.csv', delimiter = ',')
similarity_no_review = np.loadtxt('../data/similarity_no_review.csv', delimiter = ',')
# read park data
park = pd.read_csv('../data/parks.csv').reset_index(drop = True)
similarity_park = np.loadtxt('../data/similarity_parks.csv', delimiter = ',')
# store them in a dictionary
data = {"trails":{}, "parks":{}, "gym":{}}
data["trails"] = {"trail":trail, 
                  "trail_review_only":trail_review_only,
                  "similarity_with_review_only":similarity_with_review_only,
                  "similarity_no_review":similarity_no_review}
data["parks"] = {"park":park, "similarity":similarity_park}
data["parks"]["park"]["city"] = data["parks"]["park"].address.map(lambda x: x.lower().split(',')[-2].strip())

app = Flask(__name__)
place_info = {'type':'park', 'has_favorite':True, 'is_distance':True, 'far_long':0, 'city': "", 'places_list':[]}


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/select', methods = ['POST'])
def select():
    place_type = request.form['type'].lower()
    global place_info
    place_info['type'] = place_type

    if place_type not in ['trail', 'park', 'gym']:
      place_type = rand.choice(['TRAIL', 'PARK', 'GYM'])   

    return render_template('select.html', place = place_type)


@app.route('/place', methods = ['POST'])
def place():
    global place_info
    favor = request.form['YESorNO']
    place_info['has_favorite'] = favor
    return render_template('place.html',favor = favor, place = place_info['type'].lower())


@app.route('/place/wf', methods = ['POST'])
def wf():
    city = request.form['city'].lower()
    global place_info
    if (place_info['type'] == 'park'):
        city_set = set(data['parks']['park'].city)
        if city in city_set:
            place_info['city'] = city
            parks_list = []
            place_info['places_list'] = []
            for name in list(data["parks"]["park"].name[data["parks"]["park"].city == city]):
                parks_list.append(name)
                place_info['places_list'].append(name)
            return render_template('place_wf.html', places_list = parks_list, place = place_info['type'].lower(), city = city)
        return render_template('place.html', favor = 'YES', place = place_info['type'].lower())
    else:
        city_set = set(data['trails']['trail'].city)
        if city in city_set:
            place_info['city'] = city
            # generate the list of places in the city
            trails_list = []
            place_info['places_list'] = []
            print(len(list(data["trails"]["trail"].name[data["trails"]["trail"].city == city])))
            for name in list(data["trails"]["trail"].name[data["trails"]["trail"].city == city]):
                trails_list.append(name)
                place_info['places_list'].append(name)
            return render_template('place_wf.html', places_list = trails_list, place = place_info['type'].lower(), city = city)
        return render_template('place.html', favor = 'YES', city = city)

@app.route('/place/wf/result', methods = ['POST'])
def wf_result():
    distance = int(request.form['distance_time'])
    time = distance
    choice = int(request.form['choice'])-1
    metric = request.form['metric']
    isDistance = True
    if metric == 'minutes':
        isDistance = False
    if (place_info['type'] == 'park'):
        if (isDistance):
            tops = findSimilarParkByDistance(city = place_info['city'], name = place_info['places_list'][choice], k = 3, distance = distance)
        else:
            tops = findSimilarParkByTime(city = place_info['city'], name = place_info['places_list'][choice], k = 3, duration = time)
    else:
        if (isDistance):
            tops = findSimilarTrailByDistance(city = place_info['city'], name = place_info['places_list'][choice], k = 3, distance = distance)
        else:
            tops = findSimilarTrailByTime(city = place_info['city'], name = place_info['places_list'][choice], k = 3, duration = time)
    n = 1
    top_names = []
    for ind, row in tops.iterrows():
        top_name = []
        top_name.append(row['name'])
        top_name.append(row['link']) 
        top_name.append(str(row['rating']))
        top_names.append(top_name)
        n += 1
        if n > 10:
            break
    return render_template('place_wf_result.html', top_names= top_names, place = place_info['type'].lower())


@app.route('/place/nf', methods = ['POST'])
def nf():
    return render_template('place_nf.html', city_not_found = "", place = place_info['type'].lower())


@app.route('/place/nf/result', methods = ['POST'])
def nf_result():
    city = request.form['city'].lower()
    city_set = set(data['parks']['park'].city)
    if city not in city_set:
        city_not_found = "Note: fail to find the city you entered, please try again"
        return render_template('place_nf.html', city_not_found = city_not_found, place = place_info['type'].lower())
    if  place_info['type'].lower() == 'trail':
        difficulty_level = request.form['difficulty'] 
        if difficulty_level == 'easy':
            how_difficult = 'e'
        elif difficulty_level == 'moderate':
            how_difficult = 'm'
        else:
            how_difficutl = 'h'
    popularity = request.form['popularity']
    shade = request.form['shade']
    feature = request.form['feature'].lower().strip()
    distance = int(request.form['distance_time'])
    time = distance
    metric = request.form['metric']
    isDistance = True
    if metric == 'minutes':
        isDistance = False
    if (place_info['type'] == 'park'):
        if isDistance:
            tops = findParkByUserInputs(city, popularity, shade, feature, 
                         distance, isDistance = True, k = 3)
        else:
            tops = findParkByUserInputs(city, popularity, shade, feature, 
                         time, isDistance = False, k = 3)
    else:
        if isDistance:
            tops = findTrailByUserInputs(city, how_difficult, popularity, shade, 
                    feature, distance, isDistance = True)
        else:
            tops = findTrailByUserInputs(city, how_difficult, popularity, shade, 
                    feature, time, isDistance = False)
    n = 1
    top_names = []
    for ind, row in tops.iterrows():
        top_name = []
        top_name.append(row['name'])
        top_name.append(row['link']) 
        top_name.append(str(row['rating']))
        top_names.append(top_name)
        n += 1
        if n > 10:
            break

    return render_template('place_nf_result.html', top_names= top_names, place = place_info['type'].lower())


if __name__ == "__main__":
    app.run(debug=True, host='127.0.0.1', port=5000)
