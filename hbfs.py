#!/usr/bin/env python3
"""
Soundbites

Program that assigns each button a soundbit

Author: Nic La
Last Edit: Mar 2023
"""


import time
import busio
from board import SCL, SDA
from adafruit_trellis import Trellis
from pygame import mixer
import random
from datetime import datetime
from gpiozero import Button, LED


# Configure now for log
now = datetime.now().strftime("%H:%M:%S")
log_file = '/home/pi/hbfs/logs.log'

# Start new log file
with open(log_file, 'w') as file_object: file_object.write(f'{now}: Start new log\n')

# Append to log file
def print_log(log_msg):
    global log_file
    now = datetime.now().strftime("%H:%M:%S")
    with open(log_file, 'a') as file_object: 
        file_object.write(f'{now}: {log_msg}\n')

# Create the I2C interface
i2c = busio.I2C(SCL, SDA)

# Create a Trellis object
trellis = Trellis(i2c)  # 0x70 when no I2C address is supplied

# Turn on every LED
print_log('Turning all LEDs on...')
trellis.led.fill(True)
time.sleep(2)

# Turn off every LED
print_log('Turning all LEDs off...')
trellis.led.fill(False)
time.sleep(2)

# Turn on every LED, one at a time
print_log('Turning on each LED, one at a time...')
for i in range(16):
    trellis.led[i] = True
    time.sleep(0.1)

# Turn off every LED, one at a time
print_log('Turning off each LED, one at a time...')
for i in range(15, -1, -1):
    trellis.led[i] = False
    time.sleep(0.1)

# 22050 = This is the frequency, or the number of samples per second that make up your sound
# -16 = This is the bit depth, the size of each sample. -16 means "16 bit, signed" or "-32,768 to 32,767"
# 2 = This should be 1 to denote mono, and 2 to denote stereo
# 512 = This is the buffer size, it should generally be quite small since a large (the default is 4096) buffer will delay your sounds and a small buffer will distort them. I picked 512 through trial and error.
mixer.init(22050, -16, 2, 512)

# The number of sounds the mixer can play simultaneously
mixer.set_num_channels(16)

# Load sounds
soundbites = []
for sound in range(16):
    sound_item = {
        'sound': mixer.Sound(f"/home/pi/hbfs/{sound}.wav"),
        'length': mixer.Sound(f"/home/pi/hbfs/{sound}.wav").get_length(),
        'cycles': 0,
        'led_status': False,
        'count': sound
    }
    soundbites.append(sound_item)
completed_bite = mixer.Sound("/home/pi/hbfs/completed.wav")  # load completed sound bite
random.shuffle(soundbites)

# Now start reading button activity
# - When a button is depressed (just_pressed),
#   the LED for that button will turn on.
# - When the button is relased (released),
#   the LED will turn off.
# - Any button that is still depressed (pressed_buttons),
#   the LED will remain on.
print_log('Starting button sensory loop...')
pressed_buttons = set()

# Initialize variables
sequence = list(range(16))
step = 0
in_sequence = False
completed_sequence = False
button_listen = False
button = Button(27)  # GPIO27
led = LED(17)  # GPIO17
solenoid = LED(4)  # GPIO4
solenoid_count = 0

while True:
    # Make sure to take a break during each trellis.read_buttons
    # cycle.
    time.sleep(0.1)

    just_pressed, released = trellis.read_buttons()
    for b in just_pressed:
        print_log(f"Button = {b}, Sound = {soundbites[b]['count']}.wav")
        trellis.led[b] = True
        soundbites[b]['sound'].play(loops=0)  # play channel b sound
        soundbites[b]['cycles'] = round(soundbites[b]['length'] / 0.1)  # set cycles according to length

        # Check press against sequence
        if soundbites[b]['count'] == sequence[step]:
            in_sequence = True
            step += 1
        else:
            in_sequence = False
            step = 0

        if step > 15:
            print_log("Completed sequence")
            completed_sequence = True
            button_listen = True
            step = 0
            in_sequence = False
        else:
            completed_sequence = False
            button_listen = False
            completed_bite.stop()  # stop completed sound bite
        
    pressed_buttons.update(just_pressed)
    # for b in released:
    #     print("released:", b)
    #     trellis.led[b] = False
    # pressed_buttons.difference_update(released)
    # for b in pressed_buttons:
    #     print("still pressed:", b)
    #     trellis.led[b] = True

    # Manage LEDs
    for c in range(16):
        # Update led_status according to cycles
        if soundbites[c]['cycles'] > 0:
            soundbites[c]['led_status'] = True
            soundbites[c]['cycles'] -= 1
        elif not(in_sequence):
            soundbites[c]['led_status'] = False
            soundbites[c]['cycles'] = 0
        else:
            soundbites[c]['cycles'] = 0

        # Set LED according to led_status
        trellis.led[c] = soundbites[c]['led_status']

    # Play completed sound bite
    if soundbites[15]['cycles'] == 0 and completed_sequence:
        completed_bite.play(loops=0)
        completed_sequence = False

    # Button action
    if button.is_pressed and button_listen:
        if solenoid_count < 100:
            solenoid.on()  # energize solenoid
            solenoid_count += 1
        else:
            solenoid.off()
        led.off()  # deluminate button
    elif button_listen:
        solenoid.off()
        led.on()  # illuminate button
        solenoid_count = 0
    else:
        solenoid.off()
        led.off()
        solenoid_count = 0
