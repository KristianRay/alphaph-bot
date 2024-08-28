import discord
from discord.ext import commands
from discord.ui import Button, View
from PIL import Image
import aiohttp
import io
import os
from dotenv import load_dotenv
from flask import Flask
import threading

# Load environment variables from .env file
load_dotenv()

# Retrieve the environment variable 'BOT_TOKEN'
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Check if the environment variable is available
if BOT_TOKEN is None:
    raise ValueError("No BOT_TOKEN found in environment variables")

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Your frame image path
FRAME_PATH = 'frame.png'
# List of channel IDs where the bot should operate
TARGET_CHANNEL_IDS = [1278232974042595380, 1212324069458845758]  # Replace with your channel IDs

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

@bot.event
async def on_message(message):
    if message.channel.id in TARGET_CHANNEL_IDS and message.content.lower() == '!setup':
        button = Button(label="Get Your PFP", style=discord.ButtonStyle.primary, custom_id="get_pfp_button")
        view = View()
        view.add_item(button)
        await message.channel.send("Click the button below to get your profile picture with a frame!", view=view)

@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.component:
        if interaction.data["custom_id"] == "get_pfp_button":
            user = interaction.user

            # Fetch the user's PFP URL
            pfp_url = user.avatar.url

            async with aiohttp.ClientSession() as session:
                async with session.get(pfp_url) as response:
                    if response.status == 200:
                        content_type = response.headers.get('Content-Type')
                        if 'image' in content_type:
                            pfp_bytes = await response.read()
                        else:
                            await interaction.response.send_message("Unsupported image format. Please try again later.", ephemeral=True)
                            return
                    else:
                        await interaction.response.send_message("Failed to fetch image. Please try again later.", ephemeral=True)
                        return

            try:
                pfp_image = Image.open(io.BytesIO(pfp_bytes)).convert("RGBA")
            except Exception as e:
                await interaction.response.send_message(f"Error processing image: {e}", ephemeral=True)
                return

            frame_image = Image.open(FRAME_PATH).convert("RGBA")
            frame_size = frame_image.size

            frame_ratio = frame_size[0] / frame_size[1]
            pfp_size = (int(frame_size[0] * 0.84), int(frame_size[0] * 0.84 / frame_ratio))
            pfp_image = pfp_image.resize(pfp_size, Image.Resampling.LANCZOS)

            combined_image = Image.new('RGBA', frame_size)
            pfp_position = (
                (frame_size[0] - pfp_size[0]) // 2,
                (frame_size[1] - pfp_size[1]) // 2
            )
            combined_image.paste(pfp_image, pfp_position, pfp_image)
            combined_image.paste(frame_image, (0, 0), frame_image)

            with io.BytesIO() as output:
                combined_image.save(output, format='PNG')
                output.seek(0)

                try:
                    await interaction.response.send_message(
                        file=discord.File(fp=output, filename='pfp_with_frame.png'),
                        ephemeral=True
                    )
                except discord.errors.NotFound as e:
                    print(f"Interaction not found: {e}")
                    # Handle the expired interaction gracefully
                    await interaction.channel.send(
                        "Failed to complete the request. Please try again.",
                        ephemeral=True
                    )

# Flask web server to keep the bot alive
app = Flask(__name__)

@app.route('/')
def home():
    return 'Bot is running!'

def run_flask():
    app.run(host='0.0.0.0', port=5000)

if __name__ == '__main__':
    # Run Flask in a separate thread
    t = threading.Thread(target=run_flask)
    t.start()
    # Start the bot
    bot.run(BOT_TOKEN)
    print(f"BOT_TOKEN: {BOT_TOKEN}")

