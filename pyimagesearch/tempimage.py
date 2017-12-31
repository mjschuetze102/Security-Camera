import uuid
import os

class TempImage:
    def __init__(self, basePath="./", ext=".jpg"):
        # Construct the file path
        self.path = "{base_path}/{rand}{ext}".format(base_path=basePath, \
                rand=str(uuid.uuid4()), ext=ext)

    def cleanup(self):
        # Remove the file
        os.remove(self.path)
