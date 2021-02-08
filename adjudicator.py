import os
import random

import discord
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
    elif message.author.name == DAD and message.content.lower().strip() in ["my son", "my son!"]:
        response = random.choice(["Father!", "Where's Mother?"])
        await message.channel.send(response)
    elif client.user in message.mentions and "thank" in message.content.lower().strip():
        response = " ".join([random.choice(welcome), f"{message.author.name}.", random.choice(compliment)])
        await message.channel.send(response)


client.run(TOKEN)
