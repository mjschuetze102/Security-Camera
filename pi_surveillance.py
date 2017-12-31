from pyimagesearch.tempimage import TempImage
from picamera.array import PiRGBArray
from picamera import PiCamera
import argparse
import warnings
import datetime
import dropbox
import imutils
import json
import time
import cv2

# Construct the argument parser and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-c", "--conf", required=True, \
        help="path to the JSON configuration file")
args = vars(ap.parse_args())

# Filter warnings, load the configuration and initialize the Dropbox client
warnings.filterwarnings("ignore")
conf = json.load(open(args["conf"]))
client = None

# Check to see if Dropbox is being used
if conf["use_dropbox"]:
    # Connect to Dropbox and start the session authorization process
    client = dropbox.Dropbox(conf["dropbox_access_token"])
    print("[SUCCESS] dropbox account linked")

# Initialize the camera and get a reference to the raw camera capture
camera = PiCamera()
camera.resolution = tuple(conf["resolution"])
camera.framerate = conf["fps"]
rawCapture = PiRGBArray(camera, size=tuple(conf["resolution"]))

# Allow the camera to warmup
print("[INFO] warming up...")
time.sleep(conf["camera_warmup_time"])

# Initialize average frame, last uploaded timestamp, and frame motion counter
avg = None
lastUploaded = datetime.datetime.now()
motionCounter = 0

# Capture the frames from the camera
for f in camera.capture_continuous(rawCapture, format="bgr", \
        use_video_port=True):
    # Get the raw NumPy array representing the image
    frame = f.array

    # Initialize the timestamp and occupied/unoccupied text
    timestamp = datetime.datetime.now()
    text = "Unoccupied"

    # Resize the frame, convert it to grayscale, and blur it
    frame = imutils.resize(frame, width=500)
    grey = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    grey = cv2.GaussianBlur(grey, (21, 21), 0)

    # If the average frame is None, initialize it
    if avg is None:
        print("[INFO] starting background model...")
        avg = grey.copy().astype("float")
        rawCapture.truncate(0)
        continue

    # Accumulate the weighted average between the current frame
    # and previous frames, then compute the difference between
    # the current frame and running average
    cv2.accumulateWeighted(grey, avg, 0.5)
    frameDelta = cv2.absdiff(grey, cv2.convertScaleAbs(avg))

    # Threshold the delta image
    thresh = cv2.threshold(frameDelta, conf["delta_thresh"], 255, \
            cv2.THRESH_BINARY)[1]
    
    # Dilate the thresholded image to fill holes, then find contours on image
    thresh = cv2.dilate(thresh, None, iterations=2)
    cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, \
            cv2.CHAIN_APPROX_SIMPLE)
    cnts = cnts[0] if imutils.is_cv2() else cnts[1]

    # Loop over the contours
    for c in cnts:
        # If contour is too small, ignore it
        if cv2.contourArea(c) < conf["min_area"]:
            continue

        # Compute the bounding box for the contour
        (x, y, w, h) = cv2.boundingRect(c)

        # Draw the bound box on the frame and update the text
        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
        text = "Occupied"

    # Draw the text and timestamp on the frame
    ts = timestamp.strftime("%A %d %B %Y %I:%M:%S%p")
    cv2.putText(frame, "Room Status: {}".format(text), (10, 20), \
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
    cv2.putText(frame, ts, (10, frame.shape[0] - 10), \
            cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)

    # Check to see if the room is occupied
    if text == "Occupied":
        # Check to see if enough time has passed between uploads
        if (timestamp - lastUploaded).seconds >= conf["seconds_between_upload"]:
            # Increment the motion counter
            motionCounter += 1

            # Check to see if Dropbox should be used
            if conf["use_dropbox"]:
                # Write the image to temporary file
                t = TempImage()
                cv2.imwrite(t.path, frame)

                # Upload the image to Dropbox and cleanup the temp image
                print("[Upload] {}".format(ts))
                path = "/{base_path}/{timestamp}.jpg".format( \
                        base_path=conf["dropbox_base_path"], \
                        timestamp=ts)
                client.files_upload(open(t.path, "rb").read(), path)
                t.cleanup()

                # Update the last uploaded timestamp and reset motion counter
                lastUploaded = timestamp
                motionCounter = 0

    # Else, the room is not occupied
    else:
        motionCounter = 0

    # Check to see if frames should be displayed to screen
    if conf["show_video"]:
        # Display the security feed
        cv2.imshow("Security Feed", frame)
        key = cv2.waitKey(1) & 0xFF

        # If the 'q' key is pressed, break from the loop
        if key == ord("q"):
            break

    # Clear the stream in preparation for the next frame
    rawCapture.truncate(0)
