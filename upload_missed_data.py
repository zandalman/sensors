#!/usr/bin/env python
# -*- coding:utf-8 -*-

## import libraries
from influxdb import InfluxDBClient
from configparser import ConfigParser

import json
import os
import time
import errno

parser = ConfigParser()
parser.read('sensors.config')

missedDirectory = parser.get('missed','location')

## read old data if it exists
data=[]

try:
	for file in os.listdir(missedDirectory):
		if file.endswith('-missed.json'):
			fullPath = os.path.join(missedDirectory, file)
			with open(fullPath, 'r') as loadfile:
				loaddata=json.load(loadfile)
			data += loaddata
			os.remove(fullPath)
except Exception as err:
	print(err)

## upload the data; on failure, save it
if data:

	try:
		influx_url = parser.get('influx', 'url')
		influx_port = parser.get('influx', 'port')
		influx_user = parser.get('influx', 'username')
		influx_pwd = parser.get('influx', 'password')
		influx_db = parser.get('influx', 'database')
		client = InfluxDBClient(influx_url, influx_port, influx_user, influx_pwd, influx_db)
		client.write_points(data)
	except Exception as err:
		print(err)
		missedDirectory = parser.get('missed','location')
		try:
			os.makedirs(missedDirectory)
		except OSError as err:
			if err.errno != errno.EEXIST:
				raise
		saveFilename = "%d-missed.json" % time.time()
		savePath = os.path.join(missedDirectory, saveFilename)
		print("Attempting to save reading to %s" % savePath)
		with open(savePath,'w') as outfile:
			 json.dump(data, outfile)
