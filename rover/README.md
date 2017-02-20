All code that should be executed on rover should go in here. Mostly services to be uploaded to PyROS.

Services are ending with *_service.py, while libraries are subdirs ending with *lib with
python file of same name and __init__.py that imports all from the python file. That way
other services can reference library in import.

upload-all.sh is convenience shell script to upload all needed services in one go to the rover.
