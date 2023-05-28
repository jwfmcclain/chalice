import board
import busio
import time
import rtc

import adafruit_gps

import statemachines

def format_ts(ts):
    return f"{ts.tm_year}-{ts.tm_mon:02}-{ts.tm_mday:02}T{ts.tm_hour:02}:{ts.tm_min:02}:{ts.tm_sec:02}"

# The interface of the adafruit_gps.GPS class makes it difficult to
# tell when there is a new timefix. Subclass that overrides
# _update_timestamp_utc and uses that call as a signal that a) a new
# timestamp is available, and b) the RTC should be updated/
#
class TimeSettingGPS(adafruit_gps.GPS):
    def _update_timestamp_utc(self, time_utc, date=None):
        adafruit_gps.GPS._update_timestamp_utc(self, time_utc, date)
        if date is not None:
            old_time = time.localtime()
            rtc.RTC().datetime = self.datetime
            print(f"Updated RTC to {format_ts(self.datetime)}, was {format_ts(old_time)} ({statemachines.monotonic_ns_calls} {statemachines.count_string()})")

class GPS:
    def __init__(self, debug=False, reset=False, tx=board.TX, rx=board.RX):
        uart = busio.UART(tx, rx, baudrate=9600, timeout=3)
        self.gps_dev = TimeSettingGPS(uart, debug=debug)

        if reset:
            self.gps_dev.send_command(bytes('PMTK10{reset}', 'ascii'))

        # Register only for RMC messages. They are the only message
        # type with the date, which is key to whole concept, and
        # (empirically) if we register for more messages we sometimes
        # get into (meta?)stable states where adafruit_gps.GPS doesn't
        # get/process RMC messages.
        #
        self.gps_dev.send_command(bytes('PMTK314,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0', 'ascii'))
        self.gps_dev.send_command(bytes('PMTK220,1000', 'ascii'))

        self.last_read = -1 # in the time.monotonic_ns() timebase
        self.update_count = 0

    def update_fix(self, now):
        print("has_fix:", self.gps_dev.has_fix)


        # make a bunch of checks to see if we really have a complete fix
        #
        if not self.gps_dev.has_fix:
            return

        if not self.gps_dev.latitude:
            return

        if not self.gps_dev.longitude:
            return

        ts = self.gps_dev.datetime

        if not ts:
            return

        if ts.tm_year == 0 or ts.tm_mday == 0 or ts.tm_mon == 0:
            return

        # We think we have fix, update state based on last reading
        #
        self.latitude = self.gps_dev.latitude
        self.longitude = self.gps_dev.longitude

        # We don't set time here, instead we rely on TimeSettingGPS
        # (above) to set the RTC when it knows it got a valid
        # time/date from the GPS

        self.last_read = now

    def has_fix(self):
        print("last_read", self.last_read)
        return self.last_read >= 0

    def start(self, now):
        return self.poll, statemachines.OneShot(now, 0)

    def poll(self, now):
        last_last_read = self.last_read
        if self.gps_dev.update():
            print(f"calling update_fix @ {now}")
            self.update_fix(now)

        self.update_count += 1

        if self.last_read < 0 or last_last_read == self.last_read:
            # Didn't read anything, or if we did the fix isn't yet
            # complete. Emperically it seems if we want to actualy get
            # a reading from the GPS we have loop pretty tightly
            # calling update until we get something.
            return None, statemachines.OneShot(now, int(0.1 * statemachines.SECONDS_PER_NS))

        # Else assume we don't move and we're just worried about clock
        # drift, so just go to the GPS once an hour *primarly* to update the RTC.
        print(self.update_count, "calls to get new GPS reading")
        self.update_count = 0
        return None, statemachines.OneShot(now, 3600 * statemachines.SECONDS_PER_NS)

    def __str__(self):
        return f"{self.__class__.__name__}:{self.last_read}"
