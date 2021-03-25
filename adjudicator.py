import glob
import io
import json
import os
import pickle
import random
import re
import shutil
from tempfile import TemporaryFile
from datetime import datetime

import discord
from dotenv import load_dotenv

from bmiibo import balance
from chess import Game, choose_positions

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
DAD = int(os.getenv("DAD"))
DIR = os.getenv("BMIIBO_DIR")
TEMPLATES = os.getenv("TEMPLATES_DIR")

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
    "Don't tell the others but you're my favourite!",
    "Damn, you are absolutely *killing* it today!",
    "Did you do your hair different this morning? It looks great!",
    "I can already tell that you've got today in the bag.",
    "Is it hot in hear? Oh nah it's just *you*!",
    "Just remember you deserve some you time every now and again. Don't be afraid to spoil yourself!",
    "If you ever feel like the world is crashing down on you, just know I've got your back!"
]

client = discord.Client()
prefix = "!"
claim_regex = re.compile(r"claim\s+(\w{2,20})(:(\w{2,20}))?")
edit_regex = re.compile(r"edit\s+(attack|ability|ultimate)(\[\d+])?:(\w{1,20})=(number|string):(\w{1,20})")
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


def claim(user_id, name, template=None):
    if user_id in claimed.keys():
        return 2
    elif name in claimed.values():
        return 0
    elif template and any(map(lambda a: not os.path.exists(f"{TEMPLATES}{template}_{a}"), ["attack", "ability", "ultimate"])):
        return 3
    else:
        claimed[user_id] = name
        with open("claims", "wb") as claims_file:
            pickle.dump(claimed, claims_file)
        if template:

            if "wild" == template:
                for action_name in ["attack", "ability", "ultimate"]:
                    shutil.copyfile(random.choice(glob.glob(f"{TEMPLATES}*_{action_name}")), f"{DIR}{name}_{action_name}.json")
            else:
                for action_name in ["attack", "ability", "ultimate"]:
                    shutil.copyfile(f"{TEMPLATES}{template}_{action_name}", f"{DIR}{name}_{action_name}.json")
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

    if index:
        index = int(index[1:-1])

    if action_key not in edits.keys():
        if os.path.exists(file_name := f"{DIR}{action_key}.json"):
            with open(file_name, "r") as action_file:
                edits[action_key] = json.load(action_file)
        else:
            edits[action_key] = list() if index is not None else dict()

    if type(action_data := edits[action_key]) is list:
        if type(index) is int:
            return edit_group(action_data, index, key, value_type, value)
        else:
            return 0
    else:
        if type(index) is int:
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
                    if balance(action, edits[action_name]):
                        with open(f"{DIR}{action_name}.json", "w") as action_file:
                            json.dump(edits[action_name], action_file)
                        return 2
                    else:
                        return 3
        elif (action_name := f"{claimed[user_id]}_{action}") in edits.keys():
            if balance(action, edits[action_name]):
                with open(f"{DIR}{action_name}.json", "w") as action_file:
                    json.dump(edits[action_name], action_file)
                return 2
            else:
                return 3
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
    print(f"I'm all ready to go! wish me luck!")


@client.event
async def on_message(message):
    if message.author == client.user:
        return
    elif (strip_message := message.content.strip()).startswith(f"{prefix}judy"):
        if "claim" in strip_message:
            matches = claim_regex.search(strip_message)
            if matches:
                if 1 == (claim_result := claim(message.author.id, matches[1], template=matches[3])):
                    await message.channel.send(f"claimed `{matches[1]}` for {message.author.name}")
                elif 0 == claim_result:
                    await message.channel.send(f"sorry {message.author.name}! `{matches[1]}` has already been claimed :(")
                elif 2 == claim_result:
                    await message.channel.send(f"sorry {message.author.name}! you've already claimed a name")
                elif 3 == claim_result:
                    await message.channel.send(f"sorry {message.author.name}! `{matches[3]}` is not a valid template")
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
                    elif 3 == save_result:
                        await message.channel.send(
                            f"sorry {message.author.name}! this is too OP!")
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
            
            In his spare time Father made a customizable text-based auto-battler that used Q-learning to attempt to learn 
            how to fight. It was Father's intent to be able to play this with his friends (I'm guessing that's you) 
            and since the game was text based he thought what better way to do it than with me, a discord bot!
            
            Please remember that I'm quite new to this so I may make mistakes now and again, so please be nice!
            
            Thanks, Judy"""
        elif "how" in pro_message:
            if "play" in pro_message:
                with open("bmiibo_rules.pdf", "rb") as rules_file:
                    await message.channel.send(f"I'm glad you asked {message.author.name}! here are the rules", file=discord.File(rules_file, "rules.pdf"))
                return
            response = """
            All my commands are prefixed with `'!judy'`
            
            `claim name`
            where `name` is the name you want to claim for your bmiibo, can only be done once and must be done before
            most other commands. name can be any alphanumeric string between 2 and 20 characters long
            
            `train`
            add your bmiibo to the training list or if it is already in the training list remove it
            
            `edit`
            judy will open a dm with you where you can use dm only commands
            
            DM ONLY=====================================================================================================
            `edit attack|ability|ultimate:parameter=number|string:value`
            where `parameter` is the parameter for that action you want to edit and `value` is what you want to set it
            to. An action is promoted to an action group if an index is used e.g `edit attack[0]:actionType=string:melee`
            if the action already has data it will be placed into the 0 slot of the action group, if you specify an index
            greater than the current length of the action group it will be appended instead (so if you say [99] and there
            are only 3 [0, 1, 2] actions it will edit the newly added [3] slot)
            
            `save attack|ability|ultimate|all`
            saves the specified action, only works if the action is being edited. `all` saves all the actions that you
            are currently editing
            
            `view attack|ability|ultimate|all`
            lets you view the specified action showing you whether it is the version being edited or the one saved
            
            `reset attack|ability|ultimate|all`
            clears the specified action, if an action has been promoted to an action group this is the only way to change 
            it back to a single action
            
            FRIENDLY COMMANDS===========================================================================================
            these commands are run by including the keyword and mentioning judy with `@Adjudicator`
            
            `thank`
            receive a random message showing gratitude and a nice compliment
            
            `what`
            get a description of what judy is built for
            
            `how`
            this message
            """
        else:
            response = "How can I help?"
        if 2000 >= len(response):
            await message.channel.send(response)
        else:
            byte_stream = io.BytesIO(response.encode("utf-8"))
            await message.channel.send("Sorry! the response for this command was too big so i wrote it up in a nice .txt file for you", file=discord.File(byte_stream, "response.txt"))


@client.event
async def on_reaction_add(reaction, user):
    if user == client.user:
        return
    elif "challenge" in reaction.message.content and user in reaction.message.mentions:
        if "🏳️" == str(reaction):
            await reaction.message.delete()
        elif "🏴" == str(reaction):
            if reaction.message.author in reaction.message.mentions:
                await reaction.message.channel.send(f"Sorry {reaction.message.author.name}! you can't challenge yourself")
                await reaction.message.delete()
                return
            challengee_count = len(reaction.message.mentions)
            async for user in reaction.users():
                if user in reaction.message.mentions:
                    challengee_count -= 1
            if 0 == challengee_count:
                with TemporaryFile(mode="w+") as match_file:
                    try:
                        players = reaction.message.mentions + [reaction.message.author]
                        contestants = map(lambda x: claimed[x.id], players)
                        random.shuffle(players)
                        match = Game(4, **{name: pos for name, pos in zip(contestants, choose_positions(len(players), 4))})
                        winner = match.play(training=False, reporting=True, file=match_file)
                        match_file.seek(0)
                        byte_stream = io.BytesIO(match_file.read().encode("utf-8"))
                        await reaction.message.channel.send(
                            f"Congratulations `{winner.name}`! Here's a full breakdown of the match",
                            file=discord.File(byte_stream, f"{datetime.now().strftime('%d/%m/%y_%H/%M/%S')}.txt")
                        )
                        await reaction.message.delete()
                    except KeyError:
                        await reaction.message.channel.send(f"Sorry! looks like someone doesen't have a Bmiibo yet")


client.run(TOKEN)
