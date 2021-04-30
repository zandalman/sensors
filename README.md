# Sensors

An object-oriented unified sensor code for uploading sensor data from a Raspberry Pi to InfluxDB. The code supports sensors connected directly to the Raspberry Pi or connected via Arduino and USB port. New sensor types can be added easily.

## Create a config file

For security reasons, you should use a config file to store sensitive information about your database. The built-in function `parse_config` reads config files structured like this and returns a dictionary. The file `config-template.config` provides a template that you can use.

    [influxdb]
    url = DATABASE_SERVER_URL
    port = DATABASE_PORT_NUMBER
    username = DATABASE_USERNAME
    password = DATABASE_PASSWORD
    database = DATABASE_NAME
    
## Set up logger object

You need to initialize a `Logger` object to connect to the database client. Once you initialize the `Logger` object, you can add `Sensor` objects.

1. Initialize a `Logger` object. The object requires a name as an argument. All sensors associated with the Logger object will appear as seperate fields under this name in InfluxDB.
2. Call `Logger.connect` to connect to the client. The method requires all of the information in the config file as arguments. Optionally, you can specify a custom directory for writing files if the connection to the client fails using the `backup_dir` keyword argument. By default, the logger will write backup files to a folder in the current directory named `backups`.
3. Initialize the `Sensor` objects. All Arduino-based sensors require the board port as a keyword argument. All Raspberry Pi-based sensors require the GPIO pin as a keyword argument. If you want to print the measurements from a `Sensor` object, pass `print_m=True` as a keyword argument.
4. Call `Logger.add_sensors` and pass the sensors as arguments to add the sensors to the `Logger` object.

You can find an example of this in `sensors.py`.

    logger = Logger(LOGGER_NAME) # step 1
    logger.connect(**parse_config(), backup_dir=PATH_TO_BACKUP_DIRECTORY) # step 2
    sensor = Test_Sensor(SENSOR_NAME, print_m=True) # step 3
    logger.add_sensors(sensor) # step 4

## Data collection

You will need to create a loop to collect and upload the data. In each iteration of the loop, you will need to use two methods of the `Logger` object.

1. `Logger.generate_body` reads from all sensors and creates a datapoint.
2. `Logger.upload` uploads all unuploaded data points to the database.

You can find an example of this in `sensors.py`.

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
        
You must define a `read` method which sets `self.values` to a list of measurement values for each channel. Optionally, you can define a filter function which returns a mask in the form of a list of Booleans. Here is an example sensor class definition.

    class Example_Sensor(Sensor):
        """Class for testing and debugging sensor code. Inherits from Sensor class."""
        def __init__(self, name, **kwargs):
            with GlobalImport() as gi:
                import random
                gi()
            super().__init__(name, **kwargs)
            self.channels = ["distance", "time"]
            self.units = ["m", "s"]

        def read(self):
            distance = random.random()
            time = random.random()
            speed = distance / time
            self.values = [distance, time, speed]
            
        def filter(self)
            distance, time, speed = self.values
            return [distance > 0, time > 0, speed > 0]

Raspberry Pi-based sensors include an additional argument `pin` for the GPIO pin on the Raspberry Pi. Arduino-based sensors include an additional argument `board_port` and an additional keyword argument `baud` for the Arduino board port and baud rate respectively. The read function is predefined for Arduino-based sensors. The function assumes that the measurements are communicated over serial and seperated by commas.

## Setting up cron on Raspberry Pi

Cron is a tool for configuring scheduled tasks in Unix systems. Using cron, you can set the sensor code to run every time the Raspberry Pi reboots.

1. Run `crontab -e` in the command line on the Raspberry Pi. If you are prompted to choose an editor, choose the editor of your choice (e.g. nano).
2. In the cron file, add the line `@reboot python PATH_TO_SENSORS_FOLDER/sensors.py &`.

## Currently supported sensors

Sensors are listed by their part number with their object name in `sensor_classes.py` in parenthesis.

### Arduino sensors (Arduino_Sensor)

All Arduino sensors have a built-in read function which uses the "serial" library. The built-in read function requires the input values to be sent over serial as a byte string separated by commas with each timestep on a new line. For example

    int NUM_MEASUREMENTS = 2;
    int DELAY = 250;
    
    void loop(void) {
      measurement1 = ;// Insert code
      measurement2 = ;// Insert code
      double values[] = {measurement1, measurement2};
      printall(values);
      Serial.println("");
      delay(DELAY);
    }
    
    void printall(double values[]) {
      for (int i = 0; i <= NUM_MEASUREMENTS; i++) {
        Serial.print(values[i]);
        Serial.print(",");
      }
    }
    
For all Arduino sensors, you must specify the board port and baud rate on initialization using the keyword arguments `board_port` and `baud`. To find the board port on the Raspberry Pi

1. Run `ls /dev/tty*`
2. Find the result that is not one of the following:
    1. `/dev/ttyN` where `N` is an integer from 0 to 63
    2. `/dev/ttyAMA0`
    3. `/dev/ttyprintk`

#### LSM303DLHC (Magnetometer)

The LSM303DLHC is a magnetometer sensor from Adafruit. It determines the ambient magnetic field along all 3 axes in uG.

#### L3GD20H (Gyroscope)

The L3GD20H is a gyroscope sensor from Adafruit. It determines the angular velocity along all 3 axes in rad/s.

#### ADXL345 (Accelerometer)

The ADXL345 is an accelerometer sensor from Adafruit. It determines the linear acceleration along all 3 axes in m/s^2.

### Raspberry Pi sensors (Pi_Sensor)

For all Raspberry Pi sensors, you must specify the GPIO pin number on initialization using the keyword argument `pin`. Remember to use the GPIO pin number rather than the actual pin number (i.e. pin 8 is GPIO pin 14).

#### DHT22 (Temp_Humid_Sensor)

The DHT22 is a temperature-humidity sensor from Adafruit. It uses the `adafruit_dht`, `board`, and `psutil` python libraries. You may also need to install `libgpiod2`.

    pip install adafruit-circuitpython-dht
    pip install board
    pip install psutil
    sudo apt install libgpiod2

There is a glitch caused by the `adafruit_dht` library which leaves background processes running that interfere with connecting to the DHT22 multiple times. To resolve this glitch, you must initialize the first DHT22 sensor only with the keyword argument `first=True`. This will cause the `kill_processes` method to run. The sensor class includes a method `calc_dew_pt` which automatically calculates an approximation for the dew point from the temperature and humidity.

### Other sensors

#### Picoscope 2000 Series

Picoscope is a high-precision oscilloscope. To read data from the picoscope, you will need to install the correct version of the Picoscope driver for your Picoscope from the [Picoscope downloads page](https://www.picotech.com/downloads). Our code uses an existing GitHub repository [Picoscope Python drivers](https://github.com/picotech/picosdk-python-wrappers). The Picoscope works differently from the other sensors so the Picoscope object is contained in a seperate file `Picoscope.py`. To integrate a Picoscope object into the sensor code

1. Initialize a Picoscope object.
2. Create a try-finally clause. In the finally block, stop the Picoscope. If you skip this step, you will not be able to start and stop reading data freely. Do the remainder of the steps in the try block.
3. Set up the Picoscope channels.
4. Create a loop to collect data. In each iteration of the loop
    1. Set up the Picoscope buffer.
    2. Set up the Picoscope streamer.
    3. Start the stream.
    4. Generate the data body to send to InfluxDB.
    5. Upload the data body.

You can find an example of this in `sensors_picoscope.py`. More information about the options available for the Picoscope can be found [here](https://www.picotech.com/download/manuals/picoscope-2000-series-programmers-guide.pdf).

```
    pico = Picoscope("picoscope") # step 1
    try:
        pico.setup_channel("red laser power", letter="A") # step 3
        pico.setup_channel("blue laser power", letter="B")
    while True:
        pico.setup_buffer(size=1, num=1) # step 4.1
        pico.setup_stream(sample_interval=250, downsample_ratio=1) # step 4.2
        pico.stream() # step 4.3
        pico.generate_body() # step 4.4
        pico.print_status() # optional, but useful for debugging
        logger.upload_custom(pico.data) # step 4.5
    finally:
        pico.stop() # step 2
 ```

#### Thermocouple

In progress

## Planned Features

1. Automatic error logging using the python `logger` library.
