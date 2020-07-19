import os
import io
import uuid
import glob
import json
import time
import sched

import asyncio
import statistics
import random
import subprocess

from discord.ext import commands, tasks
from discord.ext.commands import Bot
from bs4 import BeautifulSoup

import pandas
import plotly
import plotly.figure_factory as ff
import plotly.express as px

import requests
import discord
import discord.utils
import datetime

bot = commands.Bot(command_prefix='huzz')


headers = {
  "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko)" +
    " Chrome/50.0.2661.75 Safari/537.36",
  "X-Requested-With": "XMLHttpRequest"
}

bot_abuse = {

}

clowned = {
    
}


def get_leaderboard(region="all"):
    global headers
    r = requests.get(
        f"https://www.futbin.com/champions/leaderboard/pc/{region}/current",
        headers=headers
    )
    df = pandas.read_html(r.text)[0]
    df["Region"] = region
    return df


def get_leaderboards():
    df = pandas.concat([get_leaderboard("eur"), get_leaderboard("ams")])
    return df.sort_values(["Wins", "SKILL RATING"], ascending=False)


def get_monthly():
    global headers
    r = requests.get(
        f"https://www.futbin.com/champions/leaderboard/pc/all/monthly",
        headers=headers
    )
    return pandas.read_html(r.text)[0]
    

def rank(username):
    leaderboard = get_leaderboard()
    df = leaderboard[leaderboard["Gamer tag"].str.lower()  == username.lower()]
    embed = discord.Embed(
        title=f"{username}'s Rank",
        description=f"Shows current rank for {username} in WL.",
        color=0xff2600
    )

    if df.shape[0] == 0:
        embed.add_field(name="Git Gud", value="Not in t100. Trash.", inline=True)
        embed.set_image(url="https://media.giphy.com/media/26FPy3QZQqGtDcrja/giphy.gif")
    else:
        embed.add_field(name="Ranking", value=str(df["Ranking"].iloc[0]), inline=True)
        embed.add_field(name="Skill Rating", value=str(df["SKILL RATING"].iloc[0]), inline=True)
    
    embed.set_footer(
        text="Source: https://www.futbin.com/champions/leaderboard/pc/all/current"
    )

    return embed


def generate_table(df):
    df["SR"] = df["SKILL RATING"]
    df["Origin"] = df["Gamer tag"]
    
    path = str(uuid.uuid4()) + ".png"
    table = ff.create_table(df[["Ranking", "Origin", "Wins", "SR"]])
    plotly.io.write_image(table, path)

    return path


def cutoff():
    leaderboard = get_leaderboard()
    min_wins = leaderboard["Wins"].tail(1).iloc[0]
    min_sr = leaderboard["SKILL RATING"].tail(1).iloc[0]

    embed = discord.Embed(
        title="Top 100 Cutoff",
        description="Shows current number of minimum wins and skill rating needed for Top 100",
        color=0xff2600
    )
    embed.add_field(name="Minimum Wins", value=str(min_wins), inline=True)
    embed.add_field(name="Minimum SR", value=str(min_sr), inline=True)
    embed.set_footer(
        text="Source: https://www.futbin.com/champions/leaderboard/pc/all/current"
    )
    
    return embed


def cheaters():
    global memes

    leaderboard = get_leaderboard()

    leaderboard["skill_per_win"] = leaderboard["SKILL RATING"] / leaderboard["Wins"]
    df = leaderboard[leaderboard["skill_per_win"] <= 75]

    embed = discord.Embed(
        title="Potential Cheaters",
        description="Shows current number players with less than 75 skill rating per win",
        color=0xff2600
    )

    if df.shape[0] >= 1:
        origins = "\n".join(list(df["Gamer tag"]))
        wins = "\n".join([str(x) for x in df["Wins"]])
        skill_ratings = "\n".join([str(x) for x in df["SKILL RATING"]])

        embed.add_field(name="Origin", value=origins, inline=True)
        embed.add_field(name="Wins", value=wins, inline=True)
        embed.add_field(name="SR", value=skill_ratings, inline=True)

    embed.set_footer(
        text="Please keep in mind this just an educated guess. Source is Futbin."
    )

    return embed


def t10():
    return generate_table(get_leaderboard().head(10))


def t100():
    leaderboard = get_leaderboard()
    paths = []
    for page in range(2):
        df = leaderboard[page * 50 : page * 50 + 50]
        paths.append(generate_table(df))
    return paths


def get_player_futbin_price(name, rating):
    global headers
    
    res = requests.get("https://www.futbin.com/search?year=20&extra=1&v=1&term=" + name, headers=headers)
    player_entry = None
    for entry in res.json():
        if int(entry["rating"]) == int(rating):
            player_entry = entry
            break
    
    if player_entry: return get_player_prices_by_id(player_entry["id"])

def get_player_prices_by_id(id):
    global headers
    
    res = requests.get("https://www.futbin.com/20/player/" + id, headers=headers)
    soup = BeautifulSoup(res.content, 'html.parser')
    price_id = soup.findAll("div", {"id": "page-info"})[0]["data-player-resource"]
    
    res2 = requests.get("https://www.futbin.com/20/playerPrices?player=" + price_id, headers=headers).json()
    price = "0"
    for time in res2:
        price = res2[time]["prices"]["pc"]["LCPrice"]
        
    return float(price.replace(",", ""))
    
def update_reward_prices():
    global headers
    
    rewards = pandas.read_csv("rewards.csv")
    rows = rewards.to_dict("records")
    for row in rows:
        try:
            row["Price"] = get_player_futbin_price(row["Name"], row["Rating"])
        except Exception as e:
            print(e)
    
    rewards = pandas.DataFrame(rows)
    rewards.to_csv("rewards.csv")


def calculate_t100_earnings():
    rewards = pandas.read_csv("rewards.csv")
    min_pack = sum(rewards.dropna().sort_values("Price", ascending=True)["Price"][:11])
    max_pack = sum(rewards.dropna().sort_values("Price", ascending=False)["Price"][:11])
    
    embed = discord.Embed(
        title="T100 Rewards",
        description="Shows t100 rewards value for this week",
        color=0xff2600
    )
    embed.set_image(url="https://media.discordapp.net/attachments/685870223684927523/724789359252996196/clutch.jpg")

    embed.add_field(name="Min Value Pack", value=min_pack, inline=True)
    embed.add_field(name="Max Value Pack", value=max_pack, inline=True)

    return embed

def calculate_elite_earnings():
    rewards = pandas.read_csv("rewards.csv")
    min_pack = sum(rewards.dropna().sort_values("Price", ascending=True)["Price"][:3])
    max_pack = sum(rewards.dropna().sort_values("Price", ascending=False)["Price"][:3])
    
    embed = discord.Embed(
        title="Elite Rewards",
        description="Shows elite rewards value for this week",
        color=0xff2600
    )
    embed.set_image(url="https://media.discordapp.net/attachments/685870223684927523/724789660563275886/spartodia.png")

    embed.add_field(name="Min Value Pack", value=min_pack, inline=True)
    embed.add_field(name="Max Value Pack", value=max_pack, inline=True)

    return embed


def help():
    utility_commands = [
        ("!t10", "posts top 10 usernames, wins, skill rating"),
        ("!t100", "posts top 100 usernames, wins, skill rating"),
        ("!cutoff", "posts minimum wins and SR needed for t100"),
        ("!cheaters", "posts number of likely cheaters to be removed"),
        ("!myrank origin", "posts your rank on t100 leaderboards. It is not case sensitive"),
        ("!updaterewards", "updates the prices for weekend league rewards. Restricted to Mongo"),
        ("!rewards", "posts current rewards expected earnings"),
    ]

    meme_commands = [
        ("!panic", "posts sparty meltdown to prime moments gullit"),
        ("!elon", "posts sparty flexing going 15-0"),
        ("!pantel", "posts screenshot of pantel smashing sparty"),
        ("!cucktel", "posts pantel getting cucked meme"),
        ("!whatif", "posts what if pantel changes password meme"),
        ("!nemesis", "posts nemesis goal"),
        ("!time", "posts what time it is"),
        ("!kill", "posts kill VVD trait"),
        ("!forbidden", "posts forbidden elon"),
        ("!sayan", "posts sayan sparty"),
        ("!retired", "posts sparty retirement"),
        ("!saviour", "the saviour of fut pc"),
        ("!n2", "performance of n2 player in the world"),

        ("!dodge", "posts random Michiel dodging gif"),
        
        ("!cum", "posts i am gonna cum"),
        ("!win", "posts this is how i win"),
        ("!disagree", "posts i disagree meme"),

        ("!grapefruit", "posts Zzonkey pasta about grapefruit"),
        ("!shitters", "posts shitters getting rewarded meme"),
    ]

    utility_embed = discord.Embed(
        title="Utility Commands",
        description="List of useful tools",
        color=0xff2600
    )
    memes_embed = discord.Embed(
        title="Meme Commands",
        description="Memes and other dumb shit",
        color=0xff2600
    )

    utility_embed.add_field(name="Command", value="\n".join([a[0] for a in utility_commands]), inline=True)
    utility_embed.add_field(name="Description", value="\n".join([a[1] for a in utility_commands]), inline=True)
    
    memes_embed.add_field(name="Command", value="\n".join([a[0] for a in meme_commands]), inline=True)
    memes_embed.add_field(name="Description", value="\n".join([a[1] for a in meme_commands]), inline=True)

    return [utility_embed, memes_embed]


@bot.event
async def on_ready():
    print ("Bot Ready")


@bot.event
async def on_raw_reaction_add(payload):
    if payload.emoji.name == "huzaifa":
        channel = bot.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        user_roles = [r.name.lower() for r in message.author.roles]
        for reaction in message.reactions:
            if "huzaifa" in str(reaction) and reaction.count == 6:
                five_mins_ago = datetime.datetime.now() - datetime.timedelta(minutes=5)
                if bot_abuse.get(message.author.id, five_mins_ago) + datetime.timedelta(minutes=5) <= datetime.datetime.now():
                    await channel.send("<@{}> you're fucking retarded dude.".format(str(message.author.id)))
                    bot_abuse[message.author.id] = datetime.datetime.now()

                if "Clowns" not in user_roles:
                    role = discord.utils.get(message.guild.roles, id=733677756784836719)
                    await message.author.add_roles(role)

                    json.dump(
                        {
                            "type": "remove_role",
                            "id": message.author.id,
                            "guild": message.guild.id, 
                            "time": datetime.datetime.timestamp(datetime.datetime.now() + datetime.timedelta(days=1)),
                            "channel": payload.channel_id
                        },
                        open("tasks/{}.json".format(str(uuid.uuid4())), "w")
                    )

                    await channel.send("<@&733677756784836719> please welcome <@{}> as your new member.".format(str(message.author.id)))
            elif "huzaifa" in str(reaction) and reaction.count == 15 and "Clowns" in user_roles:
                role = discord.utils.get(message.guild.roles, id=734476386051424309)
                await message.author.add_roles(role)

                await channel.send("<@{}> You have been permanently designated as the CEO of Clowns".format(str(message.author.id)))


@bot.event
async def on_message(message):

    memes = {
        "!pantel": [
            dict(content="https://media.discordapp.net/attachments/461638666578558988/694933953194491944/846.png"),
        ],
        
        "!dodge": [
            dict(content="https://media.discordapp.net/attachments/389698839403298816/699953878686498897/michiel_dance.gif"),
            dict(content="https://images-ext-1.discordapp.net/external/prretMcK3PCqTAm8aHSBWkw4lMYJOgi1I3KMtrGHMQE/https/media.discordapp.net/attachments/389698839403298816/700323597951959040/run_michiel_run.gif"),
            dict(content="https://images-ext-2.discordapp.net/external/DFwWduZ8cPdUEqP0wNytc6aWLa-yuiSGPkpszNhhd90/https/media.discordapp.net/attachments/389698839403298816/699983948985401344/michiel_top100.gif"),
            dict(content="https://images-ext-1.discordapp.net/external/fzKu0RlL1oCYXmZQhTq9nIOycgDNOL3GAEzMwzdsSdM/https/media.discordapp.net/attachments/389698839403298816/699698294481354752/Michiel.gif"),
        ],
        
        "!cum": [
            dict(content="https://cdn.discordapp.com/attachments/461638666578558988/679347655159185430/1580513902999.png"),
        ],
        "!win": [
            dict(content="https://cdn.discordapp.com/attachments/461638666578558988/679346955381506080/this.jpg"),
        ],
        "!disagree": [
            dict(content="https://media.discordapp.net/attachments/461638666578558988/679352877252345856/i_dissagree.jpg"),
        ],

        "!grapefruit": [
            dict(
                content="""Whenever I self-pleasure, I do a TONNE of foreplay. I write down "pre-cum" on a sheet of paper, and stick the pen in my rectum. I massage my foreskin and put a grapefruit with the centre hollowed out over my WILLY until I start leaking. Then I begin the full grapefruiting, stopping when I'm just on the edge. I get on the table, and try to cross out the "pre" on the paper with the pen still inside me. The pressure of it being pressed against my prostrate usually causes me to ejaculate all over the note. It reminds myself that I'm blessed to be a MAJESTIC EU t100 gamer and not an NA DOG.""",
                tts=True
            )
        ],

        "!cucktel": [dict(file=discord.File("memes/clutch.jpg"))],
        "!shitter": [dict(file=discord.File("memes/shitters.png"))],
        "!mongo": [dict(file=discord.File("memes/mongo.png"))],
        "!whatif": [dict(file=discord.File("memes/whatif.png"))],
        "!nemesis": [dict(file=discord.File("memes/nemesis.png"))],
        "!panic": [dict(file=discord.File("memes/panic.png"))],
        "!time": [dict(file=discord.File("memes/time.png"))],
        "!kill": [dict(file=discord.File("memes/okocha.png"))],
        "!elon": [dict(file=discord.File("memes/elon.jpg"))],
        "!huzz": [dict(file=discord.File("memes/huzz.png"))],
        "!forbidden": [
            dict(
                content="Pantel enjoys his shit flaked weetabix + coffee for breakfast, logs on to find his watch list cleared by sparty and his trade pile full of random 'extinct' bronzes listed for max price that will never sell. He then thinks at least the 200m coin time with PIM fullbacks and GK will unlock spartlingz full potential, little does he know that Elon Musk had recently bought Florida power company, the final piece of Elon, the forbidden one",
                tts=True
            ),
            dict(file=discord.File("memes/spartodia.png")),
        ],
        "!sayan": [dict(file=discord.File("memes/sayan_sparty.png"))],
        "!retired": [dict(file=discord.File("memes/nofifa.png"))],
        "!saviour": [dict(file=discord.File("memes/memechiel.jpg"))],
        "!mywl": [dict(file=discord.File("memes/elonclutch.png"))],
        "!n2": [dict(file=discord.File("memes/bestInNA.png"))],
        "!weezy": [dict(file=discord.File("memes/weezytoxic.png"))],
        "!millions": [dict(file=discord.File("memes/millions.png"))],
        ":haha:": [dict(file=discord.File("memes/haha.png"))],
        "<@&733677756784836719>": [dict(content="Clowns your attention is requested. Clown business.")]
    }

    roles = [r.name.lower() for r in message.author.roles]

    if "Bots" in roles:
        return

    if "autohuzz" in roles:
        try: await message.add_reaction(bot.get_emoji(733758438516981803))
        except: pass

    if "auto-delete-images" in roles:
        if message.attachments:
            await message.delete()

    content = message.content
    for key in memes.keys():
        if key in content:
            for meme in memes[key]: await message.channel.send(**meme)

    if content.startswith("!futbot"):
        for embed in help(): await message.channel.send(embed=embed)
    elif content.startswith("!updaterewards"):
        if message.author.id in [375097224021016587, 113388728692531200]:
            message.channel.send("This command is currently only restricted to Mongo and Shammy. It makes thousands of requests to Futbin and could get the server that hosts the bot black listed if spammed. You can still use !rewards command, you just cant update latest prices from futbin.")
        else:
            update_reward_prices()
    elif content.startswith("!rewards"):
        await message.channel.send(embed=calculate_t100_earnings())
        await message.channel.send(embed=calculate_elite_earnings())
        await message.channel.send(file=discord.File("rewards.csv"))
    elif content.startswith("!t100"):
        paths = t100()
        for f in paths:
            await message.channel.send(file=discord.File(f))
            os.remove(f)
    elif content.startswith("!t10"):
        path = t10()
        await message.channel.send(file=discord.File(path))
        os.remove(path)
    elif content.startswith("!cutoff"): await message.channel.send(embed=cutoff())
    elif content.startswith("!cheaters"): await message.channel.send(embed=cheaters())
    elif content.startswith("!myrank"):
        username = content.split(" ")[1].strip()
        await message.channel.send(embed=rank(username))

@tasks.loop(seconds=1)
async def run_tasks():
    for task_file in glob.glob("tasks/*.json"):
        task = json.load(open(task_file))
        guild = bot.get_guild(int(task.get("guild", "0")))
        if task.get("type") == "remove_role" and datetime.datetime.fromtimestamp(task.get("time")) < datetime.datetime.now():
            try:
                user = discord.utils.get(guild.members, id=int(task.get("id", "0")))
                role = discord.utils.get(guild.roles, id=733677756784836719)
                await user.remove_roles(role)

                channel = bot.get_channel(int(task.get("channel", "0")))
                await channel.send("<@{}> your clown days have come to an end.".format(user.id))

                os.remove(task_file)
            except Exception as e:
                print(e)


@run_tasks.before_loop
async def run_tasks_before():
    await bot.wait_until_ready()

run_tasks.start()
bot.run(os.environ.get("DISCORD_TOKEN"))
