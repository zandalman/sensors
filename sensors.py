from sensor_classes import *

if __name__ == "__main__":
    logger = Logger("example")
    logger.connect(**parse_config("config.config"))
    sensors = [MOTBox("MOTBox", "/dev/cu.usbmodem69511901", print_m=True)]
    logger.add_sensors(sensors)
    while True:
        logger.generate_body()
        logger.upload()
