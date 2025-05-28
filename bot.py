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
import json

import embeds

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
conf = json.loads(open("config.json", "r").read())

SONG_QUEUES = {}

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
logger = logging.getLogger(__name__)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Online!\n{bot.user} | {bot.user.id}") 


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
    audio_url = first_track["url"]
    title = first_track.get("title", "Untitled")

    guild_id = str(interaction.guild_id)
    if SONG_QUEUES.get(guild_id) is None:
        SONG_QUEUES[guild_id] = deque()

    SONG_QUEUES[guild_id].append((audio_url, title))

    if voice_client.is_playing() or voice_client.is_paused():
        await interaction.followup.send(embed=embeds.generic_embed(
            title=":musical_note: Added to Queue",
            description=f"**{title}** has been added to the queue.",
            color=discord.Color.blue()
        ), ephemeral=True)
    else:
        await interaction.followup.send(embed=embeds.generic_embed(
            title=":musical_note: Now Playing",
            description=f"### {title}",
            color=discord.Color.green()
        ), ephemeral=True)
        await play_next_song(voice_client, guild_id, interaction.channel)


async def play_next_song(voice_client, guild_id, channel):
    if SONG_QUEUES[guild_id]:
        audio_url, title = SONG_QUEUES[guild_id].popleft()

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
        asyncio.create_task(channel.send(embed=embeds.generic_embed(
            title=":musical_note: Now Playing",
            description=f"### {title}",
            color=discord.Color.green()
        )))
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

    queue_list = [f"{idx+1}. {title}" for idx, (_, title) in enumerate(queue)]
    message = "**Current Queue:**\n" + "\n".join(queue_list)
    await interaction.response.send_message(message)

bot.run(TOKEN)