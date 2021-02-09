import json
import os
import pickle
import random
import re

import discord
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD = os.getenv("DISCORD_GUILD")
DAD = int(os.getenv("DAD"))
DIR = os.getenv("BMIIBO_DIR")

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
    "Damn, you are absolutely *killing* it today!",
    "Did you do your hair different this morning? It looks great!",
    "I can already tell that you've got today in the bag.",
    "Is it hot in hear? Oh nah it's just *you*!",
    "Just remember you deserve some you time every now and again. Don't be afraid to spoil yourself!",
    "If you ever feel like the world is crashing down on you, just know I've got your back!"
]

client = discord.Client()
prefix = "!"
claim_regex = re.compile(r"claim\s+(\w+)")
edit_regex = re.compile(r"edit\s+(attack|ability|ultimate)(\[\d+])?:(\w+)=(number|string):(\w+)")
save_regex = re.compile(r"save\s+(attack|ability|ultimate|all)")
reset_regex = re.compile(r"reset\s+(attack|ability|ultimate|all)")
view_regex = re.compile(r"view\s+(attack|ability|ultimate|all)")

if os.path.exists("claims"):
    with open("claims", "rb") as file:
        claimed = pickle.load(file)
else:
    claimed = dict()
edits = dict()
if os.path.exists("training.json"):
    with open("training.json", "r") as file:
        training = json.load(file)
else:
    training = []


def claim(user_id, name):
    if user_id in claimed.keys():
        return 2
    elif name in claimed.values():
        return 0
    else:
        claimed[user_id] = name
        with open("claims", "wb") as claims_file:
            pickle.dump(claimed, claims_file)
        return 1


def edit_group(action_data, index, key, value_type, value):
    if index >= len(action_data):
        action_data.append({key: value if "string" == value_type else int(value)})
        return action_data
    else:
        action_data[index][key] = value if "string" == value_type else int(value)
        return action_data


def edit(user_id, action, index, key, value_type, value):
    if user_id in claimed.keys():
        bmiibo_name = claimed[user_id]
    else:
        return 1
    action_key = f"{bmiibo_name}_{action}"

    if action_key not in edits.keys():
        if os.path.exists(file_name := f"{DIR}{action_key}.json"):
            with open(file_name, "r") as action_file:
                edits[action_key] = json.load(action_file)
        else:
            edits[action_key] = list() if index is not None else dict()

    if type(action_data := edits[action_key]) is list:
        if index:
            return edit_group(action_data, index, key, value_type, value)
        else:
            return 0
    else:
        if index:
            edits[action_key] = [edits[action_key]]
            action_data = edits[action_key]
            return edit_group(action_data, index, key, value_type, value)
        else:
            action_data[key] = value if "string" == value_type else int(value)
            return action_data


def reset(user_id, action):
    if user_id in claimed.keys():
        if "all" == action:
            for action in ["attack", "ability", "ultimate"]:
                edits[f"{claimed[user_id]}_{action}"] = {}
            return 2
        edits[f"{claimed[user_id]}_{action}"] = {}
        return 2
    else:
        return 1


def save(user_id, action):
    if user_id in claimed.keys():
        if "all" == action:
            for action in ["attack", "ability", "ultimate"]:
                if (action_name := f"{claimed[user_id]}_{action}") in edits.keys():
                    with open(f"{DIR}{action_name}.json", "w") as action_file:
                        json.dump(edits[action_name], action_file)
            return 2
        elif (action_name := f"{claimed[user_id]}_{action}") in edits.keys():
            with open(f"{DIR}{action_name}.json", "w") as action_file:
                json.dump(edits[action_name], action_file)
            return 2
        return 0
    else:
        return 1


def view_action(results, user_id, action):
    if (action_name := f"{claimed[user_id]}_{action}") in edits.keys():
        results.append(("editing", edits[action_name]))
    if os.path.exists(file_name := f"{DIR}{action_name}.json"):
        with open(file_name, "r") as action_file:
            results.append(("saved", action_file.read()))


def view(user_id, action):
    if user_id in claimed.keys():
        results = []
        if "all" == action:
            for action in ["attack", "ability", "ultimate"]:
                view_action(results, user_id, action)
        else:
            view_action(results, user_id, action)
        return results
    else:
        return 1


def toggle_train(user_id):
    if user_id in claimed.keys():
        if (bmiibo_name := claimed[user_id]) not in training:
            training.append(bmiibo_name)
            return 2
        else:
            training.remove(bmiibo_name)
            return 1
    else:
        return 0


def finish():
    with open("training.json", "w") as training_file:
        json.dump(training, training_file)


def is_dm(channel):
    return isinstance(channel, discord.DMChannel)


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
    elif (strip_message := message.content.strip()).startswith(f"{prefix}judy"):
        if "claim" in strip_message:
            matches = claim_regex.search(strip_message)
            if matches:
                if 1 == (claim_result := claim(message.author.id, matches[1])):
                    await message.channel.send(f"claimed `{matches[1]}` for {message.author.name}")
                elif 0 == claim_result:
                    await message.channel.send(f"sorry {message.author.name}! `{matches[1]}` has already been claimed :(")
                elif 2 == claim_result:
                    await message.channel.send(f"sorry {message.author.name}! you've already claimed a name")
            else:
                await message.channel.send(f"sorry {message.author.name}! I'm not sure that's a valid name")
        elif "edit" in strip_message:
            if is_dm(message.channel):
                matches = edit_regex.search(strip_message)
                if matches:
                    if 0 == (edit_result := edit(message.author.id, matches[1], matches[2], matches[3], matches[4], matches[5])):
                        await message.channel.send(
                            f"sorry {message.author.name}! this is an action group so you need an index e.g `{matches[1]}[0]`")
                    elif 1 == edit_result:
                        await message.channel.send(
                            f"sorry {message.author.name}! you need to claim a name for your Bmiibo")
                    else:
                        await message.channel.send(f"`{matches[1]}: {edit_result}`")
                else:
                    await message.channel.send(f"sorry {message.author.name}! I didn't understand that")
            else:
                await message.author.send("what would you like to edit?")
        elif "save" in strip_message:
            if is_dm(message.channel):
                matches = save_regex.search(strip_message)
                if matches:
                    if 0 == (save_result := save(message.author.id, matches[1])):
                        await message.channel.send(f"sorry {message.author.name}! I'm not sure what went wrong there :(")
                    elif 1 == save_result:
                        await message.channel.send(
                            f"sorry {message.author.name}! you need to claim a name for your Bmiibo")
                    elif 2 == save_result:
                        await message.channel.send(f"`{matches[1]}` saved!")
                else:
                    await message.channel.send(f"sorry {message.author.name}! I didn't understand that")
        elif "view" in strip_message:
            if is_dm(message.channel):
                matches = view_regex.search(strip_message)
                if matches:
                    if 1 == (view_result := view(message.author.id, matches[1])):
                        await message.channel.send(
                            f"sorry {message.author.name}! you need to claim a name for your Bmiibo")
                    elif type(view_result) is list:
                        response = "\n".join(map(str, view_result))
                        if "" == response:
                            response = f"sorry {message.author.name}! nothing to view"
                        await message.channel.send(response)
                else:
                    await message.channel.send(f"sorry {message.author.name}! I didn't understand that")
        elif "train" in strip_message:
            if 2 == (train_result := toggle_train(user_id := message.author.id)):
                await message.channel.send(
                    f"{message.author.name}'s Bmiibo: `{claimed[user_id]}` has been marked for training!")
            elif 1 == train_result:
                await message.channel.send(
                    f"{message.author.name}'s Bmiibo: `{claimed[user_id]}` has been un-marked for training!")
            else:
                await message.channel.send(f"sorry {message.author.name}! you need to claim a name for your Bmiibo")
        elif "reset" in strip_message:
            if is_dm(message.channel):
                matches = reset_regex.search(strip_message)
                if matches:
                    if 1 == (reset_result := reset(message.author.id, matches[1])):
                        await message.channel.send(
                            f"sorry {message.author.name}! you need to claim a name for your Bmiibo")
                    elif 2 == reset_result:
                        await message.channel.send(f"`{matches[1]}` reset!")
                else:
                    await message.channel.send(f"sorry {message.author.name}! I didn't understand that")
        else:
            await message.channel.send(f"sorry {message.author.name}! I didn't understand that")
    elif (pro_message := message.content.lower().strip()) in ["my son", "my son!"] and message.author.id == DAD:
        response = random.choice(["Father!", "Where's Mother?"])
        await message.channel.send(response)
    elif "good night" in pro_message and client.user in message.mentions and message.author.id == DAD:
        finish()
        await message.channel.send("""
        Sorry to anyone who was working on their Bmiibo, it's my bedtime now so I have to go to sleep.
        Good night @everyone and Good night dad!""")
        await client.close()
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
