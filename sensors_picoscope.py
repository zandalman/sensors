from sensor_classes import *
from picoscope import Picoscope

logger = Logger("picoscope")
logger.connect(**parse_config("config.config"))

pico = Picoscope()
try:
    pico.setup_channel("ch1", letter="A")
    while True:
        pico.setup_buffer()
        pico.setup_stream()
        pico.stream()
        pico.generate_body()
        pico.print_status()
        logger.upload_custom(pico.data)
finally:
    pico.stop()
