###################################
# Doorbell with face recognition  #
###################################
#
# Author: Martijn van der Sar
# https://www.github.com/Erientes/

# Import modules
from picamera import PiCamera
import time

# Good practice, more information: https://stackoverflow.com/questions/419163/what-does-if-name-main-do
if __name__ == '__main__':
    # Instantiate PiCamera object
    camera = PiCamera()

    # Sleep for 5 seconds before taking the photo
    time.sleep(5)

    # Take photo and save it as 'test.jpg'
    camera.capture('./test.jpg')