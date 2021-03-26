import ctypes
import numpy as np
from picosdk.ps2000a import ps2000a as ps
import matplotlib.pyplot as plt
from picosdk.functions import adc2mV, assert_pico_ok
import time


class Channel():

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
        return ps.ps2000aSetChannel(self.chandle, self.channel, self.enabled, self.coupling, self.range, self.offset)

    def create_buffer(self, size, num, ratio_mode):
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

    def __init__(self, channels):
        self.channels = channels
        self.next = 0
        self.auto_stop = False
        self.called_back = False

    def callback(self, handle, num_samples, start_idx, overflow, trigger_at, triggered, auto_stop, param):
        self.called_back = True
        dest_end = self.next + num_samples
        source_end = start_idx + num_samples
        for channel in self.channels.values():
            channel.buffer_complete[self.next:dest_end] = channel.buffer[start_idx:source_end]
        self.next += num_samples
        if auto_stop:
            self.auto_stop = True


class Picoscope():

    def __init__(self):
        # create chandle and status ready for use
        self.chandle = ctypes.c_int16()
        self.status = {}
        # open picoscope device
        self.status["openunit"] = ps.ps2000aOpenUnit(ctypes.byref(self.chandle), None)
        assert_pico_ok(self.status["openunit"])
        self.channels = {}
        self.buffer_settings = {}
        self.streamer = None
        self.sample_interval = 0

    def setup_channel(self, alias, **kwargs):
        channel = Channel(self.chandle, alias, **kwargs)
        self.channels[alias] = channel
        channel_setup_name = "setCh" + channel.letter
        self.status[channel_setup_name] = channel.setup()
        assert_pico_ok(self.status[channel_setup_name])

    def setup_buffer(self, size=500, num=10, ratio_mode="PS2000A_RATIO_MODE_NONE"):
        self.buffer_settings = dict(size=size, num=num, ratio_mode=ratio_mode)
        for channel in self.channels.values():
            channel_buffer_name = "setDataBuffers" + channel.letter
            self.status[channel_buffer_name] = channel.create_buffer(**self.buffer_settings)
            assert_pico_ok(self.status[channel_buffer_name])

    def setup_stream(self, sample_interval=250, sample_units="PS2000A_US", downsample_ratio=1):
        self.sample_interval = sample_interval
        self.status["runStreaming"] = ps.ps2000aRunStreaming(self.chandle,
                                                             ctypes.c_int32(sample_interval),
                                                             ps.PS2000A_TIME_UNITS[sample_units],
                                                             0,
                                                             self.buffer_settings["size"] * self.buffer_settings["num"],
                                                             1,
                                                             downsample_ratio,
                                                             ps.PS2000A_RATIO_MODE[self.buffer_settings["ratio_mode"]],
                                                             self.buffer_settings["size"])
        assert_pico_ok(self.status["runStreaming"])

    def stream(self):
        streamer = Streamer(self.channels)
        cfunc_pointer = ps.StreamingReadyType(streamer.callback)
        while streamer.next < self.buffer_settings["size"] * self.buffer_settings["num"] and not streamer.auto_stop:
            streamer.called_back = False
            self.status["getStreamingLastestValues"] = ps.ps2000aGetStreamingLatestValues(self.chandle, cfunc_pointer, None)
            if not streamer.called_back:
                time.sleep(0.01)

    def get_data(self):
        max_ADC = ctypes.c_int16()
        self.status["maximumValue"] = ps.ps2000aMaximumValue(self.chandle, ctypes.byref(maxADC))
        assert_pico_ok(self.status["maximumValue"])
        data = {}
        total_samples = self.buffer_settings["size"] * self.buffer_settings["num"]
        data["time"] = np.linspace(0, total_samples * ctypes.c_int32(self.sample_interval).value * 1000, total_samples)
        for alias, channel in self.channels.items():
            data[alias] = adc2mV(channel.buffer_complete, channel.range, max_ADC)
        return data

    def stop(self):
        self.status["stop"] = ps.ps2000aStop(self.chandle)
        assert_pico_ok(self.status["stop"])
        self.status["close"] = ps.ps2000aCloseUnit(self.chandle)
        assert_pico_ok(self.status["close"])

    def print_status(self):
        print(self.status)


if __name__ == "main":
    pico = Picoscope()
    pico.setup_channel("ch1", letter="A")
    pico.setup_channel("ch2", letter="B")
    pico.setup_buffer()
    pico.setup_stream()
    pico.stream()
    data = pico.get_data()
    pico.stop()
    pico.print_status()
    print(data)
