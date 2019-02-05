
import time
import pyroslib
import traceback


def loop():
    pass


if __name__ == "__main__":
    try:
        print("Starting vl53l1x sensor service...")


        time.sleep(1)

        pyroslib.init("vl53l1x-sensor-service", unique=True)

        print("Started vl53l1x sensor service.")

        pyroslib.forever(0.02, loop)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
