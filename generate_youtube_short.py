from openai import OpenAI
import replicate
import requests
import subprocess
import sys
from datetime import timedelta
import os
import whisper
import pydub
from dotenv import load_dotenv
from urllib.parse import urlparse, unquote
from comfy_ws_svd import execute_prompt
from tqdm import tqdm
import time
from captionmaker import autocaption
import youtube_upload
import config
# OpenAI API client
client = OpenAI()

# ElevenLabs API settings
elevenlabs_url = "https://api.elevenlabs.io/v1/text-to-speech/"
elevenlabs_headers = {
    "Accept": "audio/mpeg",
    "Content-Type": "application/json",
    "xi-api-key": "11cd64da7c1f909172cea394262f78e0"
}
CHUNK_SIZE = 1024

elevenlabs_payload_template = {
    "model_id": "dTdcoyzdN7pUNL77bZfP",
    "text": "<string>",
    "voice_settings": {
        "similarity_boost": 123,
        "stability": 123,
        "style": 123,
        "use_speaker_boost": True
    }
}


def generate_image_prompt(topic):
    response = client.chat.completions.create(
        model="gpt-4-1106-preview",
        messages=[{"role": "system", "content": "You are a helpful assistant."},
                  {"role": "user", "content": f"""Generate an artistic prompt for an AI-created girl image related to the theme: {topic}. 
                                                  Here's an example: (Masterpiece, best quality:1.2), Hyper realistic, ultra detailed full body photograph of a woman with messy blond hair (pink highlights) wearing an off shoulder slim sweater, laughing out loud and dancing, sunlight fractal details, depth of field, detailed gorgeous face, natural body posture, captured with a 85mm lens, f4. 6, bokeh, ultra detailed, ultra accurate detailed, bokeh lighting, surrealism, ultra unreal engine, intricate, epic, freckles.
                                                  'You must follow a similar format as the prompt above. ONLY return the prompt that would be used and nothing else. Do not say anything else."""}],
    )
    print("Image Prompt \n", response.choices[0].message.content)
    return response.choices[0].message.content


def generate_script(topic):
    response = client.chat.completions.create(
        model="gpt-4-1106-preview",
        messages=[{"role": "system", "content": "You are a helpful assistant."},
                  {"role": "user", "content": f"Write an interesting and extremely unknown fact about {topic}. This should be a unique and obscure fact that is not commonly mentioned in history books or popular media. Make it like a formal informational script where one person is doing a voiceover for a 60 second Youtube shorts video while providing detail but being concise. Phrase it as if you were talking in real life. Only return the full dialogue as a paragraph/paragraphs. Do not format your response like a script. Make sure it is concise enough that if read out loud it is around a minute long."}],
    )
    print("Script \n", response.choices[0].message.content)
    return response.choices[0].message.content


def generate_title(script):
    response = client.chat.completions.create(
        model="gpt-4-1106-preview",
        messages=[{"role": "system", "content": "You are a helpful assistant."},
                  {"role": "user", "content": f"Create a clickbait Youtube short title based on the follow script: {script}"}],
    )
    print("Title \n", response.choices[0].message.content)
    return response.choices[0].message.content


def generate_description(script):
    response = client.chat.completions.create(
        model="gpt-4-1106-preview",
        messages=[{"role": "system", "content": "You are a helpful assistant."},
                  {"role": "user", "content": f"Create a interesting, concise, but detailed description for a Youtube short based on the following script: {script}"}],
    )
    print("Description \n", response.choices[0].message.content)
    return response.choices[0].message.content


def generate_anime_girl_video(prompt):
    image_path = execute_prompt(prompt)
    # Assuming you have a function to generate an anime girl image
    # Replace this line with the actual function call
    return image_path


def create_voiceover(script, voice_id):
    data = {
        "text": script,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.5
        }
    }

    response = requests.post(elevenlabs_url+voice_id, json=data,
                             headers=elevenlabs_headers)

    print("Voiceover Status\n", response.status_code)

    if response.status_code == 200:
        with open('voiceover.mp3', 'wb') as f:
            for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                if chunk:
                    f.write(chunk)
        return True
    return False


def get_audio_duration(file_path):
    cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
           '-of', 'default=noprint_wrappers=1:nokey=1', file_path]
    result = subprocess.run(cmd, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)
    duration = float(result.stdout)
    return duration


def adjust_voiceover_duration(voiceover_path, target_duration=60):
    # Get the current duration of the voiceover
    current_duration = get_audio_duration(voiceover_path)

    # Calculate the speed factor
    speed_factor = current_duration / target_duration
    if speed_factor < 0.5 or speed_factor > 2.0:
        raise ValueError(
            "Speed change is out of the feasible range (0.5x - 2.0x)")

    # Apply the speed change using FFmpeg
    adjusted_voiceover_path = 'adjusted_voiceover.mp3'
    subprocess.run(['ffmpeg', '-y', '-i', voiceover_path, '-filter:a',
                   f'atempo={speed_factor}', '-vn', adjusted_voiceover_path])

    return adjusted_voiceover_path


def loop_video(input_file, duration=60):
    output_file = 'output_loop_9_16.mp4'
    # Crop to a 9:16 aspect ratio and scale to 1080x1920
    subprocess.run(['ffmpeg', '-y', '-stream_loop', '-1', '-i', input_file, '-vf', 'crop=576:1024,scale=1080:1920',
                   '-t', str(duration), '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '22', output_file])
    return output_file


def format_timedelta(td):
    """Return a string properly formatted for SRT files: 'hh:mm:ss,ms'"""
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = td.microseconds // 1000
    return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"


def approximate_timing(duration, total_words, word_start, word_end):
    """Approximate the start and end times based on word position."""
    start_ratio = word_start / total_words
    end_ratio = word_end / total_words
    start_time = duration * start_ratio
    end_time = duration * end_ratio
    return timedelta(seconds=start_time), timedelta(seconds=end_time)

# def transcribe_audio(path, chunk_length=10000):
#     # Load the model
#     model = whisper.load_model("base")
#     print("Whisper model loaded.")

#     # Load the audio file
#     audio = pydub.AudioSegment.from_file(path)

#     # Split the audio file into chunks
#     chunks = pydub.utils.make_chunks(audio, chunk_length)

#     # Create the SrtFiles directory if it does not exist
#     os.makedirs("SrtFiles", exist_ok=True)

#     # srt_filename = os.path.join("SrtFiles", "voiceover.srt")
#     with open('voiceover.srt', 'w', encoding='utf-8') as srtFile:
#         chunk_start = 0.0
#         for i, chunk in enumerate(chunks):
#             # Save chunk to a temporary file
#             chunk_file = f"./SrtFiles/temp_chunk_{i}.wav"
#             chunk.export(chunk_file, format="wav")

#             # Transcribe the chunk
#             result = model.transcribe(chunk_file)
#             segments = result['segments']
#             for segment in segments:
#                 start_time = format_timedelta(
#                     timedelta(seconds=segment['start'] + chunk_start))
#                 end_time = format_timedelta(
#                     timedelta(seconds=segment['end'] + chunk_start))
#                 text = segment['text'].strip()
#                 segment_id = i + 1
#                 srtFile.write(
#                     f"{segment_id}\n{start_time} --> {end_time}\n{text}\n\n")

#             # Update chunk_start to the end of the current chunk
#             chunk_start += chunk.duration_seconds

#     # Clean up temporary files
#     for i in range(len(chunks)):
#         os.remove(f"./SrtFiles/temp_chunk_{i}.wav")

#     return 'voiceover.srt'


def transcribe_audio(path, words_per_segment=5):
    model = whisper.load_model("base")
    print("Whisper model loaded.")

    # Transcribe the audio file
    result = model.transcribe(audio=path)
    full_transcript = result['text']
    words = full_transcript.split()
    total_words = len(words)

    # Get duration of the audio file using pydub
    audio = pydub.AudioSegment.from_file(path)
    duration_seconds = len(audio) / 1000.0  # Convert milliseconds to seconds

    # Create the SrtFiles directory if it does not exist
    os.makedirs("SrtFiles", exist_ok=True)

    srt_filename = os.path.join("SrtFiles", "voiceover.srt")
    with open("voiceover.srt", 'w', encoding='utf-8') as srtFile:
        segment_id = 1
        for i in range(0, total_words, words_per_segment):
            segment_text = words[i:i+words_per_segment]
            word_start = i
            word_end = min(i + words_per_segment, total_words)
            segment_start, segment_end = approximate_timing(
                duration_seconds, total_words, word_start, word_end)

            start_time = format_timedelta(segment_start)
            end_time = format_timedelta(segment_end)
            srtFile.write(
                f"{segment_id}\n{start_time} --> {end_time}\n{' '.join(segment_text)}\n\n")
            segment_id += 1

    return "voiceover.srt"


def add_subtitles(video_file, voiceover_file, srt_file):
    timestamp = int(time.time())
    output_file = f'final_video_{timestamp}.mp4'
    subprocess.run([
        'ffmpeg', '-y',  # Automatically overwrite existing files
        '-i', video_file,  # Input video file
        '-i', voiceover_file,  # Input audio file (voiceover)
        '-vf', f"subtitles={srt_file}:force_style='Fontname=Trebuchet MS,PrimaryColour=&H03fcff,Alignment=10,MarginV=25,Spacing=0.8'",
        '-c:v', 'libx264',  # Video codec
        '-c:a', 'aac',  # Audio codec
        '-strict', 'experimental',  # Allow the use of experimental AAC codec
        '-b:a', '192k',  # Audio bitrate
        output_file  # Output file
    ])

    return output_file


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


def add_replicate_subtitles(video_path):
    load_dotenv()  # This loads the variables from .env
    os.environ["REPLICATE_API_TOKEN"] = os.getenv("REPLICATE_API_TOKEN")
    if video_path.startswith('http://') or video_path.startswith('https://'):
        video_path = video_path
    else:
        video_path = open(video_path, 'rb')
        print("Video opened for replicate captions")
    # print("Dense vid path", self.video_path)
    print("Generating Captions  ...")
    output = replicate.run(
        "fictions-ai/autocaption:18a45ff0d95feb4449d192bbdc06b4a6df168fa33def76dfc51b78ae224b599b",
        input={
            "video_file_input": video_path,
            "output_video": True,
        }
    )
    if not isinstance(video_path, str):
        video_path.close()
    caption_video_path = download_mp4(
        output, "./shorts", "Final Short Video")
    return caption_video_path


def upload_to_youtube(video_path, title, description):
    # Upload the video to YouTube
    config.youtube["title"] = title + " #shorts"
    print("Config Title", config.youtube["title"])
    config.youtube["description"] = description

    print("Full config", config.youtube)
    print("Uploading to Youtube...")
    uploaded = youtube_upload.upload(video_path, config.youtube)

    return uploaded


def create_short(topic, voice_id):
    # Generate script
    script = generate_script(topic)

    # Generate title
    title = generate_title(script)

    # Generate description
    description = generate_description(script)

    # Generate image prompt and anime girl image
    image_prompt = generate_image_prompt(script)

    # anime_girl_video = generate_anime_girl_video(image_prompt)

    anime_girl_video = "./test_anime_vid.mp4"

    # Create voiceover
    if not create_voiceover(script, voice_id):
        print("Failed to create voiceover")
        return

    # Adjust voiceover length
    adjusted_voiceover = adjust_voiceover_duration('voiceover.mp3')

    # Loop and format video
    print("Creating video loop")
    looped_video = loop_video(anime_girl_video)

    # Transcribe and create SRT file
    print("Creating captions")
    srt_file = transcribe_audio(adjusted_voiceover)

    # # Add Replicate Subtitles
    # print("Adding Replicate Subtitles")
    # caption_video_path = add_replicate_subtitles(looped_video)

    # # Add autocaptions
    # print("Add autocaptions")
    # videofilename = looped_video  # Replace with your video file path
    # v_type = "reels"  # Example, adjust as needed
    # subs_position = "bottom75"  # Example, adjust as needed
    # highlight_color = "yellow"  # Example, adjust as needed
    # fontsize = 10.0  # Example, adjust as needed
    # opacity = 0.5  # Example, adjust as needed
    # MaxChars = 20  # Example, adjust as needed
    # color = "white"  # Example, adjust as needed

    # caption_video_path = autocaption.add_subtitle(
    #     videofilename, adjusted_voiceover, v_type, subs_position, highlight_color, fontsize, opacity, MaxChars, color)
    # print("Captioned video created at:", caption_video_path)

    # Add subtitles to video
    print("Combining video and audio")
    final_video = add_subtitles(looped_video, adjusted_voiceover, srt_file)

    print("Short created successfully!")

    print("Starting Youtube upload")
    upload_to_youtube(final_video, title, description)


# Example usage
create_short("unusual and mysterious history facts", "UTNUxrT2AypU740wiD5i")
