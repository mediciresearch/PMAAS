import subprocess
import json
import os


def get_video_info(video_path):
    """
    Get width and height of the video.

    :param video_path: Path to the video file.
    :return: width, height
    """
    cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0",
           "-show_entries", "stream=width,height", "-of", "json", video_path]
    result = subprocess.run(cmd, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)
    info = json.loads(result.stdout)
    width = info['streams'][0]['width']
    height = info['streams'][0]['height']
    return width, height


def crop_video_center(input_path, output_path):
    """
    Crop the video to 512x512 centered.

    :param input_path: Path to the input video.
    :param output_path: Path to save the cropped video.
    """
    width, height = get_video_info(input_path)

    # Check if video dimensions are too small
    if width < 512 or height < 512:
        raise ValueError(
            "Video dimensions are too small to be cropped to 512x512.")

    # Calculate the cropping area
    x = (width - 512) // 2
    y = (height - 512) // 2

    # Crop and save the video using ffmpeg
    cmd = ["ffmpeg", "-i", input_path, "-vf",
           f"crop=512:512:{x}:{y}", "-c:a", "copy", output_path]
    subprocess.run(cmd)


# Example usage
# try:
#     input_video_path = 'path/to/your/input/video.mp4'
#     output_video_path = 'path/to/your/output/cropped_video.mp4'
#     crop_video_center(input_video_path, output_video_path)
#     print("Video cropped successfully.")
# except ValueError as e:
#     print(e)
# except Exception as e:
#     print(f"An error occurred: {e}")
