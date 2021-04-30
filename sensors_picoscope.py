from sensor_classes import *
from picoscope import Picoscope

logger = Logger("picoscope")
logger.connect(**parse_config("config.config"))

pico = Picoscope("picoscope")
try:
    pico.setup_channel("ch1", letter="A")
    while True:
        pico.setup_buffer(size=1, num=1)
        pico.setup_stream(sample_interval=1000)
        pico.stream()
        pico.generate_body()
        pico.print_status()
        logger.upload_custom(pico.data)
finally:
    pico.stop()
