import asyncio
import time

import aiofiles
import aiohttp


async def capture_stream_aiohttp(url, stop_flag, queue):
    frame_count = 0
    last_time = time.time()
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            while not stop_flag.is_set():
                line = await response.content.readline()
                if not line:
                    break
                # JPEGs start with \xff\xd8 and end with \xff\xd9
                if line.startswith(b"\xff\xd8"):
                    frame_data = line + await response.content.readuntil(b"\xff\xd9")
                    await queue.put((frame_count, frame_data))
                    frame_count += 1
                    print(f"Frame speed {1/(time.time()-last_time)} Hz")
                    last_time = time.time()


async def write_frames_aiofiles(frame_queue, stop_flag, robot_load_counter):
    while not stop_flag.is_set():
        # Get frame data from queue (asynchronous)
        frame_count, frame = await frame_queue.get()

        # Check if within the frame range and write to disk
        async with aiofiles.open(
            f"/scratch/ffd84814/images_test_{robot_load_counter}/frame_{frame_count}.jpg",
            mode="wb",
        ) as f:
            await f.write(frame)

    # Indicate queue completion
    print("Frame writing task completed.")


async def main(counter):
    # Define stream URL, frame range, and stop flag
    stream_url = "http://bl04i-di-serv-01.diamond.ac.uk:8080/OAV.XTAL.mjpg"
    stop_flag = asyncio.Event()

    # Create queues
    frame_queue = asyncio.Queue()

    # Run capture and write tasks asynchronously
    tasks = [
        asyncio.create_task(capture_stream_aiohttp(stream_url, stop_flag, frame_queue)),
        asyncio.create_task(write_frames_aiofiles(frame_queue, stop_flag, counter)),
    ]

    # Set flag to stop after some time (replace with your condition)
    await asyncio.sleep(20)  # Change this to your stopping condition
    stop_flag.set()

    # Wait for all tasks to complete
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    from beamline import redis
    import json
    import pathlib

    count = json.loads(redis.get("robot_counter"))
    count = count + 1
    count_fill = str(count).zfill(4)
    dir_path = pathlib.Path(f"/scratch/ffd84814/images_test_{count_fill}/")
    dir_path.mkdir()
    asyncio.run(main(count_fill))
