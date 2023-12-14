import json
from urllib import request, parse
import random
from tqdm import tqdm
import glob
import os
import time


def get_most_recent_image(folder_path, image_extensions=['*.png', '*.jpg', '*.jpeg', '*.gif']):
    # List all image files in the folder
    image_files = []
    for extension in image_extensions:
        image_files.extend(glob.glob(os.path.join(folder_path, extension)))

    # Sort the files by modification time
    most_recent_image = max(image_files, key=os.path.getmtime, default=None)

    return most_recent_image


def queue_prompt(prompt_workflow):
    p = {"prompt": prompt_workflow}
    data = json.dumps(p).encode('utf-8')
    # req =  request.Request("http://192.168.0.37:8188/prompt", data=data)
    req = request.Request("http://127.0.0.1:8188/prompt", data=data)
    request.urlopen(req)

    return get_most_recent_image("C:\\Users\\rohan\\Documents\\ComfyUI\\output\\")


def comfy_api(prompts):
    # load the workflow from fil, assign it to variable named prompt_workflow
    prompt_workflow = json.load(open('workflow_api.json'))

    # create a list of prompts
    prompt_list = prompts

    # give some easy-to-remember names to the nodes
    chkpoint_loader_node = prompt_workflow["4"]
    prompt_pos_node = prompt_workflow["6"]
    empty_latent_img_node = prompt_workflow["5"]
    ksampler_node = prompt_workflow["3"]
    save_image_node = prompt_workflow["9"]

    # load the checkpoint that we want.
    # make sure the path is correct to avoid 'HTTP Error 400: Bad Request' errors
    chkpoint_loader_node["inputs"]["ckpt_name"] = "aimaginationEvolved_v10.safetensors"

    # set image dimensions and batch size in EmptyLatentImage node
    empty_latent_img_node["inputs"]["width"] = 1024
    empty_latent_img_node["inputs"]["height"] = 1024
    empty_latent_img_node["inputs"]["batch_size"] = 1

    # for every prompt in prompt_list...
    for prompt in tqdm(prompt_list, desc="Processing Prompts"):
        # set the text prompt for positive CLIPTextEncode node
        prompt_pos_node["inputs"]["text"] = prompt

        # set a random seed in KSampler node
        ksampler_node["inputs"]["seed"] = random.randint(
            1, 18446744073709551614)

        # set filename prefix to be the same as prompt
        # (truncate to first 100 chars if necessary)
        fileprefix = prompt

        if len(fileprefix) > 100:
            fileprefix = fileprefix[:100]

        save_image_node["inputs"]["filename_prefix"] = fileprefix

        # everything set, add entire workflow to queue.
        most_recent_image = queue_prompt(prompt_workflow)

        # return "C:\\Users\\rohan\\Documents\\ComfyUI\\output\\" + fileprefix + ".png"
        return most_recent_image


# comfy_api(["Front view of a single anime girl standing wearing an elegant battle outfit, full body view."])
