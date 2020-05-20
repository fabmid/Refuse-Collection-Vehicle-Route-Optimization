import numpy as np
import pandas as pd
import pickle
from geopy.geocoders import Photon
from ratelimit import limits, sleep_and_retry
from geopy.exc import GeocoderTimedOut
import requests
import json

def geolocation_calc(address_data, dates_served):
    '''
    Defines the geolocation of address data.
    Used module: geopy-package
    Further Info on rate_limit:
        https://www.fintu.ai/en/working-with-geodata-in-python/

    Parameter:
        address_data: dict. address data with postal code, street name and number
        dates_served: list. Dates of served routes

    Returns:
        address data with geo locations
    '''

    ## Geo location determination
    ## define geopy geocoder functions
    geolocator = Photon(user_agent="user@mail.de")

    @sleep_and_retry
    @limits(1,1)
    def rate_limited_geocode(query):
        try:
            coordinates = geolocator.geocode(query, timeout = 60)

        except GeocoderTimedOut:# as e:
            print("Error: geocode failed on input %s with message %s")

        return coordinates

    def geocode(data,row):
        # Formulates query: address, Number, postal code
        query = data.iloc[row][1] + "," + data.iloc[row][0].split()[0]
        # Compute gelocation with rate limited
        geocode = rate_limited_geocode(query)

        return geocode

    # Define dict to store geolocation data
    geolocation_data_dict_main = {}

    for i in range (0,len(dates_served)):
        print('geo location calculation:', dates_served[i])
        #Load each day tour
        data_filtered = address_data[dates_served[i]]
        #Prepare address data for geo location and distance calc
        data = data_filtered['address'].str.split(',', expand=True)

        ## calculate coordinates for given address data
        geolocation_data_dict = {}
        lat=[]
        lng=[]
        address=[]

        for j in range(0,len(data)):
            #geo location calculation
            location = geocode(data,j)
            #check if geo location can be calculated
            if location != None:
                address.append(data.iloc[j][1] +','+ data.iloc[j][0].split()[0])
                lat.append(location.latitude)
                lng.append(location.longitude)
            else:
                print("No geocode found for",data.iloc[j][1] +','+ data.iloc[j][0].split()[0] )
                address.append(data.iloc[j][1] +','+ data.iloc[j][0].split()[0])
                lat.append('No loc')
                lng.append('No loc')

        #save address plus added geo-data to pandas dataframe/dict
        address_geo_data = pd.DataFrame({'address':address,
                                         'lat':lat,
                                         'lng':lng}, \
                                         columns = ['address','lat','lng'])
        geolocation_data_dict[dates_served[i]] = address_geo_data

        ## Update main address_data_dict with all address data processed
        geolocation_data_dict_main.update(geolocation_data_dict)

    return geolocation_data_dict_main


def routing_calc_vroom(geolocation_data_dict_main, dates_served):
    '''
    Computes optimized route on local Vroom express server on http://localhost:3000/.
    Query is done via Vroom Express API, which sends via Vroom backend table request to osrm backend server.
    osrm returns for table request duration matrix. Therefore optimal route is defined as fastest (time) route.
    Distances between all waypoints of route are returned as well.
    All servers run locally in docker containers. Docker containers need to be defined and accesable.

    For Vroom Express API documentation:
        https://github.com/VROOM-Project/vroom/blob/master/docs/API.md

        Input:
            The problem description is read from standard input or from a file
            (using -i) and should be valid json formatted as follow.

            jobs 	    array of job objects describing the places to visit
            vehicles 	array of vehicle objects describing the available vehicles
            [matrix] 	optional two-dimensional array describing a custom matrix

        Note:
            the expected order for all coordinates arrays is [lon, lat]
            all timings are in seconds
            all distances are in meters
            a time_window object is a pair of timestamps in the form [start, end]

        Define a vehicle object:
            id 	an integer used as unique identifier
            [profile]       routing profile (defaults to car)
            [start] 	    coordinates array
            [start_index] 	index of relevant row and column in custom matrix
            [end] 	        coordinates array
            [end_index] 	index of relevant row and column in custom matrix
            [capacity] 	    an array of integers describing multidimensional quantities
            [skills] 	    an array of integers defining skills for this vehicle
            [time_window] 	a time_window object describing working hours for this vehicle

        Define a job object:
            id 	an integer used as unique identifier
            [location] 	        coordinates array
            [location_index] 	index of relevant row and column in custom matrix
            [service] 	        job service duration (defaults to 0)
            [amount] 	        an array of integers describing multidimensional quantities
            [skills] 	        an array of integers defining mandatory skills for this job
            [time_windows] 	    an array of time_window objects describing valid slots for job service start

        Post request on local Vroom express api:
            https://github.com/VROOM-Project/vroom-express
        For details on request libary check:
            https://github.com/requests

    Parameters:
        geolocation_data_dict_main: dict. address data with geo locations
        dates_served: list. Dates of served routes

    Returns:
        dict. Computed Optimized route with duration and distance between all route steps
    '''

    # Define dict to store route data
    routes_data_dict_main = {}

    for i in range (0,len(dates_served)):

        routes_data_dict = {}

        # Constructing Vroom query
        address_data = geolocation_data_dict_main[dates_served[i]]
        address_data = address_data.reset_index(drop=True)

        # Copy latitude and longitude value of each route into address_coordinates_list (input query)
        address_coordinates_list = list()
        for j in range (0,len(address_data)):
            lat = address_data['lat'][j]
            lon = address_data['lng'][j]
            address_coordinates_list.append([lon,lat])

        # Depot location
        lon_depot = 13.369444
        lat_depot = 52.52
        # Service time [seconds] - optional
        service_time = 0

        # Create query dict
        input_file = {}
        # Add vehicle object as list to dict
        input_file = {"vehicles": [{"id": 1,
                                    "start": [lon_depot, lat_depot],
                                    "end": [lon_depot, lat_depot]
                                  }]
                     }
        # Add job object as list to dict
        # Each row of address_coordinates_list ist added as individual job.
        input_file["jobs"] = []
        for k in range(0, len(address_coordinates_list)):
            input_file["jobs"].append({"id": k,
                                       "service": service_time,
                                       "location": address_coordinates_list[k]
                                       })
        # Add options object as dict to dict
        options = {}
        options["options"] = {"g": True}
        # Add options dict to main input_file dict
        input_file.update(options)

        '''
        # Save constructed query dict as json
        with open('data/output/optimization/json_query/'+dates_served[i].split()[0] \
                  +'_query.json', 'w') as json_file:
            json.dump(input_file, json_file)
        '''

        # Define the Vrrom-express API endpoint
        api_endpoint = 'http://localhost:3000/'

        # Post request to Vroom express - Get optimized tour data
        # query needs to be json - for details on query format check: https://github.com/VROOM-Project/vroom-express
        r = requests.post(api_endpoint, json=input_file)
        print('routing:', dates_served[i], r.ok)

        # Convert route matrix json format
        results_matrix = r.json()
        '''
        # Save results matrix to dict
        routes_data_dict = results_matrix

        # Save address dict with geo locations to pickles
        file_name = 'data/output/optimization/routes/'+dates_served[i].split()[0] \
                    +'_'+'route_data'+'.pkl'
        output = open(file_name, 'wb')
        pickle.dump(routes_data_dict, output)
        output.close()
        '''
        # Update route_data_dict main to store all route data
        routes_data_dict_main[dates_served[i]] = results_matrix

    return routes_data_dict_main


def route_evaluation(address_data_dict_main, routes_data_dict_main, dates_served):
    '''
    Function to evaluate the route matrix returned by Vroom and
    calculate number of stops by defined minimal distance between stops.

    Parameters:
        address_data_dict_main: dict. With all unordered route data including container data
        route_data_dict_main: dict. Ordered optimized route points with geo locations
        dates_served: list. Dates of served routes

    Returns:
        route_evaluation_dict: dict. Following evaluation parameters:
            'overall_distance'      [m] oberall trip distance
            'distance_there'        [m] distance from recycling plant to first collection address point
            'distance_collection'   [m] distance from first to last collection address point
            'distance_back'         [m] distance from last collection address point back to recycling plant
            'containers_sum_all     [1] Number of collected container
            'stops_sum'             [1] Number of vehicle stops during collection phase
            'container_mass'        [kg] Mean mass of waste container
    '''

    # Define dict to store evaluation results
    route_evaluation_dict_main = {}

    for i in range (0, len(dates_served)):

        route = routes_data_dict_main[dates_served[i]]

        ## Distance df with all distance values of collection phase and the distance between two consecutive stops
        collection_distance_list = []
        collection_distance_difference_list = []
        for j in range (1,(len(route['routes'][0]['steps'])-1)):
            # Take distance value from step
            collection_distance_list.append(route['routes'][0]['steps'][j]['distance'])
            # Distance difference between stop and next stop
            collection_distance_difference_list.append(-(route['routes'][0]['steps'][j]['distance'])\
                                                       +(route['routes'][0]['steps'][j+1]['distance']))

        # Merge the two lists into distance dataframe
        collection_distance_df = pd.DataFrame({'collection_distance_list':collection_distance_list,
                                               'collection_distance_difference_list':collection_distance_difference_list})

        ## Identify number of physical stops
        min_distance_base = 30
        min_distance = min_distance_base
        collection_distance_stops_list = []
        for k in range (0,len(collection_distance_df)):
            # Distance to next stop is below threshold
            if collection_distance_df['collection_distance_difference_list'][k] < min_distance:
                # Vehicle does not stop and drives further to next stop
                collection_distance_stops_list.append(0)
                # Distance threshold reduces with distance value
                min_distance = min_distance - collection_distance_df['collection_distance_difference_list'][k]

            # Distance to next stop is above threshold
            else:
                # Vehicle does stop
                collection_distance_stops_list.append(collection_distance_df['collection_distance_list'][k])
                # Distance threshold is set back to initial value
                min_distance = min_distance_base

        # Update collection_distance_stop_list into collection_distance_df
        collection_distance_df['collection_distance_stops'] = collection_distance_stops_list

        ## Collect all evaluation parameters
        route_evaluation_dict = {}
        print('route evaluation main', dates_served[i])

        route = routes_data_dict_main[dates_served[i]]
        address_num = len(route['routes'][0]['steps'])

        ## Main route evaluation
        route_evaluation_dict['overall_distance'] = route['routes'][0]['distance']
        route_evaluation_dict['distance_there'] = (route['routes'][0]['steps'][1]['distance'])
        route_evaluation_dict['distance_collection'] = (route['routes'][0]['steps'][address_num-2]['distance']) \
                                                        -(route['routes'][0]['steps'][1]['distance'])
        route_evaluation_dict['distance_back'] = (route['routes'][0]['steps'][address_num-1]['distance']) \
                                                  -(route['routes'][0]['steps'][address_num-2]['distance'])
        # Number of collected container
        route_evaluation_dict['containers_sum'] = sum(address_data_dict_main[dates_served[i]]['container_number'])
        # Mass of waste container
        route_evaluation_dict['containers_mass'] = np.mean(address_data_dict_main[dates_served[i]]['container_mass'])

        # Get number of stops from detailed evaluation function
        stops = collection_distance_df['collection_distance_stops']
        route_evaluation_dict['stops_sum'] = np.count_nonzero(stops)


        # Update main dict
        route_evaluation_dict_main[dates_served[i]] = route_evaluation_dict

    return route_evaluation_dict_main