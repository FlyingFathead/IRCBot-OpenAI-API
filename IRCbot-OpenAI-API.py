# IRC-GPT2-Chatbot
# by FlyingFathead & ChaosWhisperer | v0.23 | 02/AUG/2023
# https://github.com/FlyingFathead/IRCBot-OpenAI-API/

# time & logging
from datetime import datetime, timedelta
import time
import logging

# irc bot libraries
import irc.client
import irc.events

# configparser
import configparser

# for fixing non-unicode inputs
from jaraco.stream import buffer

import json, os, string, sys, threading, logging, time
import re
import os
import random
import openai

MAX_TOKENS = 2096
MAX_PAST_INTERACTIONS = 40  # the number of past interactions to remember

# set debug mode True/False
# not in use rn
# debug = True

# Replace 'user_contexts' with 'chatroom_contexts'
chatroom_contexts = {}

# (for multi-user mode) Initialize an empty dictionary for each user's context
user_contexts = {}

# Time in seconds between each response
# For example, a value of 60 would allow one response per minute
RATE_LIMIT_SECONDS = 60

# Time when the last response was sent
last_response_time = datetime.now()

# ===============
# Preset messages
# ===============
# Define messages (in English):
MSG_RATE_LIMIT = "Sorry! I'm taking a break right now, try again later!"
MSG_NO_ADMIN_PRIV = "Error: Sorry {}, but you don't have the privileges to control me!"
MSG_INVALID_RATE_LIMIT = "Error: Invalid value for response rate limit. Usage: !ratelimit <seconds>"
MSG_RATE_LIMIT_SET = "Response rate limit has been set to {} seconds by user {}."
MSG_INVALID_MUTE_SYNTAX = "Error: Invalid mute message syntax. Usage: !mute <minutes>"
MSG_NO_MUTE_PRIV = "Error: Apologies, dear {}, but you can't just silence me! You don't have the necessary privileges."
MSG_MUTE_SUCCESS = "I'll be quiet for {} minutes at the request of user {}! Shh!"
MSG_NO_GOAWAY_PRIV = "Error: Unfortunately, {}, you don't have the rights to send me away! No!"
MSG_GOAWAY_SUCCESS = "Now it's time for me to go, see you soon! 😢"

""" # Define messages (alternative, in Finnish):
MSG_RATE_LIMIT = "Sori! Keke on nyt tauolla, koita myöhemmin uudelleen!"
MSG_NO_ADMIN_PRIV = "Virhe: Sori vaan {}, mutta sulla ei ole oikeutta säädellä mua!"
MSG_INVALID_RATE_LIMIT = "Virhe: Virheellinen arvo vastausten aikarajoituksille. Käyttöohje: !ratelimit <sekuntia>"
MSG_RATE_LIMIT_SET = "Vastausten rajoitus asetettu {} sekuntiin käyttäjän {} toimesta."
MSG_INVALID_MUTE_SYNTAX = "Virhe: Epävalidi mute-viestin syntaksi. Käyttöohje: !mute <minuuttia>"
MSG_NO_MUTE_PRIV = "Virhe: Pahoitteluni, arvon {}, mutta minua et noin vaan hiljennä! Sinulla ei ole siihen tarvittavia oikeuksia."
MSG_MUTE_SUCCESS = "ChatKeke on nyt vaiti {} minuuttia käyttäjän {} pyynnöstä! Tui tui!"
MSG_NO_GOAWAY_PRIV = "Virhe: Valitettavasti, {} sinulla ei ole oikeuksia lähettää minua pois! Ni! "
MSG_GOAWAY_SUCCESS = "Nyt minun on aika mennä, nähdään pian! 😢" """

# ===============
# Admin settings
# ==============

# List of admin nicknames that are allowed to mute the bot
ADMIN_NICKNAMES = ["adminnick1", "adminnick2"]

# Variable to hold the mute end time
mute_end_time = None

# ========================
# IRC settings of your bot
# ========================

# your irc server's name/hostmask
SERVER="YOUR_IRC_SERVER_ADDRESS_HERE"

# the IRC server port you want the bot to connect to
PORT=6667

# the nick you want the bot to use
NICKNAME="GPT4Bot"

# the real name of the bot (displayed on /whois)
REALNAME="Powered by GPT-4!"

# the username of the bot
USERNAME="GPT4Bot"

# the channel you want the bot to join to
CHANNEL="#gpt4"

# the IRC network in question, for ChatKeke's reference
NETWORK="IRCnet"

# API system message
api_system_message = f"You are a friendly and happy IRC chat bot. You are on {NETWORK} and the channel is {CHANNEL}. Your nick is {GPT4Bot}. The server is {SERVER}."

#
# > let's roll
#

# API key reading
# First, try to get the API key from an environment variable
openai.api_key = os.getenv('OPENAI_API_KEY')

# If the environment variable is not set, try to read the key from a file
if openai.api_key is None:
    try:
        with open('api_token.txt', 'r') as file:
            openai.api_key = file.read().strip()
    except FileNotFoundError:
        print("Error: The OPENAI_API_KEY environment variable is not set, and api_token.txt was not found. Please set the environment variable or create this file with your OpenAI API key.")
        sys.exit(1)

# If the key is still None at this point, neither method was successful
if openai.api_key is None:
    print("Error: Failed to obtain OpenAI API key. Please set the OPENAI_API_KEY environment variable or create a file named api_token.txt with your OpenAI API key.")
    sys.exit(1)

# turns
# global turns
# turns = []

# Global variable to store the current time
now = ""

# Define a custom logging formatter
class CustomFormatter(logging.Formatter):
    def format(self, record):
        now = time.strftime('%Y-%m-%d %H:%M:%S')  # Get the current time
        record.now = now  # Add the 'now' attribute to the log record
        return super().format(record)

# Configure logging with the custom formatter
logging_format = '[{now}][{levelname}] {message}'
logging.basicConfig(format=logging_format, style='{', level=logging.INFO)
logging.getLogger().handlers[0].formatter = CustomFormatter(logging_format, style='{')

# split messages that are too long
def split_message(message, max_length):
    return [message[i:i+max_length] for i in range(0, len(message), max_length)]

class Bot:
    def __init__(self, server, channel, nickname):
        self.reactor = irc.client.Reactor()
        # self.reactor.server().errors = 'ignore'  # Ignore encoding errors; treat inbound text as-is
        self.server = server
        self.channel = channel
        self.nickname = nickname

        # UTF-8 fixes
        irc.client.ServerConnection.buffer_class = buffer.LenientDecodingLineBuffer
        irc.client.ServerConnection.buffer_class.errors = 'replace'  # replace invalid bytes

    def connect(self):        
        global now  # Indicate that we want to use the global 'now' variable

        # Get the current time
        now = time.strftime('%Y-%m-%d %H:%M:%S')

        # UTF-8 fixes
        irc.client.ServerConnection.buffer_class = buffer.LenientDecodingLineBuffer
        irc.client.ServerConnection.buffer_class.errors = 'replace'  # replace invalid bytes

        # Print connection information
        logging.info(f"Connecting to IRC network: {self.server}, port {PORT}")
        logging.info(f"Nickname: {self.nickname}")
        logging.info(f"Username: {USERNAME}")
        logging.info(f"Realname: {REALNAME}")

        try:
            self.connection = self.reactor.server().connect(self.server, PORT, self.nickname)
        except irc.client.ServerConnectionError as x:
            logging.error(f"Failed to connect to {self.server}: {x}")
            sys.exit(1)

        # Print successful connection
        logging.info(f"Connected to: {self.server}")

        self.connection.join(self.channel)

        # Print channel join information
        logging.info(f"Joining channel: {self.channel}")

        self.connection.add_global_handler("welcome", self.on_connect)
        self.connection.add_global_handler("pubmsg", self.on_pubmsg)
    
    def on_connect(self, connection, event):
    # Join the channel after the connection is established
        self.connection.join(self.channel)

    def on_pubmsg(self, connection, event):
        global mute_end_time
        global last_response_time
        global RATE_LIMIT_SECONDS        
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            input_text = event.arguments[0]
            sender_username = event.source.nick  # Get the sender's username from the IRC event
            formatted_input = f"<{timestamp}> <{sender_username}> {input_text}"
            print(formatted_input)

            # Handle rate limit command
            if input_text.startswith("!ratelimit"):
                if sender_username in ADMIN_NICKNAMES:
                    try:
                        new_rate_limit = int(input_text.split(" ")[1])  # Get the new rate limit from the command
                        RATE_LIMIT_SECONDS = new_rate_limit  # Update the rate limit
                        self.connection.privmsg(self.channel, MSG_RATE_LIMIT_SET.format(new_rate_limit, sender_username))
                    except (IndexError, ValueError):
                        self.connection.privmsg(self.channel, MSG_INVALID_RATE_LIMIT)
                else:
                    self.connection.privmsg(self.channel, MSG_NO_ADMIN_PRIV.format(sender_username))

            # Handle mute command
            if input_text.startswith("!mute"):
                if sender_username in ADMIN_NICKNAMES:
                    try:
                        mute_duration = int(input_text.split(" ")[1])  # Get the number of minutes from the command
                        mute_end_time = datetime.now() + timedelta(minutes=mute_duration)  # Calculate the mute end time
                        self.connection.privmsg(self.channel, MSG_MUTE_SUCCESS.format(mute_duration, sender_username))
                    except (IndexError, ValueError):
                        self.connection.privmsg(self.channel, MSG_INVALID_MUTE_SYNTAX)
                else:
                    self.connection.privmsg(self.channel, MSG_NO_MUTE_PRIV.format(sender_username))

            # Handle goaway command
            if input_text.startswith("!goaway"):
                if sender_username in ADMIN_NICKNAMES:
                    self.connection.privmsg(self.channel, MSG_GOAWAY_SUCCESS)
                    sys.exit(0)
                else:
                    self.connection.privmsg(self.channel, MSG_NO_GOAWAY_PRIV.format(sender_username))

            # Update the chatroom's conversation history
            conversation_history = chatroom_contexts.get(self.channel, [api_system_message])
            conversation_history.append(formatted_input)
            while len(conversation_history) > MAX_PAST_INTERACTIONS:
                conversation_history.pop(0)
            chatroom_contexts[self.channel] = conversation_history

            # Only respond if the message starts with the bot's nickname and the bot is not muted
            # and enough time has passed since the last response
            if input_text.startswith(self.nickname + ":") and (mute_end_time is None or datetime.now() >= mute_end_time):
                if datetime.now() - last_response_time >= timedelta(seconds=RATE_LIMIT_SECONDS):
                    response = self.interact_model(self, input_text, sender_username, formatted_input)
                    response_parts = split_message(response, 400)  # Split the response into parts
                    for part in response_parts:
                        self.connection.privmsg(self.channel, part)
                    last_response_time = datetime.now()  # Update the last response time
                else:
                    # Send a rate limit warning to the user
                    self.connection.privmsg(self.channel, MSG_RATE_LIMIT)

        except UnicodeDecodeError:
            print("[WARN/ERROR] A message was received that could not be decoded. Skipping.")

    @staticmethod
    def interact_model(bot, input_text, sender_username, formatted_input=None):
        # Retrieve the chatroom's conversation history from chatroom_contexts, or initialize it with the starting context
        conversation_history = chatroom_contexts.get(bot.channel, [api_system_message])

        # Generate the model's response using the conversation history
        conversation = [{'role': 'system', 'content': api_system_message}]
        for turn in conversation_history:
            conversation.append({'role': 'user', 'content': turn})

        response = openai.ChatCompletion.create(
            # model="gpt-4-0613", # for gpt-4
            model="gpt-3.5-turbo",
            messages=conversation,
        )

        print("Response from the model:", response)  # Print the response for debugging purposes

        # Get the model's output
        output_text = response['choices'][0]['message']['content']

        # Initialize output_text_clean with an empty string
        output_text_clean = ""

        # Parse out the timestamp, bot's name and reply-to-nick
        if input_text.startswith(bot.nickname + ":"):
            output_text_clean = output_text.split("> ", 2)[-1]
            output_text_clean = output_text_clean.split(": ", 1)[-1]  # splits at the first colon followed by a space

        # Add the cleaned output_text to the conversation history
        conversation_history.append(f"<{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}> <{NICKNAME}> {output_text_clean}")

        # Update the chatroom's conversation history in chatroom_contexts
        chatroom_contexts[bot.channel] = conversation_history

        # Remove newline and carriage return characters
        return output_text_clean.replace("\n", " ").replace("\r", " ")

    def generate_response(bot, input_text, sender_username):
        response = interact_model(bot, input_text, sender_username)

        # Remove any newline or carriage return characters
        response = response.replace("\n", " ").replace("\r", " ")

        # Split the response into parts that do not exceed the maximum length
        response_parts = split_message(response, 400)  # 400 to leave some room for other parts of the IRC message

        # Send each part of the response separately
        for part in response_parts:
            bot.connection.privmsg(bot.channel, part)

        # Concatenate the response parts into a single string
        # full_response = ' '.join(response_parts)

        return response

    def start(self):
        self.connect()
        self.reactor.process_forever()

if __name__ == "__main__":
    bot = Bot(SERVER, CHANNEL, NICKNAME)
    bot.start()    
