###################################
# Doorbell with face recognition  #
###################################
#
# Author: Martijn van der Sar
# https://www.github.com/Erientes/


#########################
# MODULES               #
#########################
from src._button import Button
from src._led import LED
import json
import RPi.GPIO as GPIO
import time

#########################
# GLOBALS               #
#########################
LAST_MODE     = [0] * 7
DEBOUNCE_TIME = 500         # In seconds
MODE          = [0] * 7     # Initial MODE is zero: All LEDs and Buttons are off.

try:
    with open('../config.json', 'r') as f:
        PIN_MAPPING = json.load(f)
except:
    print('config.json not found. Loading PIN_MAPPING from {}'.format(__file__))
    PIN_MAPPING = {"RED_BUTTON": 14, "YELLOW_BUTTON": 15, "GREEN_BUTTON": 18,
                   "RED_LED": 23, "YELLOW_LED": 24, "GREEN_LED": 25}


#########################
# FUNCTIONS             #
#########################
def red_cb(obj):
    """ Red button callback function """
    print('Red button pressed.')

    # set Button mode
    MODE[0] = 1

    # set LED mode
    set_MODE_value(3)

    # Push new LED modes to the driver
    set_LED_states()

    print(MODE)


def yellow_cb(obj):
    """ Yellow button callback function """
    print('Yellow button pressed')

    # set Button mode
    MODE[1] = 1

    # set LED mode
    set_MODE_value(4)

    # Push new LED modes to the driver
    set_LED_states()

    print(MODE)


def green_cb(obj):
    """ Green button callback function """
    print('Green button pressed')

    # set Button mode
    MODE[2] = 1

    # set LED mode
    set_MODE_value(5)

    # Push new LED modes to the driver
    set_LED_states()

    print(MODE)


def set_MODE_value(idx, value=None):
    """ Set values of global variable MODE"""

    # Assert that the idx is within MODE list
    assert(len(MODE) >= idx), 'Entered index is too large. {}{}'.format(len(MODE), idx)

    # If no value is given, the binary value is swapped
    if value is None:
        MODE[idx] = 0 if MODE[idx] == 1 else 1
    else:
        MODE[idx] = value


def set_LED_states():
    """ Set the states of the LEDs, but only if the MODE has changed."""
    global LAST_MODE

    # Conditions to check if the mode has changed for that particular LED
    # If it has changed, set the new state.
    if MODE[3] != LAST_MODE[3]:
        red_led.set_state(MODE[3])
    elif MODE[4] != LAST_MODE[4]:
        yellow_led.set_state(MODE[4])
    elif MODE[5] != LAST_MODE[5]:
        green_led.set_state(MODE[5])

    # Save the new mode for next callback
    LAST_MODE = [val for val in MODE]


#########################
# MAIN                  #
#########################
if __name__ == '__main__':

    # LED SETUP
    # Instantiate LED object for red, yellow and green button
    # TODO: make this cleaner; maybe move to dictionary?
    red_led = LED(channel=PIN_MAPPING['RED_LED'])
    yellow_led = LED(channel=PIN_MAPPING['YELLOW_LED'])
    green_led = LED(channel=PIN_MAPPING['GREEN_LED'])

    # Start LED drivers
    red_led.start()
    yellow_led.start()
    green_led.start()

    # Push initial values (as defined in MODE) to the LEDs
    set_LED_states()

    # BUTTON SETUP
    # Instantiate Button object for red, yellow and green button
    red_button = Button(PIN_MAPPING['RED_BUTTON'], polarity=GPIO.FALLING, pull_up_down=GPIO.PUD_UP,
                        debounce_time=DEBOUNCE_TIME)
    yellow_button = Button(PIN_MAPPING['YELLOW_BUTTON'], polarity=GPIO.FALLING, pull_up_down=GPIO.PUD_UP,
                           debounce_time=DEBOUNCE_TIME)
    green_button = Button(PIN_MAPPING['GREEN_BUTTON'], polarity=GPIO.FALLING, pull_up_down=GPIO.PUD_UP,
                          debounce_time=DEBOUNCE_TIME)

    # Add event detection and assign callback function
    red_button.on_press(red_cb)
    yellow_button.on_press(yellow_cb)
    green_button.on_press(green_cb)

    # Infinite loop
    i = 0
    while i < 100:
        i = i + 1
        if i % 10 == 0:
            print(i)
        time.sleep(0.05)
