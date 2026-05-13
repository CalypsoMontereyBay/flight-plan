

'''
This file contains all the geographic math currently needed for V1 of the flight planning
engine. It contains the following functions (descriptions soon to follow):

        1. normalize_heading(heading_deg)
        2. destination_point(start_lon, start_lat, heading_deg, distance_km)
        3. bearing_between(point A, point B)
        4. distance_between(point A, point B)
        5. make_line_through_point(center_point, heading_deg, length_km)
        6. offset_lie(line, offset_heading_deg, offset_km)
        7. make_lawnmower_grid_through_m1()
'''
