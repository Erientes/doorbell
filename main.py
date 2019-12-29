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
import face_recognition
from picamera import PiCamera
import numpy as np
import csv
from PIL import Image
import telegram
from credentials_telegram import token_value
import glob

#########################
# GLOBALS               #
#########################
DEBOUNCE_TIME = 500         # In ms
MODE = [0] * 7              # Initial MODE is zero: All LEDs and Buttons are off.
LAST_MODE = [0] * 7         # The last MODE that has been pushed to the LEDs
COUNTER = 0                 # Counting how much images are obtained (mainly for debugging)
IMG_WIDTH = 640             # Image width
IMG_HEIGHT = 480            # Image height
T_SHOW_RESULT = 10          # Time that the sign is on after the doorbell is rung (in seconds)
CAMERA = PiCamera()         # Instantiate RPi camera object

# Load configuration dictionaries
with open('config.json', 'r') as f:
	PIN_MAPPING = json.load(f)['PIN_MAPPING'] 
	f.seek(0)
	MODE_MAPPING = json.load(f)['MODE_MAPPING']


#########################
# FUNCTIONS             #
#########################


# BUTTON AND LED FUNCTIONS
# -------------------------

def red_cb(obj):
    """ Red button callback function """
    # Debugging tool:
    print('\nRed button pressed')
    # print(MODE)

    # Blink red LED to on
    set_MODE_value(MODE_MAPPING['RED_LED'], value=1)
    set_LED_states()

    # ----------------------------------------------------------------------------------
    # Add code here that you wan to execute if the yellow button is pressed

    time.sleep(2.5)

    # ----------------------------------------------------------------------------------

    set_MODE_value(MODE_MAPPING['RED_LED'], value=0)
    set_LED_states()


def yellow_cb(obj):
    """ Yellow button callback function """
    # Debugging tool:
    print('\nYellow button pressed')
    #print(MODE)

    # Set yellow LED mode to on
    set_MODE_value(4, value=1)
    set_LED_states()


    # ----------------------------------------------------------------------------------
    # Add code here that you wan to execute if the yellow button is pressed

    time.sleep(1)

    # Statements checks if yellow button was pressed as a main menu or sub menu option
    if not any(MODE[:3]):
        # Add face to whitelist if yellow button is pressed from the main menu
        print('Add face to list.')
        add_face_to_list()

    # ----------------------------------------------------------------------------------

    # Set LED mode
    set_MODE_value(4, value=0)
    set_LED_states()


def green_cb(obj):
    """ Green button callback function """
    # Debugging tool:
    print('\nGreen button pressed')
    #print(MODE)

    # Blink red LED 3 times
    set_MODE_value(MODE_MAPPING['GREEN_LED'], value=1)
    set_LED_states()

    # ----------------------------------------------------------------------------------
    # Add code here that you wan to execute if the yellow button is pressed

    time.sleep(2.5)

    # ----------------------------------------------------------------------------------

    set_MODE_value(MODE_MAPPING['GREEN_LED'], value=0)
    set_LED_states()


def bell_cb(obj):
    """ Bell button callback function """
    print('Bell button pressed')

    # Turn on the LEDs
    set_MODE_value([3,4,5], value=0)
    set_LED_states()

    # Check if the face of the person ringing the door exists in database
    # and return result
    result = check_face_from_doorbell()

    # Set the light that represents the result
    # 0 - Encoding on blacklist
    # 1 - Encoding on whitelist
    # 2 - Encoding on whitelist and blacklist (not good)
    # 3 - Encoding not on any of the lists
    if result == 0:
        set_MODE_value(3, value=1)
        send_img_telegram('\U0001F53A')
    elif result == 1:
        set_MODE_value(5, value=1)
    elif result == 2:
        set_MODE_value(4, value=3)
        send_img_telegram('\U000025FE')
    elif result == 3:
        set_MODE_value(4, value=1)
        send_img_telegram('\U0001F538')
    set_LED_states()

    # Show result for T_SHOW_RESULT seconds before turning off the lights
    time.sleep(T_SHOW_RESULT)

    # Turn of the lights and start listening again.
    set_MODE_value([3,4,5], value=0)
    set_LED_states()
    print('')


def set_MODE_value(idxs, value=None):
    """ Set values of global variable MODE"""

    if isinstance(idxs, int):
        idxs = [idxs]

    for idx in idxs:
        # Assert that the idx is within MODE list
        assert (len(MODE) >= idx), 'Entered index is too large.'

        # If no value is given, the binary value is swapped
        if value is None:
            MODE[idx] = 1 if MODE[idx] == 0 else 0
        else:
            MODE[idx] = value


def set_LED_states():
    """ Set the states of the LEDs, but only if the MODE has changed."""
    global LAST_MODE

    # Conditions to check if the mode has changed for that particular LED
    # If it has changed, set the new state.
    if MODE[3] != LAST_MODE[3]:
        red_led.set_state(MODE[3])
    if MODE[4] != LAST_MODE[4]:
        yellow_led.set_state(MODE[4])
    if MODE[5] != LAST_MODE[5]:
        green_led.set_state(MODE[5])

    # Save the new mode for next callback
    LAST_MODE = [val for val in MODE]


# FACE RECOGNITION FUNCTIONS
# ---------------------------

def get_image_test(fn):
    return np.array(Image.open("img/whitelist/{}.jpg".format(fn)))


def get_face_locations(inp_img):
    return face_recognition.face_locations(inp_img)


def get_face_encoding(inp_img, loc):
    return face_recognition.face_encodings(inp_img, loc)


def match_face_encodings(inp_img, known_faces=None):
    if known_faces == None:
        print('badness at match_face_encodings')

    return face_recognition.compare_faces(known_faces, inp_img)


def save_to_list(enc, list_id):
    print('Save encoding to csv file: {}'.format(list_id))
    with open('{}.csv'.format(list_id), 'a') as f:
        writer = csv.writer(f)
        writer.writerow(enc)


def get_image(filename=None):
    # Debug tool ----
    global COUNTER
    COUNTER = COUNTER + 1
    # print(COUNTER)
    # End of Debug tool ----

    output = np.empty((IMG_HEIGHT, IMG_WIDTH, 3), dtype=np.uint8)
    CAMERA.capture(output, format="rgb")
    if filename is not None:
        print('Saving image: {}.jpg'.format(filename))
        im = Image.fromarray(output)
        im.save("{}.jpeg".format(filename))
    return output


def check_face_from_doorbell():

    # Get whitelist and blacklist from csv file
    whitelist = np.genfromtxt('whitelist.csv', delimiter=',').reshape((-1, 128))
    blacklist = np.genfromtxt('blacklist.csv', delimiter=',').reshape((-1, 128))

    # Take picture and calculate encoding
    enc_doorbell = get_doorbell_enc()

    # Compare encoding with encoding databases
    match_allowed = face_recognition.compare_faces(whitelist, enc_doorbell, tolerance=0.6)
    match_denied  = face_recognition.compare_faces(blacklist, enc_doorbell, tolerance=0.6)

    print('In whitelist: {}\nIn blacklist: {}'.format(any(match_allowed), any(match_denied)))

    # What to do next?
    if any(match_allowed) == True and any(match_denied) == True:
        print('Face encoding in both whitelist and blacklist.')
        output = 2
    elif any(match_allowed) == True:
        print('Face encoding in whitelist')
        output = 1
    elif any(match_denied) == True:
        print('Face encoding in blacklist')
        output = 0
    else:
        print('Face encoding not in whitelist / blacklist')
        output = 3

    return output


def add_face_wrapper():
    if True:
        list_id = 'whitelist'
    else:
        list_id = 'blacklist'
    add_face_to_list(list_id=list_id)


def get_doorbell_enc():
    loc = []

    while len(loc) < 1:
        img = get_image(filename='img/doorbell/{}'.format(int(time.time())))
        loc = get_face_locations(img)

    return get_face_encoding(img, loc)


def add_face_to_list(list_id='whitelist'):
    assert (list_id in ['whitelist', 'blacklist']), 'Provide list_id: whitelist/blacklist.'

    # img = get_image_test('face')
    img = get_image(filename='img/whitelist/{}'.format(int(time.time())))
    loc = get_face_locations(img)

    if len(loc) == 1:
        print('Face detected. Calculating encoding...')
        enc = get_face_encoding(img, loc)
        save_to_list(enc[0], list_id)

        # Set LED mode
        set_MODE_value(5, value=3)
        set_LED_states()
        time.sleep(2.5)
        set_MODE_value(5, value=0)
        set_LED_states()

        print('Done...')
    else:
        if len(loc) > 1:
            print('{} faces detected. Please try again with only 1 face...'.format(len(loc)))
        else:
            print('No face detected. Please try again...'.format(len(loc)))


# Telegram Bot
# ---------------------------

def send_img_telegram(msg):
    dir_doorbell = 'img/doorbell/'
    threshold = 60 * 0.5

    fns = sorted([int(val.split('/')[-1].split('.')[0]) for val in glob.glob(dir_doorbell + '*')])

    bot = telegram.Bot(token=token_value)
    chat_id = bot.get_updates()[-1].message.chat_id

    bot.send_message(chat_id=chat_id, text="Doorbell Alarm")
    for fn in fns:
        if fns[-1] - fn < threshold:
            fn_format = dir_doorbell + '{}.jpeg'.format(fn)
            caption_str = msg + ' - {}'.format(time.ctime(fn))
            bot.send_photo(chat_id=chat_id, photo=open(fn_format, 'rb'), caption=caption_str)


#########################
# MAIN                  #
#########################
if __name__ == '__main__':

    CAMERA.resolution = (IMG_WIDTH, IMG_HEIGHT)

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
    bell_button = Button(PIN_MAPPING['BELL_BUTTON'], polarity=GPIO.FALLING, pull_up_down=GPIO.PUD_UP,
                        debounce_time=3 * DEBOUNCE_TIME)

    # Add event detection and assign callback function
    red_button.on_press(red_cb)
    yellow_button.on_press(yellow_cb)
    green_button.on_press(green_cb)
    bell_button.on_press(bell_cb)

    # Infinite loop
    i = 0
    print('Ready...')
    while True:
        i = i + 1
        if i % 1000 == 0:
            print('heartbeat')
        time.sleep(0.05)
