import pandas as pd
import pickle

from functions import geolocation_calc
from functions import routing_calc_vroom
from functions import route_evaluation

## Load route address and container data
file_name = 'data/input/Tour_data_address_data.pkl'
address_data = pd.read_pickle(file_name)
# Dates of served routes
dates_served = []
dates_served.extend(iter(address_data.keys()))

## Geo location computation of address data
# Call geolocation function
geolocation_data = geolocation_calc(address_data,
                                    dates_served)
# Save geo location dict to pickles
file_name = 'data/output/Tour_data_geolocation_data.pkl'
output = open(file_name, 'wb')
pickle.dump(geolocation_data, output)
output.close()

## Routing optimization for distance calculation
# Call routing function
routes_data = routing_calc_vroom(geolocation_data,
                                 dates_served)
# Save routes dict to pickles
file_name = 'data/output/Route_optimization_data.pkl'
output = open(file_name, 'wb')
pickle.dump(routes_data, output)
output.close()

## Route evaluation defintition of route distances
# Call evaluation function
routes_evaluation = route_evaluation(address_data,
                                              routes_data,
                                              dates_served)
# Save evaluation dict main to pickles
file_name = 'data/output/Route_evaluation_data_main'+'.pkl'
output = open(file_name, 'wb')
pickle.dump(routes_evaluation, output)
output.close()