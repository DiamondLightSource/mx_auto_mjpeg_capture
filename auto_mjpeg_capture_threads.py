#!/usr/bin/env python
# coding: utf-8


from epics import PV, poll
from epics.ca import CAThread

import cv2
import re

import sys
from pprint import pprint
import time


class CaptureData(object):
    def __init__(
        self,
        epics_pvs,
        gdalog="/dls_sw/i04/logs/gda-server.log",
        list_of_patterns=["BLSampleID"],
        buffer_size=1024,
    ):
        self.epics_pvs = epics_pvs
        self.PV_instances = {}
        self.gda_log = gdalog
        self.list_of_patterns = list_of_patterns
        self.buffer_size = buffer_size

    def setup_PVs(self):
        for PV_human, PV_str in epics_PVs.items():
            self.PV_instances[PV_human] = PV(PV_str)

    def get_PV_data(self):
        data_payload = {}
        for PV_human, pv_instance in self.PV_instances.items():
            data_payload[PV_human] = pv_instance.get()

        return data_payload

    def get_last_matching_line(filename, pattern="BLSampleID"):
        with open(filename, "rb") as f:
            # Move the file pointer near the end (adjustable bugger size):
            buffer_size = self.buffer_size
            f.seek(-buffer_size, 2)

            # Read the last part of the file
            last_chunk = f.read()

            # search for pattern in reverse order using re
            last_line = (
                re.search(
                    rb".*?(" + re.escape(pattern.encode()) + rb")$",
                    last_chunk,
                    re.M | re.I,
                )
                .group(1)
                .decode()
            )

            return last_line if last_line else None


class CaptureMJPEG(object):
    def __init__(self, image_folder_root, start_capture_on=1):
        self.run_capture = False
        self.start_capture_on = start_capture_on
        self.threads = []
        self.thread_running_since = time.time()
        self.image_folder_root = image_folder_root

    def capture_mjpeg(
        self,
        url="http://bl04i-di-serv-01.diamond.ac.uk:8080/OAV.XTAL.mjpg",
        max_video_time=25,
    ):
        start_time = time.time()
        cap = cv2.VideoCapture(url)

        if not cap.isOpened():
            print("Error opening MJPEG stream")
            return

        print("Making folders")
        if json.loads(redis.get("robot_counter")):
            self.count = json.loads(redis.get("robot_counter")) + 1
        else:
            self.count = 1

        print(f"New count image is {self.count}")
        redis.set("robot_counter", json.dumps(self.count))
        count_fill = str(self.count).zfill(4)
        self.image_folder = f"{self.image_folder_root}/images_test_{count_fill}/"
        dir_path = pathlib.Path(self.image_folder)
        print(f"Made folder {self.image_folder}")
        try:
            dir_path.mkdir()
        except Exception as e:
            print(f"had issue making folder {self.image_folder} with error {e}")
        frame_count = 0

        print("Frame count set to zero, ready to enter while loop")
        while time.time() - start_time < max_video_time:
            frame_count_zfill = str(frame_count).zfill(4)
            print(f"Frame count: {frame_count}")
            ret, frame = cap.read()
            if not ret:
                print("Can't receive frame. Maybe the stream ended?. Existing...")
                break
            filename = f"frame_{frame_count_zfill}.jpg"

            full_path = f"{self.image_folder}/{filename}"
            cv2.imwrite(full_path, frame)
            print(f"Wrote {full_path} to disk")
            frame_count += 1

        cap.release()
        print("Streaming processing for this crystal complete")
        return

    def capture_jpeg(
        self, url="http://bl04i-di-serv-01.diamond.ac.uk:8080/OAV.XTAL.jpg"
    ):
        pass

    def test_capture_logic(self, pv):
        while self.run_capture:
            print(f"Should be capturing while {pv.get()} is 1")
            poll(1.0)
            time.sleep(0.2)
            if pv.get() != self.start_capture_on:
                break
        print("Finished capturing")

    def start_capturing(self, *args, **kargs):
        # print(f"args")
        # pprint(args)
        # print(f"kargs")
        # pprint(kargs)
        if self.trigger_pv.get():
            # self.test_capture_logic(kargs["cb_info"][1])
            self.test_capture_logic(self.trigger_pv)

        else:
            pass

    def trigger_capture(self, **kwargs):
        self.trigger_value = kwargs["cb_info"][0]
        self.trigger_pv = kwargs["cb_info"][1]
        if len(self.threads) > 0:
            print("A thread is already running. Will not create another one")
            pass
        elif self.trigger_value == 0:
            print(
                "This python callback trigger was run on the return of the PV to 0. Ignoring it. Only trigger move when the PV changes to 1"
            )
            pass
        else:
            print("Creating new thread to run the mjpeg capture")
            new_thread = CAThread(target=self.capture_mjpeg)
            self.threads.append(new_thread)
            new_thread.start()
            self.thread_running_since = time.time()


if __name__ == "__main__":
    from beamline import redis
    import json
    import pathlib

    image_folder_root = f"/scratch/ffd84814/"

    pv2monitor = PV("BL04I-EA-THAW-01:CTRL")
    cap_mjpg = CaptureMJPEG(start_capture_on=1, image_folder_root=image_folder_root)

    cap_pvs = CaptureData(
        epics_pvs={"zoom_level": "BL04I-EA-OAV-01:FZOOM:MP:SELECT"},
    )

    print("Starting...")
    print(f"Current thawer state is  {pv2monitor.get()}")
    pv2monitor.add_callback(callback=cap_mjpg.trigger_capture)
    print("Added call back PV")
    sys.stdout.flush()

    while True:
        poll(0.5)
        print(
            f"Number of threads: {len(cap_mjpg.threads)} and thread running since {time.time() - cap_mjpg.thread_running_since}"
        )
        if len(cap_mjpg.threads) == 1:
            print(f"Is thread alive? {cap_mjpg.threads[0].is_alive()}")
            if not cap_mjpg.threads[0].is_alive():
                cap_mjpg.threads.pop()
                print(f"Thread taken away from list")
        sys.stdout.flush()

    import code

    code.interact(local=locals())
