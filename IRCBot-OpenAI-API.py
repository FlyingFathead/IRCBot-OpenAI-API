# IRC-GPT2-Chatbot
# by FlyingFathead & ChaosWhisperer | v0.15 | 02/AUG/2023
# https://github.com/FlyingFathead/IRCBot-OpenAI-API/

# time & logging
from datetime import datetime
import time
import logging

# irc bot libraries
import irc.client
import irc.events

# configparser
import configparser

# for fixing non-unicode inputs
from jaraco.stream import buffer

import json, os, string, sys, threading, random, logging, time
import re
import os
import random
import openai

MAX_TOKENS = 4096
MAX_PAST_INTERACTIONS = 100  # the number of past interactions to remember

# set debug mode True/False
# not in use rn
# debug = True

# Replace 'user_contexts' with 'chatroom_contexts'
chatroom_contexts = {}

# (for multi-user mode) Initialize an empty dictionary for each user's context
user_contexts = {}

# ========================
# IRC settings of your bot
# ========================

# your irc server's name/hostmask
SERVER="irc.atw-inter.net"

# the IRC server port you want the bot to connect to
PORT=6667

# the nick you want the bot to use
NICKNAME="ChatKeke"

# the real name of the bot (displayed on /whois)
REALNAME="Original ChatKeke[TM]. Powered by GPT-4"

# the username of the bot
USERNAME="ChatKeke"

# the channel you want the bot to join to
CHANNEL="#chatkeke"

# the IRC network in question, for ChatKeke's reference
NETWORK="IRCnet"

# API system message
api_system_message = f"Olet ChatKeke, mukava ja hupaisa IRC-chatbot. Vastaa IRC-riveille mahtuvilla viestinmitoilla (n.400 merkkiä), tilanteen vaatiessa voit käyttää emojeita ja hymiöitä, kuten :) ja :D. Olet {NETWORK}-verkossa, palvelimella {SERVER}, kanavalla {CHANNEL}. ChatKeken web-versio: chatkeke.fi. Skrolli-lehti: skrolli.fi. ChatKeken tekijä on paikalla nickillä HarryTuttle."

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
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            input_text = event.arguments[0]
            sender_username = event.source.nick  # Get the sender's username from the IRC event
            formatted_input = f"<{timestamp}> <{sender_username}> {input_text}"
            print(formatted_input)

            # Update the chatroom's conversation history
            conversation_history = chatroom_contexts.get(self.channel, [api_system_message])
            conversation_history.append(formatted_input)
            while len(conversation_history) > MAX_PAST_INTERACTIONS:
                conversation_history.pop(0)
            chatroom_contexts[self.channel] = conversation_history

            # Only respond if the message starts with the bot's nickname
            if input_text.startswith(self.nickname + ":"):
                response = self.interact_model(self, input_text, sender_username, formatted_input)
                # response = interact_model(self, input_text, sender_username, formatted_input)
                response_parts = split_message(response, 400)  # Split the response into parts
                for part in response_parts:
                    self.connection.privmsg(self.channel, part)
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
            model="gpt-4-0613",
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

        return output_text_clean

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
