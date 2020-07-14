import os
import io
import uuid

import asyncio
import statistics
import random
import subprocess

from discord.ext import commands
from discord.ext.commands import Bot
from bs4 import BeautifulSoup

import sys
import pandas
import plotly
import plotly.figure_factory as ff
import plotly.express as px

import requests
import discord
import datetime

bot = commands.Bot(command_prefix='huzz')

@bot.event
async def on_ready():
    print ("Bot Ready")


@bot.event
async def on_message(message):
    roles = [r.name.lower() for r in message.author.roles]
    if "autohuzz" in roles:
        await message.add_reaction(bot.get_emoji(711327605189771294))
bot.run(sys.argv[-1])
