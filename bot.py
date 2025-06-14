# Importing libraries and modules
import os
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import yt_dlp
from collections import deque
import asyncio
import logging
import datetime
import json

import embeds

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
conf = json.loads(open("config.json", "r").read())

SONG_QUEUES = {}
CURRENT_SONG = {}

async def search_ytdlp_async(query, ydl_opts):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: _extract(query, ydl_opts))

def _extract(query, ydl_opts):
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            return ydl.extract_info(query, download=False)
        except yt_dlp.utils.DownloadError as e:
            if "Requested format is not available" in str(e):
                raise ValueError("This video might be DRM-protected or region-locked.")
            raise


intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
logger = logging.getLogger("discord")

is_ready = False

@bot.event
async def on_ready():
    global is_ready

    await bot.tree.sync()
    logger.info(f"Logged in as {bot.user} (ID: {bot.user.id})")
    logger.info("Bot is ready!")
    is_ready = True

@bot.tree.command(name="skip", description="Skips the current playing song")
async def skip(interaction: discord.Interaction):
    if interaction.guild.voice_client and (interaction.guild.voice_client.is_playing() or interaction.guild.voice_client.is_paused()):
        interaction.guild.voice_client.stop()
        await interaction.response.send_message(embed=embeds.generic_embed(
            title=":white_check_mark: Skipped",
            description="Skipped the current song.",
            color=discord.Color.green()
        ), ephemeral=True) 
    else:
        await interaction.response.send_message(embed=embeds.generic_embed(
            title=":x: Error",
            description="No song is currently playing.",
            color=discord.Color.red()
        ), ephemeral=True)


@bot.tree.command(name="pause", description="Pause the currently playing song.")
async def pause(interaction: discord.Interaction):
    
    voice_client = interaction.guild.voice_client

    if voice_client is None:
        return await interaction.response.send_message(embed=embeds.generic_embed(
            title=":x: Error",
            description="I'm not connected to any voice channel.",
            color=discord.Color.red()
        ), ephemeral=True)

    if not voice_client.is_playing():
        return await interaction.response.send_message(embed=embeds.generic_embed(
            title=":x: Error",
            description="I'm not currently playing any song.",
            color=discord.Color.red()
        ), ephemeral=True)
    
    voice_client.pause()
    await interaction.response.send_message(embed=embeds.generic_embed(
        title=":pause_button: Paused",
        description="Playback has been paused.",
        color=discord.Color.yellow()
    ), ephemeral=True)


@bot.tree.command(name="resume", description="Resume the currently paused song.")
async def resume(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client

    if voice_client is None:
        return await interaction.response.send_message(embed=embeds.generic_embed(
            title=":x: Error",
            description="I'm not connected to any voice channel.",
            color=discord.Color.red()
        ), ephemeral=True)

    if not voice_client.is_paused():
        return await interaction.response.send_message(embed=embeds.generic_embed(
            title=":x: Error",
            description="I’m not paused right now.",
            color=discord.Color.red()
        ), ephemeral=True)
    
    voice_client.resume()
    await interaction.response.send_message(embed=embeds.generic_embed(
        title=":arrow_forward: Resumed",
        description="Playback has been resumed.",
        color=discord.Color.green()
    ), ephemeral=True)


@bot.tree.command(name="stop", description="Stop playback and clear the queue.")
async def stop(interaction: discord.Interaction):    
    voice_client = interaction.guild.voice_client

    if not voice_client or not voice_client.is_connected():
        return await interaction.response.send_message(embed=embeds.generic_embed(
            title=":x: Error",
            description="I'm not connected to any voice channel.",
            color=discord.Color.red()
        ), ephemeral=True)

    guild_id_str = str(interaction.guild_id)
    if guild_id_str in SONG_QUEUES:
        SONG_QUEUES[guild_id_str].clear()

    if voice_client.is_playing() or voice_client.is_paused():
        voice_client.stop()

    await voice_client.disconnect()

    await interaction.response.send_message(embed=embeds.generic_embed(
        title=":stop_button: Stopped",
        description="Playback has been stopped and the queue cleared.",
        color=discord.Color.red()
    ), ephemeral=True)


@bot.tree.command(name="play", description="Play a song or add it to the queue.")
@app_commands.describe(song_query="Search query")
async def play(interaction: discord.Interaction, song_query: str):
    if not interaction.response.is_done():
        await interaction.response.defer(ephemeral=True)

    if not interaction.user.voice:
        await interaction.followup.send(embed=embeds.generic_embed(
            title=":x: Error",
            description="You must be in a voice channel to use this command.",
            color=discord.Color.red()
        ), ephemeral=True)
        return
    
    voice_channel = interaction.user.voice.channel

    if voice_channel is None:
        await interaction.followup.send(embed=embeds.generic_embed(
            title=":x: Error",
            description="You must be in a voice channel to use this command.",
            color=discord.Color.red()
        ), ephemeral=True)
        return

    voice_client = interaction.guild.voice_client

    if voice_client is None:
        voice_client = await voice_channel.connect()
    elif voice_channel != voice_client.channel:
        await voice_client.move_to(voice_channel)

    ydl_options = {
        "format": "bestaudio[abr<=96]/bestaudio/best",
        "noplaylist": True,
        "youtube_include_dash_manifest": False,
        "youtube_include_hls_manifest": False,
    }

    query = "ytsearch1: " + song_query
    results = await search_ytdlp_async(query, ydl_options)
    tracks = results.get("entries", [])

    if tracks is None:
        await interaction.followup.send(embed=embeds.generic_embed(
            title=":x: Error",
            description="No results found for your query.",
            color=discord.Color.red()
        ), ephemeral=True)
        return

    first_track = tracks[0]
    # Remove unnecessary fields
    for key in ['formats', 'thumbnails', 'automatic_captions', 'heatmap']:
        first_track.pop(key, None)

    guild_id = str(interaction.guild_id)
    if SONG_QUEUES.get(guild_id) is None:
        SONG_QUEUES[guild_id] = deque()

    SONG_QUEUES[guild_id].append(first_track)

    title = first_track.get("title", "Untitled")
    if voice_client.is_playing() or voice_client.is_paused():
        await interaction.followup.send(embed=embeds.song_embed(
            title=f":musical_note: {title}",
            description="**Added to queue.**",
            color=discord.Color.blue(),
            thumbnail_url=first_track.get("thumbnail")
        ), ephemeral=True)
    else:
        await interaction.followup.send(embed=embeds.song_embed(
            title=f":musical_note: {title}",
            description=f"**Now playing.**\nDuration: {datetime.timedelta(seconds=first_track.get('duration', 0))}",
            color=discord.Color.green(),
            thumbnail_url=first_track.get("thumbnail")
        ), ephemeral=True)
        await play_next_song(voice_client, guild_id, interaction.channel)


async def play_next_song(voice_client, guild_id, channel):
    if SONG_QUEUES[guild_id]:
        track = SONG_QUEUES[guild_id].popleft()
        with open("test.json", "w", encoding="utf-8") as f: # DEBUG
            json.dump(track, f, indent=4, ensure_ascii=False)

        audio_url = track["url"]
        title = track.get("title", "Untitled")

        ffmpeg_options = {
            "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
            "options": "-vn -c:a libopus -b:a 96k",
        }

        source = discord.FFmpegOpusAudio(audio_url, **ffmpeg_options, executable="bin\\ffmpeg\\ffmpeg.exe")

        def after_play(error):
            if error:
                print(f"Error playing {title}: {error}")
            asyncio.run_coroutine_threadsafe(play_next_song(voice_client, guild_id, channel), bot.loop)

        voice_client.play(source, after=after_play)
        asyncio.create_task(bot.change_presence(activity=discord.Activity(name=f"Playing: {title}", type=discord.ActivityType.listening)))
        CURRENT_SONG[guild_id] = (audio_url, title, track)
    else:
        await voice_client.disconnect()
        SONG_QUEUES[guild_id] = deque()


@bot.tree.command(name="queue", description="Show the current song queue.")
async def queue(interaction: discord.Interaction):
    guild_id = str(interaction.guild_id)
    queue = SONG_QUEUES.get(guild_id, deque())
    if not queue:
        await interaction.response.send_message("The queue is empty.")
        return

    queue_list = [f"{idx+1}. {track.get('title', 'Untitled')}" for idx, track in enumerate(queue)]
    message = "**Current Queue:**\n" + "\n".join(queue_list)
    await interaction.response.send_message(message)
    
# WIP
# @bot.tree.command(name="details", description="Shows raw details of the current song.")
# async def details(interaction: discord.Interaction):
#     voice_client = interaction.guild.voice_client
    
#     if voice_client is None:
#         return await interaction.response.send_message(embed=embeds.generic_embed(
#             title=":x: Error",
#             description="I'm not connected to any voice channel.",
#             color=discord.Color.red()
#         ), ephemeral=True)
#     guild_id = str(interaction.guild_id)
#     if guild_id not in SONG_QUEUES or not SONG_QUEUES[guild_id]:
#         return await interaction.response.send_message(embed=embeds.generic_embed(
#             title=":x: Error",
#             description="There are no songs in the queue.",
#             color=discord.Color.red()
#         ), ephemeral=True)
#     current_song = SONG_QUEUES[guild_id][0]
#     if not current_song:
#         return await interaction.response.send_message(embed=embeds.generic_embed(
#             title=":x: Error",
#             description="There is no song currently playing.",
#             color=discord.Color.red()
#         ), ephemeral=True)
#     _, title, details = current_song
#     details_str = json.dumps(details, indent=4, ensure_ascii=False)
#     embed = discord.Embed(title=f"Details for: {title}", description=f"```{details_str}```", color=discord.Color.blue())
#     await interaction.response.send_message(embed=embed, ephemeral=True)

# GUI Utils
async def skip_song(guild_id: int):
    voice_client = discord.utils.find(lambda vc: vc.guild.id == guild_id, bot.voice_clients)
    if voice_client and (voice_client.is_playing() or voice_client.is_paused()):
        voice_client.stop()
        
async def pause_song(guild_id: int):
    voice_client = discord.utils.find(lambda vc: vc.guild.id == guild_id, bot.voice_clients)
    if voice_client and voice_client.is_playing():
        voice_client.pause()
        
async def resume_song(guild_id: int):
    voice_client = discord.utils.find(lambda vc: vc.guild.id == guild_id, bot.voice_clients)
    if voice_client and voice_client.is_paused():
        voice_client.resume()
        
async def song_status(guild_id: int):
    voice_client = discord.utils.find(lambda vc: vc.guild.id == guild_id, bot.voice_clients)
    if voice_client:
        if voice_client.is_playing():
            return "Playing"
        elif voice_client.is_paused():
            return "Paused"
    return "Stopped"

# Run the bot
async def run_bot(loop):
    asyncio.set_event_loop(loop)
    await bot.start(TOKEN)
    