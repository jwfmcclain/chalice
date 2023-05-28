import board
import digitalio
import pwmio
import time

import statemachines

import gps
import astral
import flicker

# Functions for low level control of flame LED
#
RED_LED   = pwmio.PWMOut(board.D11, frequency=50000, duty_cycle=0)
GREEN_LED = pwmio.PWMOut(board.D12, frequency=50000, duty_cycle=0)
BLUE_LED  = pwmio.PWMOut(board.D13, frequency=50000, duty_cycle=0)

def set_led(r, g, b):
    RED_LED.duty_cycle = r
    GREEN_LED.duty_cycle = g
    BLUE_LED.duty_cycle = b

def blink(count, r, g, b):
    for _ in range(count):
        set_led(r, g, b)
        time.sleep(0.5)
        set_led(0, 0, 0)
        time.sleep(0.5)

MAX = 255 * 255

# Subclass of Flicker object that controls high power LED hooked up
# to propmaker board
#
class BigFlicker(flicker.Flicker):
    def __init__(self, event, policy, controller):
        super().__init__(event, policy)
        self.controller = controller

    def set_color(self, red, green, blue):
        set_led(red, green, blue)

    def suppress(self):
        if self.controller.lamp_on():
            return None

        return self.controller

class Debug:
    def __init__(self):
        self._count = 0

    def start(self, now):
        return self.run, statemachines.IMMEDATE_TRANSFER

    def run(self, now):
        print(f"DEBUG: {now}: ", end='')
        print(f"{flicker}, transitions: {flicker.transitions} : {flicker.state.__name__}")
        print(f" actor count: {self._count} {statemachines.count_string()}")
        return None, statemachines.OneShot(now, statemachines.SECONDS_PER_NS * 3600)

    def inc(self):
        self._count += 1

# State Machine for top level executive

class Control:
    def __init__(self, mode_switch, gps_machine, pulser):
        self._lamp_on = False
        self.pulser = pulser
        self.mode_switch = mode_switch
        self.gps_machine = gps_machine

    def start(self, now):
        if self.mode_switch.value:
            return self.on, statemachines.IMMEDATE_TRANSFER
        return self.wait_on_gps, self.pulser

    def lamp_on(self):
        return self._lamp_on

    def triggered(self):
        return self._lamp_on

    def on(self, now):
        self._lamp_on = True

        if not self.mode_switch.value:
            # No longer in maual overide, see if we have a fix, if we
            # do it will do the right dispatch.
            return self.wait_on_gps, statemachines.IMMEDATE_TRANSFER

        # still in (manual) on state, loop
        return None, self.pulser

    def wait_on_gps(self, now):
        if self.mode_switch.value:
            # Maual override, flip on
            return self.on, statemachines.IMMEDATE_TRANSFER

        if self.gps_machine.has_fix():
            # Mode switch is set to automatic and we have a fix, go to
            # automatic state.
            return self.enter_automatic, statemachines.IMMEDATE_TRANSFER

        # Mode switch is set to automatic, but we don't have a fix, so
        # assert off and loop
        self._lamp_on = False
        return None, self.pulser

    def auto_on(self, now):
        self._lamp_on = True
        return self.auto_poll, statemachines.IMMEDATE_TRANSFER

    def auto_off(self, now):
        self._lamp_on = False
        return self.auto_poll, statemachines.IMMEDATE_TRANSFER

    def auto_poll(self, now):
        if self.mode_switch.value:
            # Maual override, go to (manual) on state
            return self.on, self.pulser

        if now >= self.deadline:
            # Hit deadline, figurer out next action
            return self.enter_automatic, statemachines.IMMEDATE_TRANSFER

        # loop
        return None, self.pulser

    def enter_automatic(self, now):
        # Always use the RTC for the time, that way things work in the face of
        # extended GPS outages (on the assumption that we're not really
        # moving)
        #
        # The GPS state machine takes care of updating the RTC clock with fixes from
        # from the GPS as they come int.
        day_seconds = astral.DateSeconds.fromtimestamp(time.localtime())

        latitude         = self.gps_machine.latitude
        longitude        = self.gps_machine.longitude

        seconds_until_sunrise = astral.time_of_first_after(astral.sunrise_utc, day_seconds, latitude, longitude) - day_seconds
        seconds_until_sunset  = astral.time_of_first_after(astral.sunset_utc,  day_seconds, latitude, longitude) - day_seconds

        print("sunset:", seconds_until_sunset, "sunrise:", seconds_until_sunrise)

        if (seconds_until_sunrise != 0 and seconds_until_sunrise < seconds_until_sunset) or seconds_until_sunset == 0:
            # night
            self.deadline = now + seconds_until_sunrise * statemachines.SECONDS_PER_NS
            return self.auto_on, statemachines.IMMEDATE_TRANSFER
        else:
            # day
            self.deadline = now + seconds_until_sunset * statemachines.SECONDS_PER_NS
            return self.auto_off, statemachines.IMMEDATE_TRANSFER

    def __str__(self):
        return f"{self.__class__.__name__}:{self._lamp_on}:{self.mode_switch.value}"

#
# Hardware Setup
#

mode_switch = digitalio.DigitalInOut(board.D9)
mode_switch.switch_to_input(pull=digitalio.Pull.UP)

#
# Turn on Propmaker Board
#
enable = digitalio.DigitalInOut(board.D10)
enable.direction = digitalio.Direction.OUTPUT
enable.value = True

# POST
blink(1, MAX, 0,     0)
blink(1,   0, MAX,   0)
blink(1,   0,   0, MAX)
blink(1, MAX, MAX, MAX)

gps_machine = gps.GPS(debug=True, reset=1)
controller = Control(mode_switch, gps_machine, statemachines.Pulser(0.5))
flicker_policy = flicker.FlickerPolicy(index_bottom=64,
                                       index_min=int(MAX/4),
                                       index_max=MAX)
flicker = BigFlicker(statemachines.Pulser(0.01), flicker_policy, controller)

statemachines.register_machine(gps_machine, controller, flicker)


debugger = Debug()
statemachines.register_machine(debugger)

statemachines.run((debugger.inc,), dump_interval=3600)
