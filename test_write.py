import asyncio
import cv2

import asyncio
import cv2


async def capture_stream(stream_url, output_dir, stop_capture_event):
    """
    This asynchronous function captures frames from an MJPEG stream and writes them to disk.

    Args:
        stream_url (str): URL or path to the MJPEG stream.
        output_dir (str): Directory to save captured frames.
        stop_capture_event (asyncio.Event): Event to signal stopping capture.
    """
    # Open video capture object
    cap = cv2.VideoCapture(stream_url)

    # Check if video capture object is opened successfully
    if not cap.isOpened():
        print("Error opening video stream or file")
        return

    # Frame counter
    frame_count = 0

    while not stop_capture_event.is_set():
        # Capture frame-by-frame
        ret, frame = cap.read()

        # Check if frame is read correctly
        if not ret:
            print("Can't receive frame (stream end?). Exiting...")
            break

        # Generate filename
        filename = f"{output_dir}/frame_{frame_count}.jpg"

        # Write the frame to disk asynchronously
        await asyncio.create_task(cv2.imwrite(filename, frame))

        # Increment frame counter
        frame_count += 1
        print(f"Frame count: {frame_count}")

    # Release the video capture object
    cap.release()
    print("Stream capture stopped.")


async def main():
    # Define stream URL, output directory, and stop flag
    stream_url = "http://bl04i-di-serv-01.diamond.ac.uk:8080/OAV.XTAL.mjpg"
    output_dir = "/scratch/ffd84814/images_playground"
    stop_capture = asyncio.Event()  # Initially not set

    # Start capture task
    capture_task = asyncio.create_task(
        capture_stream(stream_url, output_dir, stop_capture)
    )

    print(f"Current stop flag is {stop_capture.is_set()} waiting 10 seconds")
    # Simulate external condition to stop capture (replace with your logic)
    await asyncio.sleep(10)  # Stop after 10 seconds (replace with your condition)
    print(
        f"10 seconds passed, going to set stop flag to False, currently {stop_capture.is_set()}"
    )
    stop_capture.set()  # Set the stop event
    print(f"Flag set to {stop_capture.is_set()}")

    print("Wait for capture task to finish")
    await capture_task


if __name__ == "__main__":
    asyncio.run(main())
