import os
import asyncio
import aiohttp
from PIL import Image
from io import BytesIO
from g4f.cookies import set_cookies_dir, read_cookie_files
from g4f.client import Client
from g4f.Provider import OpenaiChat

import g4f.debug

g4f.debug.logging = True

# Set event loop policy for Windows
if os.name == 'nt':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Set cookies directory
cookies_dir = os.path.join(os.path.dirname(__file__), "har_and_cookies")
set_cookies_dir(cookies_dir)
read_cookie_files(cookies_dir)


async def generate_image(prompt):
    client = Client(image_provider=OpenaiChat)

    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
    )
    image_url = response.data[0].url
    print(f"Image URL: {image_url}")
    return image_url


async def download_image(url, filename):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                image_data = await response.read()
                image = Image.open(BytesIO(image_data))
                image = image.convert("RGB")  # Convert to JPG format
                image.save(filename, "JPEG")
                print(f"Image saved to {filename}")
            else:
                print(f"Failed to download image: {response.status}")


def generate_text_response(prompt, model="gpt-4o", log=False):
    client = Client(provider=OpenaiChat)

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
    )
    text_response = response.choices[0].message.content
    if log:
        print(f"Text Response: {text_response}")
    return text_response



