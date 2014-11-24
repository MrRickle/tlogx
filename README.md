tlogx
=====

tlogx logs temperature data from DS18B20 sensors on a raspberry pi to an SQLite DataBase.
Reads all probs available, logs time & temp to the temperatures table in the SQLite db. 
The device table in db specify's... 
A freindly name that may be set for each sensor.
How often to check for temperature changes on a per sensor basis. 
How large a change is required to trigger a log entry.
How often to force a log entry even if the temperature has not changed a specified amount.

Not done!  
Needs to not crash when sensors are removed. 
Needs to auto find new sensors when they are added, with out having to restart the program

Needs additional programs
No GUI.
Settings are only editable useing an SQLite manager.

Still needs a gui to look at the data.
Still needs a control program to control zones or whatever.


