# Sensors

A unified sensor code for uploading data from sensors to InfluxDB.

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

Will add information soon.
