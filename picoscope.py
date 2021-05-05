import ctypes
import numpy as np
from picosdk.ps2000a import ps2000a as ps
from picosdk.functions import adc2mV, assert_pico_ok
import time
import datetime


class Channel():
    """
    Picoscope channel object.

    For coupling and range options, see https://www.picotech.com/download/manuals/picoscope-2000-series-programmers-guide.pdf

    Args:
        chandle: C handle from Picoscope object
        alias (string): Channel alias
        letter (string): Channel letter. Either "A", "B", "C", or "D"
        enabled (bool): Enable channel.
        coupling (string): Channel coupling
        range (string): Channel range
        offset (float): Channel offset

    Attrs:
        chandle: C handle from Picoscope object
        alias (string): Channel alias
        letter (string): Channel letter. Either "A", "B", "C", or "D"
        enabled (bool): Enable channel.
        coupling (string): Channel coupling
        range (string): Channel range
        offset (float): Channel offset
        buffer (list): Channel buffer
        buffer_complete (list): Complete channel buffer
    """
    def __init__(self, chandle, alias, letter="A", enabled=True, coupling="PS2000A_DC", range="PS2000A_2V", offset=0):
        self.chandle = chandle
        self.alias = alias
        self.letter = letter
        self.channel = ps.PS2000A_CHANNEL["PS2000A_CHANNEL_" + letter]
        self.enabled = int(enabled)
        self.coupling = ps.PS2000A_COUPLING[coupling]
        self.range = ps.PS2000A_RANGE[range]
        self.offset = offset
        self.buffer = None
        self.buffer_complete = None

    def setup(self):
        """
        Setup channel.

        Returns:
            Channel setup status
        """
        return ps.ps2000aSetChannel(self.chandle, self.channel, self.enabled, self.coupling, self.range, self.offset)

    def create_buffer(self, size, num, ratio_mode):
        """
        Create channel buffer.

        Args:
            size (int): Size of a single buffer
            num (int): Number of buffers to capture
            ratio_mode (string): Buffer ratio mode

        Returns:
            Buffer setup status
        """
        self.buffer = np.zeros(shape=size, dtype=np.int16)
        self.buffer_complete = np.zeros(shape=size * num, dtype=np.int16)
        return ps.ps2000aSetDataBuffers(self.chandle,
                                        self.channel,
                                        self.buffer.ctypes.data_as(ctypes.POINTER(ctypes.c_int16)),
                                        None,
                                        size,
                                        0,
                                        ps.PS2000A_RATIO_MODE[ratio_mode])


class Streamer():
    """
    Picoscope streamer object.

    Args:
        channels (dict): Dictionary of channel aliases and channel objects

    Attrs:
        channels (dict): Dictionary of channel aliases and channel objects
        next (int): Number of next sample
        auto_stop (bool): Auto stop streaming
        called_back (bool): Picoscope streamer was already called back
    """
    def __init__(self, channels):
        self.channels = channels
        self.next = 0
        self.auto_stop = False
        self.called_back = False

    def callback(self, handle, num_samples, start_idx, overflow, trigger_at, triggered, auto_stop, param):
        """Streamer callback function."""
        self.called_back = True
        dest_end = self.next + num_samples
        source_end = start_idx + num_samples
        for channel in self.channels.values():
            channel.buffer_complete[self.next:dest_end] = channel.buffer[start_idx:source_end]
        self.next += num_samples
        if auto_stop:
            self.auto_stop = True


class Picoscope():
    """
    Picoscope object.

    Args:
        name (str): A name to associate with the picoscope

    Attrs:
        name: A name to associate with the picoscope
        chandle: C handle
        status (dict): Dictionary of picoscope status objects
        channels (dict): Dictionary of channel aliases and channel objects
        buffer_settings (dict): Dictionary of buffer settings
        sample_interval (float): Sample interval
    """
    def __init__(self, name):
        self.chandle = ctypes.c_int16()
        self.status = {}
        self.status["openunit"] = ps.ps2000aOpenUnit(ctypes.byref(self.chandle), None)
        assert_pico_ok(self.status["openunit"])
        self.channels = {}
        self.buffer_settings = {}
        self.sample_interval = 0
        self.stream_start = datetime.datetime.utcnow()
        self.raw_data = {}
        self.data = []
        self.name = name

    def setup_channel(self, alias, **kwargs):
        """
        Setup channel

        Args:
            alias (string): Channel alias
            **kwargs: Channel object arguments
        """
        channel = Channel(self.chandle, alias, **kwargs)
        self.channels[alias] = channel
        channel_setup_name = "setCh" + channel.letter
        self.status[channel_setup_name] = channel.setup()
        assert_pico_ok(self.status[channel_setup_name])

    def setup_buffer(self, size=500, num=10, ratio_mode="PS2000A_RATIO_MODE_NONE"):
        """
        Setup buffer for all channels.

        For ratio mode options, see https://www.picotech.com/download/manuals/picoscope-2000-series-programmers-guide.pdf

        Args:
            size (int): Size of a single buffer
            num (int): Number of buffers to capture
            ratio_mode (string): Buffer ratio mode
        """
        self.buffer_settings = dict(size=size, num=num, ratio_mode=ratio_mode)
        for channel in self.channels.values():
            channel_buffer_name = "setDataBuffers" + channel.letter
            self.status[channel_buffer_name] = channel.create_buffer(**self.buffer_settings)
            assert_pico_ok(self.status[channel_buffer_name])

    def setup_stream(self, sample_interval=250, sample_units="PS2000A_US", downsample_ratio=1):
        """
        Setup streaming.

        For sample_units options, see https://www.picotech.com/download/manuals/picoscope-2000-series-programmers-guide.pdf

        Args:
            sample_interval (int): Sample interval
            sample_units (string): Sample units
            downsample_ratio (int): Downsample ratio
        """
        self.sample_interval = ctypes.c_int32(sample_interval)
        self.status["runStreaming"] = ps.ps2000aRunStreaming(self.chandle,
                                                             ctypes.byref(self.sample_interval),
                                                             ps.PS2000A_TIME_UNITS[sample_units],
                                                             0,
                                                             self.buffer_settings["size"] * self.buffer_settings["num"],
                                                             1,
                                                             downsample_ratio,
                                                             ps.PS2000A_RATIO_MODE[self.buffer_settings["ratio_mode"]],
                                                             self.buffer_settings["size"])
        assert_pico_ok(self.status["runStreaming"])

    def stream(self):
        """Stream data."""
        streamer = Streamer(self.channels)
        cfunc_pointer = ps.StreamingReadyType(streamer.callback)
        self.stream_start = datetime.datetime.utcnow()
        while streamer.next < self.buffer_settings["size"] * self.buffer_settings["num"] and not streamer.auto_stop:
            streamer.called_back = False
            self.status["getStreamingLastestValues"] = ps.ps2000aGetStreamingLatestValues(self.chandle, cfunc_pointer, None)
            if not streamer.called_back:
                time.sleep(0.01)

    def process_data(self):
        """Process data"""
        total_samples = self.buffer_settings["size"] * self.buffer_settings["num"]
        for i in range(total_samples):
            measurement_time = str(self.stream_start + datetime.timedelta(microseconds=self.raw_data["time"][i]))
            data_body = dict(measurement=self.name, time=measurement_time, fields={})
            for channel_name in self.channels.keys():
                data_body["fields"][channel_name] = self.raw_data[channel_name][i]
            self.data.append(data_body)

    def generate_body(self):
        """Retrieve data."""
        max_ADC = ctypes.c_int16()
        self.status["maximumValue"] = ps.ps2000aMaximumValue(self.chandle, ctypes.byref(max_ADC))
        assert_pico_ok(self.status["maximumValue"])
        total_samples = self.buffer_settings["size"] * self.buffer_settings["num"]
        self.raw_data["time"] = np.linspace(0, total_samples * self.sample_interval.value, total_samples)
        for alias, channel in self.channels.items():
            self.raw_data[alias] = adc2mV(channel.buffer_complete, channel.range, max_ADC)
        self.process_data()

    def stop(self):
        """Stop picoscope."""
        self.status["stop"] = ps.ps2000aStop(self.chandle)
        assert_pico_ok(self.status["stop"])
        self.status["close"] = ps.ps2000aCloseUnit(self.chandle)
        assert_pico_ok(self.status["close"])

    def print_status(self):
        """Print picoscope status."""
        print(self.status)
