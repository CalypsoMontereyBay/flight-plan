'''
Planner.py is the "Hub" for the engine. This program puts all of the pieces together.

It is knowledgable of the other files while each module is not. 

Planner.py pulls the sun state (sun.py) and grid geometry (geo.py), then converts waypoints from
their geometric form into Waypoint objects so they can be placed into a Mission
Request object. The best corner is picked for the start of the mission route within the grid.
Then, this file returns a candidate plan that is scored.

Planner.py stitches the engine's calculations together and presents a candidate.
'''

#File Imports:
'''
import .objects
import .constants
import .geo
import .sun
import .aircraft_math


#Constants Imports:

#Constant Declarations:

'''