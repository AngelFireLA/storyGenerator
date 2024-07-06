import ast
import os
import asyncio
import requests
from moviepy.editor import (ImageClip, TextClip, CompositeVideoClip,
                            concatenate_videoclips, AudioFileClip)
from utils import generate_image, download_image, generate_text_response

UNREAL_SPEECH_API_KEY = '8oeZGSawghm3WXy9yso2mnempCDNOwrABwCyJLAaHBiNO7fwKlqQCb'
UNREAL_SPEECH_VOICE_ID = 'Liv'  # You can change this to any available voice
UNREAL_SPEECH_BITRATE = '192k'
UNREAL_SPEECH_SPEED = '0'
UNREAL_SPEECH_PITCH = '1'
UNREAL_SPEECH_TIMESTAMP_TYPE = 'sentence'


def get_scenes(story, num_of_images):
    prompt = f"""You will be given a textual story. Your goal is to divide the story into {num_of_images} scenes 
    that will each be used to generate an AI Image, so think of a scene like a prompt. So the scenes must try to represent the story as good as possible, while respecting the 
    number of images and not include so much detail that the Image gener. The style of the images should be consistent. Once you know the prompts for all {num_of_images} 
    images, say ABCDEF:[the_actual_prompt_for_image1,the_actual_prompt_for_image2,...] with each element being the prompt 
    of a scene, like it was a python list of scenes. Remember that the image generator doesn't remember previous scene so 
    each scene's prompt must be standalone, without needing info from previous scenes. Remember that each scene must be 
    like it's a prompt for image generation, not as a story. Here is the story: {story}. Moreover, after saying 
    ABCDEF:[the prompts] you will also say HIJKLM:[part1, part2,..] in the same format on a new line with each part being 
    the whole part of the story that is represented by the corresponding scene. (I want to create a video from the images 
    and want to add TTS but for that I also need the actual parts of the story to read, that's why.)"""
    text_response = generate_text_response(prompt)
    text_response = text_response.split("ABCDEF:")[1].strip()
    image_prompt = text_response.split("HIJKLM:")[0].strip()
    image_prompt2 = text_response.split("HIJKLM:")[1].strip()
    while image_prompt[0] == " ":
        image_prompt = image_prompt[1:]
    image_prompts = ast.literal_eval(image_prompt)

    while image_prompt2[0] == " ":
        image_prompt2 = image_prompt2[1:]
    image_prompts2 = ast.literal_eval(image_prompt2)
    return image_prompts, image_prompts2


async def generate_story_images(image_prompts):
    filenames = []
    for i, prompt in enumerate(image_prompts):
        image = await generate_image(prompt)
        print(image)
        filename = f"image_{i}.jpg"
        await download_image(image, filename)
        print(f"Image saved to {filename}")
        filenames.append(filename)
    return filenames


def generate_tts_audio(text, task_id):
    response = requests.post(
        'https://api.v7.unrealspeech.com/synthesisTasks',
        headers={
            'Authorization': f'Bearer {UNREAL_SPEECH_API_KEY}'
        },
        json={
            'Text': text,
            'VoiceId': UNREAL_SPEECH_VOICE_ID,
            'Bitrate': UNREAL_SPEECH_BITRATE,
            'Speed': UNREAL_SPEECH_SPEED,
            'Pitch': UNREAL_SPEECH_PITCH,
            'TimestampType': UNREAL_SPEECH_TIMESTAMP_TYPE
        }
    )

    response_data = response.json()
    task_id = response_data['SynthesisTask']['TaskId']
    return task_id


def check_task_status(task_id):
    response = requests.get(
        f'https://api.v7.unrealspeech.com/synthesisTasks/{task_id}',
        headers={
            'Authorization': f'Bearer {UNREAL_SPEECH_API_KEY}'
        }
    )
    return response.json()


def download_audio_file(output_uri, filename):
    response = requests.get(output_uri)
    with open(filename, 'wb') as file:
        file.write(response.content)
    print(f"Audio downloaded to {filename}")


def get_audio_duration(filename):
    audio = AudioFileClip(filename)
    duration = audio.duration
    audio.close()
    return duration

def get_amount_of_scenes(story):
    prompt = f"You will be given a story. It will be used in a video generator that will divide the story into scenes and then have an image AI generated per scene. You're goal is only to output a number representing the number of scenes you think the story has. The number shouldn't be too big because of the cost of generating AI images. Only output the number and strictly nothing else. Here's the story : {story}"
    while True:
        try:
            number_of_scenes = int(generate_text_response(prompt, model="gpt-3.5-turbo"))
            break
        except ValueError:
            continue
    # noinspection PyUnboundLocalVariable
    return number_of_scenes

def get_unique_filename(base_name, extension):
    counter = 1
    new_name = f"{base_name}{extension}"
    while os.path.exists(new_name):
        new_name = f"{base_name}{counter}{extension}"
        counter += 1
    return new_name

def create_video_with_audio_and_text(image_files, audio_files, durations, scenes):
    clips = []
    for image_file, audio_file, duration, scene_text in zip(image_files, audio_files, durations, scenes):
        image_clip = ImageClip(image_file).set_duration(duration)
        audio_clip = AudioFileClip(audio_file).subclip(0, duration)

        # Create a text clip with transparent background and border
        text_clip = TextClip(scene_text, fontsize=48, color='white', font='Arial-Bold',
                             stroke_color='black', stroke_width=2)
        text_clip = text_clip.set_position(('center', 'bottom')).set_duration(duration)

        # Overlay text on image
        video_clip = CompositeVideoClip([image_clip, text_clip]).set_audio(audio_clip)
        clips.append(video_clip)

    final_video = concatenate_videoclips(clips, method="compose")
    output_filename = get_unique_filename("final_story_video_with_text", ".mp4")

    final_video.write_videofile(output_filename, fps=24)


async def main():
    story = """Pierre's journey through the magical realm led him to meet a kind-hearted fairy named Elara, who revealed that the light was fading because the enchanted crystal at the heart of their world had been stolen. Together, they ventured through enchanted forests and over shimmering rivers, facing challenges that tested Pierre's bravery and wit. Along the way, they made friends with talking animals and learned ancient spells. When they finally reached the dark castle where the crystal was hidden, Pierre used his courage and the power of friendship to outsmart the greedy sorcerer and restore the crystal to its rightful place, bringing light and joy back to the magical realm. As a thank you, Elara gifted Pierre a small, enchanted acorn, promising it would always guide him home."""
    num_of_images = get_amount_of_scenes(story)
    print("Number of Scenes :", num_of_images)
    images, scenes = get_scenes(story, num_of_images)
    image_files = await generate_story_images(images)

    audio_files = []
    durations = []

    # Request TTS for each scene and download audio when ready
    for i, part in enumerate(scenes):
        task_id = generate_tts_audio(part, f"story_part_{i}.mp3")
        while True:
            status_response = check_task_status(task_id)
            if status_response['SynthesisTask']['TaskStatus'] == 'completed':
                output_uri = status_response['SynthesisTask']['OutputUri']
                download_audio_file(output_uri, f"story_part_{i}.mp3")
                break
            await asyncio.sleep(3)  # Wait for a while before checking again

        audio_file = f"story_part_{i}.mp3"
        audio_files.append(audio_file)
        duration = get_audio_duration(audio_file)
        durations.append(duration)

    create_video_with_audio_and_text(image_files, audio_files, durations, scenes)


# Run the async main function
asyncio.run(main())
