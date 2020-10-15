# Sensors

A unified sensor code for uploading sensor data from a Raspberry Pi to InfluxDB.

## Create a config file

For security reasons, you should use a config file to store sensitive information about your database. The config file could look something like this.

    [influxdb]
    url = DATABASE_SERVER_URL
    port = DATABASE_PORT_NUMBER
    username = DATABASE_USERNAME
    password = DATABASE_PASSWORD
    database = DATABASE_NAME
    
## Set up logger object

You need to initialize a `Logger` object to connect to the database client. Once you initialize the `Logger` object, you can add `Sensor` objects.

1. Initialize a `Logger` object. The object requires a name as an argument. All sensors associated with the Logger object will appear as seperate fields under this name in InfluxDB.
2. Call `Logger.connect` to connect to the client. The method requires all of the information in the config file as arguments. Optionally, specify a custom directory for writing files if the connection to the client fails using the `backup_dir` keyword argument.
3. Initialize the `Sensor` objects. All Arduino-based sensors require the board port as an argument. All Raspberry Pi-based sensors require the GPIO pin as an argument. If you want to print the measurements from a `Sensor` object, pass `print_m=True` as a keyword argument.
4. Call `Logger.add_sensors` and pass the sensors as arguments to add the sensors to the `Logger` object.

## Data collection

You will probably create a loop to collect and upload the data. To do this, you will need to use two methods of the `Logger` object.

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
        self.channels = [] # fill list with sensor channels
        self.units = [] # fill list with units for each sensor channel
        
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

