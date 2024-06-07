from ophyd import Device

import redis
import json
import numpy as np
import cv2
import pickle
from dodal.devices.oav.oav_detector import OAV
from dodal.devices.smargon import Smargon
from uuid import uuid4
from redis_client import RedisClient
from ophyd.status import Status



class MurkoTrigger(Device):
    def __init__(self, oav: OAV, smargon: Smargon, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.redis = RedisClient(host="ws561.diamond.ac.uk")
        self.oav = oav
        self.smargon = smargon
        self.sample_id = None

    def trigger(self):
        """
        This asynchronous function captures frames from an MJPEG stream, writes a subset to disk,
        and continues until the stop_flag variable is set to False.

        Args:
            stream_url (str): URL or path to the MJPEG stream.
            start_frame (int): Starting frame for the subset.
            end_frame (int): Ending frame (exclusive) for the subset.
            stop_flag (asyncio.Event): Flag to signal stopping the capture.
            frame_queue (asyncio.Queue): Queue to store captured frames for writing.
        """
        stream_url = "http://bl04i-di-serv-01.diamond.ac.uk:8080/OAV.mjpg.mjpg"
        # Open the video capture object
        cap = cv2.VideoCapture(stream_url)

        # Check if video capture object is opened successfully
        if not cap.isOpened():
            print("Error opening video stream or file")
            return

        # extract static metadata from beamline
        zoom_percentage = self.oav.zoom_controller.percentage.get()
        microns_per_x_pixel = self.oav.parameters.micronsPerXPixel
        microns_per_y_pixel = self.oav.parameters.micronsPerYPixel
        beam_centre_i = self.oav.parameters.beam_centre_i
        beam_centre_j = self.oav.parameters.beam_centre_j

        # Process video frames
        # Capture frame-by-frame
        ret, frame = cap.read()
        # extract updated smargon omega angle
        smargon_omega_angle = self.smargon.omega.get(use_monitor=False).user_readback
        frame_count = 0
        print(f"frame {frame_count} omega_angle is {smargon_omega_angle}")
        uuid = str(uuid4())
        metadata = {
            "uuid": uuid,
            "omega_angle": smargon_omega_angle,
            "zoom_percentage": zoom_percentage,
            "microns_per_x_pixel": microns_per_x_pixel,
            "microns_per_y_pixel": microns_per_y_pixel,
            "beam_centre_i": beam_centre_i,
            "beam_centre_j": beam_centre_j,
            "sample_id": self.sample_id,
        }

        # Release the video capture object
        cap.release()
        print("Stream capture stopped.")

        image_np = np.array(frame)
        # Send metadata and image to REDIS
        self.redis.hset("test-metadata", uuid, json.dumps(metadata))
        self.redis.hset("test-image", uuid, pickle.dumps(image_np))
        self.redis.publish("murko", json.dumps(metadata))
        print("Frame writing task completed.")
        return Status(done=True, success=True)


if __name__ == "__main__":
    from bluesky.run_engine import RunEngine
    from dodal.beamlines import i04
    re = RunEngine()
    murko_trigger = MurkoTrigger(name="murko-trigger", smargon = i04.smargon(), oav = i04.oav())
    murko_trigger.wait_for_connection()
    import bluesky.plan_stubs as bps
    re(bps.trigger(murko_trigger))
