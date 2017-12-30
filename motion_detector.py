import argparse
import datetime
import imutils
import time
import cv2

# Construct the argument parser and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-v", "--video", help="path to the video file")
ap.add_argument("-a", "--min-area", type=int, default=500, help="minimum area size")
args = vars(ap.parse_args())

# If video argument is None, then we are reading from a webcam
# Else we are reading from a video file
if args.get("video", None) is None:
    camera = cv2.VideoCapture(0)
    time.sleep(0.25)
else:
    camera = cv2.VideoCapture(args["video"])

# Variable to store the first frame of video stream
# Will be used to distinguish background from foreground
firstFrame = None

# Loop over the frames of the video input
while True:
    # Get the current frame and initialize the occupied/unoccupied text
    (grabbed, frame) = camera.read()
    text = "Unoccupied"

    # If there is no frame to get, the end of video has been reached
    if not grabbed:
        break

    # Resize the frame, convert it to grayscale, and blur it
    frame = imutils.resize(frame, width=500)
    grey = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    grey = cv2.GaussianBlur(grey, (21,21), 0)

    # If the first frame has yet to be initialized
    if firstFrame is None:
        firstFrame = grey
        continue

    # Compute the absolute difference between current frame and first frame
    frameDelta = cv2.absdiff(firstFrame, grey)
    thresh = cv2.threshold(frameDelta, 25, 255, cv2.THRESH_BINARY)[1]

    # Dilate the thresholded image to fill holes, then find contours on image
    thresh = cv2.dilate(thresh, None, iterations=2)
    (cnts, _) = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, \
            cv2.CHAIN_APPROX_SIMPLE)

    # Loop over the contours
    for c in cntrs:
        # If contour is too small, ignore it
        if cv2.contourArea(c) < args["min_area"]:
            continue

    # Compute the bounding box for the contour
    (x, y, w, h) = cv2.boundingRect(c)

    # Draw the bounding box on the frame and update the text
    cv2.rectangle(frame, (x,y), (x+w, y+h), (0, 255, 0), 2)
    text = "Occupied"

    # Draw the text and timestamp on the frame
    cv2.putText(frame, "Room Status: {}".format(text), (10,20), \
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
    cv2.putText(frame, \
            datetime.datetime.now().strftime("%A %d %B %Y %I:%M:%S%p"), \
            (10, frame.shape[0] - 10), \
            cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)

    # Show the frame and record if the user presses a key
    cv2.imshow("Security Feed", frame)
    cv2.imshow("Thresh", thresh)
    cv2.imshow("Frame Delta", frameDelta)
    key = cv2.waitKey(1) & 0xFF

    # If 'q' is pressed, break from the loop
    if key == ord("q"):
        break

# Cleanup the camera and close any open windows
camera.release()
cv2.destroyAllWindows()

