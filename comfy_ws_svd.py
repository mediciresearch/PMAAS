# This is an example that uses the websockets api to know when a prompt execution is done
# Once the prompt execution is done it downloads the images using the /history endpoint

# NOTE: websocket-client (https://github.com/websocket-client/websocket-client)
import websocket
import uuid
import json
import urllib.request
import urllib.parse
import glob
import os

server_address = "127.0.0.1:8188"
client_id = str(uuid.uuid4())


def queue_prompt(prompt):
    p = {"prompt": prompt, "client_id": client_id}
    data = json.dumps(p).encode('utf-8')
    req = urllib.request.Request(
        "http://{}/prompt".format(server_address), data=data)
    print("Prompt Response\n", json.loads(urllib.request.urlopen(req).read()))
    return json.loads(urllib.request.urlopen(req).read())


def get_image(filename, subfolder, folder_type):
    data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    url_values = urllib.parse.urlencode(data)
    with urllib.request.urlopen("http://{}/view?{}".format(server_address, url_values)) as response:
        image_data = response.read()
        # Assuming you want to save the image to a file
        with open(filename, 'wb') as f:
            f.write(image_data)
        return image_data


def get_history(prompt_id):
    with urllib.request.urlopen("http://{}/history/{}".format(server_address, prompt_id)) as response:
        response_data = response.read()
        print("History\n", response_data)
        return json.loads(response_data)


def get_most_recent_image(folder_path, image_extensions=['*.png', '*.jpg', '*.jpeg', '*.gif']):
    # List all image files in the folder
    image_files = []
    for extension in image_extensions:
        image_files.extend(glob.glob(os.path.join(folder_path, extension)))

    # Sort the files by modification time
    most_recent_image = max(image_files, key=os.path.getmtime, default=None)

    return most_recent_image


def get_images(ws, prompt):
    prompt_id = queue_prompt(prompt)['prompt_id']
    print(prompt_id)
    output_images = {}
    while True:
        out = ws.recv()
        if isinstance(out, str):
            message = json.loads(out)
            if message['type'] == 'executing':
                data = message['data']
                if data['node'] is None and data['prompt_id'] == prompt_id:
                    break  # Execution is done
        else:
            continue  # previews are binary data

    history = get_history(prompt_id)[prompt_id]
    # print(history)
    images_output = []
    for o in history['outputs']:
        for node_id in history['outputs']:
            node_output = history['outputs'][node_id]
            if 'images' in node_output:
                images_output = []
                for image in node_output['images']:
                    # print(image['filename'], image['subfolder'], image['type'])
                    # image_data = get_image(
                    #     image['filename'], image['subfolder'], image['type'])
                    images_output.append(image['filename'])
            output_images[node_id] = images_output

    print("Output Images\n", output_images)
    recent_image = get_most_recent_image(
        "C:\\Users\\rohan\\Documents\\ComfyUI\\output\\")
    return recent_image


def fix_json_quotes(json_string):
    # Replace single quotes with double quotes
    fixed_json = json_string.replace("'", '"')

    # Additional replacements for common issues that might arise from the above replacement
    fixed_json = fixed_json.replace('"{', '{').replace('}"', '}')
    fixed_json = fixed_json.replace('["', '[').replace(']"', ']')

    return fixed_json


prompt_text = """
{
    "3": {
        "class_type": "KSampler",
        "inputs": {
            "cfg": 8,
            "denoise": 1,
            "latent_image": [
                "5",
                0
            ],
            "model": [
                "4",
                0
            ],
            "negative": [
                "7",
                0
            ],
            "positive": [
                "6",
                0
            ],
            "sampler_name": "euler",
            "scheduler": "normal",
            "seed": 8566257,
            "steps": 20
        }
    },
    "4": {
        "class_type": "CheckpointLoaderSimple",
        "inputs": {
            "ckpt_name": "dreamshaper_8.safetensors"
        }
    },
    "5": {
        "class_type": "EmptyLatentImage",
        "inputs": {
            "batch_size": 1,
            "height": 512,
            "width": 512
        }
    },
    "6": {
        "class_type": "CLIPTextEncode",
        "inputs": {
            "clip": [
                "4",
                1
            ],
            "text": "masterpiece best quality girl"
        }
    },
    "7": {
        "class_type": "CLIPTextEncode",
        "inputs": {
            "clip": [
                "4",
                1
            ],
            "text": "bad hands"
        }
    },
    "8": {
        "class_type": "VAEDecode",
        "inputs": {
            "samples": [
                "3",
                0
            ],
            "vae": [
                "4",
                2
            ]
        }
    },
    "9": {
        "class_type": "SaveImage",
        "inputs": {
            "filename_prefix": "girl",
            "images": [
                "8",
                0
            ]
        }
    }
}
"""


def execute_prompt(input_prompt):
    # prompt = json.loads('animate_loop_upscaled_workflow.json')
    with open('./animate_loop_upscaled_workflow.json', 'r') as file:
        prompt = json.load(file)
    # set the text prompt for our positive CLIPTextEncode
    prompt["3"]["inputs"]["text"] = input_prompt

    ws = websocket.WebSocket()
    ws.connect("ws://{}/ws?clientId={}".format(server_address, client_id))
    images = get_images(ws, prompt)
    print("Final Images\n", images)
    # return images[['101'][0]]\
    return images
    # Commented out code to display the output images:

    # for node_id in images:
    #     for image_data in images[node_id]:
    #         from PIL import Image
    #         import io
    #         image = Image.open(io.BytesIO(image_data))
    #         image.show()


# execute_prompt("A woman with pink hair smiling")
