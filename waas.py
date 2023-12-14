import argparse
import replicate
import requests
import os
from urllib.parse import urlparse, unquote
from dotenv import load_dotenv
from comfy import comfy_api
from video_utils import crop_video_center
from tqdm import tqdm


class WaaS():
    def __init__(self):
        load_dotenv()  # This loads the variables from .env
        os.environ["REPLICATE_API_TOKEN"] = os.getenv("REPLICATE_API_TOKEN")
        self.magic_output_folder = "./magic_output"
        self.densepose_output_folder = "./densepose_output"
        self.img_path = ""
        self.vid_path = ""

    def open_video(self, video_path):
        os.startfile(video_path)  # Works on Windows

    def download_mp4(self, url, download_folder, process_type):
        """
        Download an MP4 file from the given URL and save it with the same name in the specified download folder.

        :param url: URL of the MP4 file to download.
        :param download_folder: Folder where the MP4 file will be saved.
        """
        # Parse the URL to get the file name
        parsed_url = urlparse(url)
        file_name = os.path.basename(unquote(parsed_url.path))

        # Full path for the file to be saved
        file_path = os.path.join(download_folder, file_name)

        response = requests.get(url, stream=True)

        # Check if the request was successful
        if response.status_code == 200:
            with open(file_path, 'wb') as file:
                for chunk in tqdm(response.iter_content(chunk_size=1024), desc="Downloading " + process_type, unit="KB"):
                    if chunk:  # filter out keep-alive chunks
                        file.write(chunk)
            print(f"File downloaded successfully: {file_path}")
            return file_path
        else:
            print(
                f"Failed to download file. Status code: {response.status_code}")

    def gen_image_from_text(self, text_prompt):
        # Assuming comfy_api function generates an image from text and saves it
        print("Generating base image from prompt...")
        self.img_path = comfy_api([text_prompt])
        return self.img_path

    def gen_densepose_vid(self, vid_path):
        if vid_path.startswith('http://') or vid_path.startswith('https://'):
            self.video_path = vid_path
        else:
            self.video_path = open(vid_path, 'rb')

        # print("Dense vid path", self.video_path)
        print("Generating DensePose mask...")
        output = replicate.run(
            "chigozienri/densepose:e2466793b9a60a3891202f1b93527c5db7bbcd7dbb181c11958b50e25f2d55c3",
            input={
                "input": self.video_path,
                "model": "R_50_FPN_s1x",
                "overlay": False,
                "visualizer": "FineSegmentation"
            }
        )

        if not isinstance(self.video_path, str):
            self.video_path.close()

        denspose_path = self.download_mp4(
            output, self.densepose_output_folder, "DensePose Video")
        return denspose_path

    def gen_magic(self, img_path, vid_path):
        self.video_path = vid_path

        if img_path.startswith('http://') or img_path.startswith('https://'):
            # If the input is a URL
            self.img_path = img_path
        else:
            # If the input is a local file path
            self.img_path = open(img_path, 'rb')

        if vid_path.startswith('http://') or vid_path.startswith('https://'):
            self.video_path = vid_path
        else:
            self.video_path = open(vid_path, 'rb')

        print("Generating Animation...")
        output = replicate.run(
            "lucataco/magic-animate:e24ad72cc67dd2a365b5b909aca70371bba62b685019f4e96317e59d4ace6714",
            input={
                "image": self.img_path,
                "video": self.video_path,
                "guidance_scale": 7.5,
                "num_inference_steps": 50
            }
        )

        # If a file was opened, close it
        if not isinstance(self.img_path, str):
            self.img_path.close()

        if not isinstance(self.video_path, str):
            self.video_path.close()

        final_magic_vid_path = self.download_mp4(
            output, self.magic_output_folder, "MagicAnimate Video")
        return final_magic_vid_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Process input for WaaS system.")
    parser.add_argument(
        '--text', help="Text prompt to generate your image.", type=str, default=None)
    parser.add_argument(
        '--image', help="Path to an existing image.", type=str, default=None)
    parser.add_argument(
        '--video', help="Path to the video file.", type=str, required=True)

    args = parser.parse_args()

    # Check if both text and image are provided
    if args.text and args.image:
        raise ValueError(
            "Please provide either a text prompt or an image path, not both.")

    waas = WaaS()

    if args.text:
        # Generate an image from the text prompt
        img_path = waas.gen_image_from_text(args.text)
    elif args.image:
        # Use the provided image path
        img_path = args.image
    else:
        raise ValueError(
            "Either a text prompt or an image path must be provided.")

    video_path = args.video

    def get_densepose_video_path(waas_instance, video_path, densepose_output_folder):
        video_name = os.path.basename(video_path)
        densepose_video_path = os.path.join(
            densepose_output_folder, video_name)

        # Check if the video already exists in the densepose_output folder
        if os.path.isfile(densepose_video_path):
            print(f"Using existing densepose video: {densepose_video_path}")
        else:
            # If not, generate the video
            densepose_video_path = waas_instance.gen_densepose_vid(video_path)

        return densepose_video_path

    densepose_video_path = get_densepose_video_path(
        waas, video_path, './densepose_output')

    # Process the image and video
    magic_video_path = waas.gen_magic(
        img_path, densepose_video_path)

    waas.open_video(magic_video_path)
