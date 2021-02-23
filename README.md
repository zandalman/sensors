# Sensors

A unified sensor code for uploading sensor data from a Raspberry Pi to InfluxDB.

## Create a config file

For security reasons, you should use a config file to store sensitive information about your database. The built-in function `parse_config` reads config files structured like this and returns a dictionary.

    [influxdb]
    url = DATABASE_SERVER_URL
    port = DATABASE_PORT_NUMBER
    username = DATABASE_USERNAME
    password = DATABASE_PASSWORD
    database = DATABASE_NAME
    
## Set up logger object

You need to initialize a `Logger` object to connect to the database client. Once you initialize the `Logger` object, you can add `Sensor` objects.

1. Initialize a `Logger` object. The object requires a name as an argument. All sensors associated with the Logger object will appear as seperate fields under this name in InfluxDB.
2. Call `Logger.connect` to connect to the client. The method requires all of the information in the config file as arguments. Optionally, you can specify a custom directory for writing files if the connection to the client fails using the `backup_dir` keyword argument.
3. Initialize the `Sensor` objects. All Arduino-based sensors require the board port as a keyword argument. All Raspberry Pi-based sensors require the GPIO pin as a keyword argument. If you want to print the measurements from a `Sensor` object, pass `print_m=True` as a keyword argument.
4. Call `Logger.add_sensors` and pass the sensors as arguments to add the sensors to the `Logger` object.

        logger = Logger(LOGGER_NAME) # step 1
        logger.connect(**parse_config(), backup_dir=PATH_TO_BACKUP_DIRECTORY) # step 2
        sensor = Test_Sensor(SENSOR_NAME, print_m=True) # step 3
        logger.add_sensors(sensor) # step 4

## Data collection

You will need to create a loop to collect and upload the data. In each iteration of the loop, you will need to use two methods of the `Logger` object.

1. `Logger.generate_body` reads from all sensors and creates a datapoint.
2. `Logger.upload` uploads all unuploaded data points to the database.

## Recovering backup data

To recover backup data, call `Logger.upload_backups`.

## Defining a new sensor class

If you want to use this code with a sensor which does not appear in `sensor_classes.py`, you will need to create a new sensor class. In `sensor_classes.py`, create a new sensor class. If the sensor is an Arudino-based sensor, inherit from the class `Arduino_Sensor`. If the sensor is a Raspberry-Pi based sensor, inherit from the class `Pi_Sensor`. If the sensor does not fall into one of these categories, inherit from the class `Sensor`.

The initialization function in the new class should look like this.

    def __init__(self, name, **kwargs):
        with GlobalImport() as gi:
            # import libraries required for sensor here
            gi()
        super().__init__(name, **kwargs)
        self.channels = [] # sensor channel names
        self.units = [] # units for each sensor channel; must be the same length a self.channels
        # define any other sensor properties
        
You must define a `read` method which sets `self.values` to a list of measurement values for each channel. Optionally, you can define a filter function which returns a mask in the form of a list. Here is an example sensor class definition.

    class Example_Sensor(Sensor):
        """Class for testing and debugging sensor code. Inherits from Sensor class."""
        def __init__(self, name, **kwargs):
            with GlobalImport() as gi:
                import random
                gi()
            super().__init__(name, **kwargs)
            self.channels = ["measurement1", "measurement2"]
            self.units = ["units", "units"]

        def read(self):
            self.values = [random.random(), random.random()]
            
        def filter(self)
            return [x > 0 for x in self.values]

Raspberry Pi-based sensors include an additional argument `pin` for the GPIO pin on the Raspberry-Pi. Arduino-based sensors include an additional argument `board_port` and an additional keyword argument `baud` for the Arduino board port and baud rate respectively. The read function is predefined for Arduino-based sensors. The function assumes that the measurements are communicated over serial and seperated by commas.

## Currently supported sensors

### Respberry-Pi sensors

#### DHT22

The DHT22 is a temperature-humidity sensor from Adafruit. It uses the `adafruit_dht`, `board`, and `psutil` python libraries. You may also need to install `libgpiod2`.

        pip install adafruit-circuitpython-dht
        pip install board
        pip install psutil
        sudo apt install libgpiod2

There is a glitch where the `adafruit_dht` library leaves background processes running that interfere with connecting to the DHT22 multiple times. This glitch is resolved using the `kill_processes` method of the DHT22 sensor class. The sensor class automatically calculates an approximation for the dew point from the temperature and humidity.
