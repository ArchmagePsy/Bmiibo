import os
import random
import re

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD = os.getenv("DISCORD_GUILD")
DAD = os.getenv("DAD")

welcome = [
    "You're welcome",
    "Don't mention it",
    "Not a problem",
    "Always happy to help you",
    "Anything for you",
    "That's great to hear",
    "That's really brightened up my day, thanks"
]

compliment = [
    "Don't tell the others but you're my faveourite!",
    "Damn, you are absolutely killing it today!",
    "Did you do your hair different this morning? It looks great!",
    "I can already tell that you've got today in the bag.",
    "Is it Hot in hear? Oh nah it's just *you*!",
    "Just remember you deserve some you time every now and again. Don't be afraid to spoil yourself!",
    "If you ever feel like the world is crashing down on you, just know I've got your back!"
]

client = discord.Client()
claim_regex = re.compile(r"(claim\s+(\w+))")
claimed = dict()


def claim(user_id, name):
    if user_id in claimed.keys():
        return 2
    elif name in claimed.values():
        return 0
    else:
        claimed[user_id] = name
        return 1


@client.event
async def on_ready():
    guild = discord.utils.get(client.guilds, name=GUILD)
    print(
        f"{client.user} is connected to the following guild:\n"
        f"{guild.name}(id: {guild.id})"
    )


@client.event
async def on_message(message):
    if message.author == client.user:
        return
    elif (strip_message := message.content.strip()).startswith("!judy"):
        if "claim" in strip_message:
            matches = claim_regex.search(strip_message)
            if matches:
                if 1 == (claim_result := claim(message.author.id, matches[2])):
                    await message.channel.send(f"claimed {matches[2]} for {message.author.name}")
                elif 0 == claim_result:
                    await message.channel.send(f"sorry {message.author.name}! {matches[2]} has already been claimed :(")
                elif 2 == claim_result:
                    await message.channel.send(f"sorry {message.author.name}! you've already claimed a name")
            else:
                await message.channel.send(f"sorry {message.author.name}! I'm not sure that's a valid name")
        else:
            await message.channel.send(f"sorry {message.author.name}! I didn't understand that")
    elif (pro_message := message.content.lower().strip()) in ["my son", "my son!"] and message.author.name == DAD:
        response = random.choice(["Father!", "Where's Mother?"])
        await message.channel.send(response)
    elif client.user in message.mentions:
        if "thank" in pro_message:
            response = " ".join([random.choice(welcome), f"{message.author.name}.", random.choice(compliment)])
        elif "what" in pro_message:
            response = """
            I am Adjudicator, the arbiter of all things Bmiibo.
            
            In his spare time Father made a customizeable text-based autobattler that used Q-learning to attempt to learn 
            how to fight. It was Father's intent to be able to play this with his friends (I'm guessing that's you) 
            and since the game was text based he thought what better way to do it than with me, a discord bot!"""
        else:
            response = "How can I help?"
        await message.channel.send(response)


client.run(TOKEN)
