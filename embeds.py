import json
import discord
from discord.ext import commands

config = json.loads(open("config.json", "r").read())

def generic_embed(title=None, description=None, color=discord.Color.blurple(), footer=None):
    embed = discord.Embed(title=title, description=description, color=color)
    embed.set_footer(text=footer and footer or config['default_footer'])
    return embed

def song_embed(title=None, description=None, thumbnail_url=None, color=discord.Color.blurple(), footer=None, url=None):
    embed = discord.Embed(title=title, description=description, color=color)
    
    if thumbnail_url: embed.set_thumbnail(url=thumbnail_url)
    if url: embed.url = url
    embed.set_footer(text=footer and footer or config['default_footer'])
    
    return embed
        