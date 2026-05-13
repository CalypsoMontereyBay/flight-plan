

'''
For the first build of the engine, this file will hold all of the constants used/assumed.

    1. We use these assumed "constants" in order to prove the engine works.

    2. We will be assuming the aircraft type, and therefore, its properties.

    3. We will also be assuming permanently clear skies on January 1st 2026 for now.

    4. The coordinates of the M1 Mooring station are also found here and will be used
    even after the first eversion of the engine works.
    
    5. Legal status for now is assumed to be true (Legal).
    
    6. Flight path constants like altitude, line lengths, etc are also found her for now.
    
    7. We are also ignoring wind in version 1.
'''

# M1 Mooring station coordinates are defined below:

M1_MOORING_LONG = -122.020
M1_MOORING_LAT = 36.750

# Engine Version 1 constants are defined below:

V1_DEFAULT_MISSION_DAY_OF_YEAR = 1

V1_DEFAULT_MISSION_CLOUD_COVER = 0

V1_DEFAULT_LEGAL_STATUS = True

V1_DEFAULT_AIRCRAFT_ALTIUDE_m = 118 #Units = m. 118m = ~385 FT.

V1_DEFAULT_LINE_LENGTH_km = 2 #Units = km. 2 km = ~6562 FT.

V1_DEFAULT_LINE_SPACING_km = 0.15 #Units = km. 0.15 km = ~500 FT.

V1_DEFAULT_GRID_WIDTH_km = 2.5 #Units = km. 2.5 km = ~1.55 MI -> ~8202 FT.

# Engine Version 1 aircraft defailts are defined below:

#AIRCRAFT PARAMS ARE DEFINED WITH RESPECT TO THE BLACKSWIFT S2 FIXED-WING UAV

BLACKSWIFT_ENDURANCE_min = 90 #Units = minutes

BLACKSWIFT_WIND_RATING_ms = 15 #Units = m/s

BLACKSWIFT_CLIMB_RATE_ms = 3.35 #Units = m/s

BLACKSWIFT_DESCENT_RATE_ms = 1.80 #Units = m/s

BLACKSWIFT_TURN_RADIUS_m = 57 #Units = m

BLACKSWIFT_TURN_PENALTY_s = 10 #Units = seconds

BLACKSWIFT_MIN_GROUND_SPEED_ms = 12 #Units = m/s

BLACKSWIFT_CRUISE_SPEED_ms = 18 #Units = m/s



