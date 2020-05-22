# Refuse Collection Vehicle Route Optimization

### About

This tool is based on the Open source Routing Machine (OSRM) [[1\]](#_ftn1) and Vehicle Routing Open-source Optimization Machine (Vroom) [[2\]](#_ftn2) to compute the optimal route for a set of address data. Based on the optimal route individual route distances can be determined.

### Features

1. Find optimal route of given address steps anywhere in the world. 

2. Analyze route specification and individual distances
3. Can be basis for further route synthetization for a vehicle energy demand simulation 
4. No restriction regarding number of steps, in case own docker container is set up with osrm and vroom instance

### Setup

1. Download OpenStreetMap data from your desired routing area, e.g. http://download.geofabrik.de/
2. OSM file needs to be pre-processed for osrm, see https://hub.docker.com/r/osrm/osrm-backend/
3. Final docker container should contain:
   1. osrm backend - https://hub.docker.com/r/osrm/osrm-backend/
   2. osrm frontend - https://hub.docker.com/r/osrm/osrm-frontend/
   3. vroom frontend - https://github.com/VROOM-Project/vroom-frontend

### Remark

Need of deployment of docker container including osrm&vroom - no out of the box tool!

Geo-calculation based on geopy

Further documentation on vroom can be found here https://github.com/VROOM-Project/vroom-express

[[1\]](#_ftnref1) http://project-osrm.org/

[[2\]](#_ftnref2) http://vroom-project.org/