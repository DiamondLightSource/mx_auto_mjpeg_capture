import asyncio
import json
import pickle
import time
import numpy as np

from uuid import uuid4
from redis_client import RedisClient
import aiofiles
import cv2

from dodal.beamlines import i04

# instantiate smargon device
smargon = i04.smargon()
smargon.wait_for_connection()

# instantiate oav device
oav = i04.oav()
oav.wait_for_connection()

# setup redis client
redis = RedisClient(host="ws561.diamond.ac.uk")


async def capture_stream(stream_url, stop_flag, frame_queue: asyncio.Queue):
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
    # Open the video capture object
    cap = cv2.VideoCapture(stream_url)

    # Check if video capture object is opened successfully
    if not cap.isOpened():
        print("Error opening video stream or file")
        return

    # extract static metadata from beamline
    zoom_percentage = oav.zoom_controller.percentage.get()
    microns_per_x_pixel = oav.parameters.micronsPerXPixel
    microns_per_y_pixel = oav.parameters.micronsPerYPixel
    beam_centre_i = oav.parameters.beam_centre_i
    beam_centre_j = oav.parameters.beam_centre_j

    # Process video frames
    last_time = time.time()
    frame_count = 0
    while not stop_flag.is_set():
        # Capture frame-by-frame
        ret, frame = cap.read()
        # extract updated smargon omega angle
        smargon_omega_angle = smargon.omega.get(use_monitor=False).user_readback
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
        }
        # Check if frame is read correctly
        if not ret:
            print("Can't receive frame (stream end?). Exiting...")
            break

        # Add frame to queue for writing (asynchronous)
        await frame_queue.put((frame_count, frame, metadata, uuid))
        print(f"Frame speed {1/(time.time()-last_time)} Hz")
        last_time = time.time()
        # Increment frame counter
        frame_count += 1

    # Release the video capture object
    cap.release()
    print("Stream capture stopped.")


async def write_frames(frame_queue, stop_flag):
    """
    This asynchronous function writes frames from the queue to disk if within the specified range.

    Args:
        frame_queue (asyncio.Queue): Queue containing captured frames.
        stop_flag (asyncio.Event): Flag to signal stopping the capture.
        start_frame (int): Starting frame for the subset.
        end_frame (int): Ending frame (exclusive) for the subset.
    """
    while not stop_flag.is_set():
        # Get frame data from queue (asynchronous)
        frame_count, frame, metadata, uuid = await frame_queue.get()
        # Check if within the frame range and write to disk
        # filename = f"frame_{frame_count}.jpg"
        # cv2.imwrite(filename, frame)
        # with open(filename+"_metadata","w") as f:
        #    f.write(json.dumps(metadata))
        # print(f"Writing frame {filename}")
        image_np = np.array(frame)
        # Send metadata and image to REDIS
        if frame_count == 1 or frame_count % 15 == 0:
            redis.hset("test-metadata", uuid, json.dumps(metadata))
            redis.hset("test-image", uuid, pickle.dumps(image_np))
            redis.publish("murko", json.dumps(metadata))
    # Indicate queue completion
    print("Frame writing task completed.")


async def main():
    # Define stream URL, frame range, and stop flag
    #stream_url = "http://bl04i-di-serv-01.diamond.ac.uk:8080/OAV.mjpg.mjpg"
    stream_url = "http://bl04i-di-serv-01.diamond.ac.uk:8080/OAV.XTAL.mjpg"
    stop_flag = asyncio.Event()

    # Create queues
    frame_queue = asyncio.Queue(1)

    # Run capture and write tasks asynchronously
    tasks = [
        asyncio.create_task(capture_stream(stream_url, stop_flag, frame_queue)),
        asyncio.create_task(write_frames(frame_queue, stop_flag)),
    ]

    # Set flag to stop after some time (replace with your condition)
    await asyncio.sleep(0.05)  # Change this to your stopping condition
    stop_flag.set()

    # Wait for all tasks to complete
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
