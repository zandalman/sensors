#!/usr/bin/env python
# -*- coding:utf-8 -*-

from sensor_classes import *

if __name__ == "__main__":
	db = InfluxDB("config.config", missed_dir="/Users/zacharyandalman/Documents/Sr Lab/logs")
	if not db.missed_dir:
		raise ValueError("Missed data directory is not defined.")
	for file in os.listdir(db.missed_dir):
		if file.endswith('-missed.json'):
			path = os.path.join(db.missed_dir, file)
			with open(path, 'r') as loadfile:
				dump = json.load(loadfile)
			data += [dump]
			os.remove(path)
	db.write(data)
