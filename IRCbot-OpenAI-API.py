# IRC-GPT2-Chatbot
# by FlyingFathead & ChaosWhisperer | v0.27 | 03/AUG/2023
# https://github.com/FlyingFathead/IRCBot-OpenAI-API/

#
# > imports
#

# time & logging
from datetime import datetime, timedelta
import time
import logging
import json
import random

# Read the configuration file
with open('config.json', 'r') as f:
    config = json.load(f)

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

#
# > config
#

# Configuration: open our config file from `config.json`
try:
    with open('config.json') as config_file:
        config = json.load(config_file)
except FileNotFoundError:
    print("Error: The config.json file was not found.")
    sys.exit(1)
except json.JSONDecodeError:
    print("Error: The config.json file is not a valid JSON file.")
    sys.exit(1)

# the number of past interactions to remember
MAX_TOKENS = config['DEFAULT']['MAX_TOKENS']

# max past tokens
MAX_PAST_INTERACTIONS = config['DEFAULT']['MAX_PAST_INTERACTIONS']

# set debug mode True/False
# not in use rn
debug = config['DEFAULT']['debug']

# Set verbosity flag (True/False)
bot_is_verbose = config['DEFAULT']['bot_is_verbose']

# Time in seconds between each response
# For example, a value of 60 would allow one response per minute
RATE_LIMIT_SECONDS = config['DEFAULT']['RATE_LIMIT_SECONDS']

# Probabilities for the bot to answer to the message. 1 = answer every time
ANSWER_PROBABILITY = config['DEFAULT']['ANSWER_PROBABILITY']

# ===============
# Preset messages
# ===============
# Define messages. English:
# messages = config['MESSAGES']

# Define messages. Finnish:
messages = config['MESSAGES_FI']

# ===============
# Admin settings
# ==============

# List of admin nicknames that are allowed to mute the bot
ADMIN_NICKNAMES = config['DEFAULT']['ADMIN_NICKNAMES']

# ========================
# IRC settings of your bot
# ========================

# your irc server's name/hostmask
SERVER = config['DEFAULT']['SERVER']

# the IRC server port you want the bot to connect to
PORT = config['DEFAULT']['PORT']

# the nick you want the bot to use
NICKNAME = config['DEFAULT']['NICKNAME']

# the real name of the bot (displayed on /whois)
REALNAME = config['DEFAULT']['REALNAME']

# the username of the bot
USERNAME = config['DEFAULT']['USERNAME']

# the channel you want the bot to join to
CHANNEL = config['DEFAULT']['CHANNEL']

# the IRC network in question, for chatbot's reference
# (can be i.e. Freenode, EFnet, Undernet, QuakeNet, DALnet, IRCnet...)
NETWORK = config['DEFAULT']['NETWORK']

# The nickname and/or contact details of the bot's admin
BOT_ADMIN_INFO = config['DEFAULT']['BOT_ADMIN_INFO']

# Respond to all messages, or only when the bot is addressed?
# If True, the bot will respond to all messages. If False, it will only respond to messages that start with its nickname.
RESPOND_TO_ALL = config['DEFAULT']['RESPOND_TO_ALL']

# Replace unicode emojis with ASCII? True = yes, False = no
USE_EMOJI_DICT = config['DEFAULT']['USE_EMOJI_DICT']

# Emoji replacement dictionary location
EMOJI_DICT_FILE = config['DEFAULT']['EMOJI_DICT_FILE']

# Convert the first character of each sentence to lowercase? True = yes, False = no
CONVERT_TO_LOWER = config['DEFAULT']['CONVERT_TO_LOWER']

# API system message (sent to the bot as instructions)
api_system_message =f"You're {NICKNAME}, an IRC bot. Answer within the limits of IRC message length (less than 400 character replies only). Your handle is {NICKNAME}, you are on {NETWORK}, on channel {CHANNEL}. Your admin's contact: {BOT_ADMIN_INFO}."

api_system_message_template = config['DEFAULT']['api_system_message']
api_system_message = api_system_message_template.format(NICKNAME=NICKNAME, NETWORK=NETWORK, CHANNEL=CHANNEL, BOT_ADMIN_INFO=BOT_ADMIN_INFO)

# ~~~
#
# > let's roll
#

# Variable to hold the mute end time
mute_end_time = None

# Time when the last response was sent
last_response_time = datetime.now() - timedelta(days=1)  # Set to a day ago
# last_response_time = datetime.now()

# Replace 'user_contexts' with 'chatroom_contexts'
chatroom_contexts = {}

# (for multi-user mode) Initialize an empty dictionary for each user's context
user_contexts = {}

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

# Load the emoji replacement dictionary
def load_emoji_dict(filepath):
    emoji_dict = {}
    with open(filepath, 'r') as f:
        for line in f:
            # Remove quotation marks
            line = line.replace('"', '')
            if not line.strip():  # If line is empty, skip it
                continue
            if ": " not in line:  # If there's no colon separator, skip it
                continue
            emoji, replacement = line.strip().split(': ', 1)  # Split at the first colon
            emoji_dict[emoji] = replacement
    return emoji_dict

# Load the emoji dictionary from the specified file if the USE_EMOJI_DICT flag is set
if USE_EMOJI_DICT:
    emoji_dict = load_emoji_dict(EMOJI_DICT_FILE)
    # (debug) Print the contents of the emoji dictionary
    print("[INFO] Loaded emoji dictionary:")
    print(emoji_dict)

# (debug) Print the contents of the emoji dictionary
print("[INFO] Loaded emoji dictionary:")
print(emoji_dict)

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

""" # split messages that are too long
def split_message(message, max_length):
    return [message[i:i+max_length] for i in range(0, len(message), max_length)] """

""" def split_message(message, max_length):
    # Subtract the length of other parts of the IRC message from max_length
    max_length -= len("PRIVMSG {} :".format(CHANNEL)) + len("\r\n") + len(NICKNAME)
    return [message[i:i+max_length] for i in range(0, len(message), max_length)] """

""" def split_message(message, max_bytes):
    messages = []
    current_message = ""
    current_bytes = 0
    for word in message.split():
        word_bytes = len(word.encode('utf-8'))
        if current_bytes + word_bytes < max_bytes:
            current_message += word + " "
            current_bytes += word_bytes
        else:
            messages.append(current_message.strip())  # strip trailing spaces
            current_message = word + " "
            current_bytes = word_bytes
    if current_message:
        messages.append(current_message.strip())  # strip trailing spaces
    return messages """

def split_message(message, max_bytes):
    messages = []
    current_message = ""
    current_bytes = 0
    for word in message.split():
        word_bytes = len(word.encode('utf-8'))
        if current_bytes + word_bytes < max_bytes:
            current_message += word + " "
            current_bytes += word_bytes
        else:
            messages.append(current_message.strip())  # strip trailing spaces
            current_message = word + " "
            current_bytes = word_bytes
    if current_message:
        messages.append(current_message.strip())  # strip trailing spaces
    return messages

class Bot:
    def __init__(self, server, channel, nickname):
        self.message_count = 0
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
        print("[INFO] Connection to server established. Joining channel.")
        self.connection.join(self.channel)

    def on_pubmsg(self, connection, event):
        global mute_end_time
        global last_response_time
        global RATE_LIMIT_SECONDS
        global RESPOND_TO_ALL
        print("[INFO] Status of RESPOND_TO_ALL: " + str(RESPOND_TO_ALL))
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            input_text = event.arguments[0]
            sender_username = event.source.nick  # Get the sender's username from the IRC event            
            formatted_input = f"<{timestamp}> <{sender_username}> {self.nickname}: {input_text}"
            print(formatted_input)

            # Handle rate limit command
            if input_text.startswith("!ratelimit"):
                if sender_username in ADMIN_NICKNAMES:
                    try:
                        new_rate_limit = int(input_text.split(" ")[1])  # Get the new rate limit from the command
                        RATE_LIMIT_SECONDS = new_rate_limit  # Update the rate limit
                        message_parts = split_message(MSG_RATE_LIMIT_SET.format(new_rate_limit, sender_username), 512)
                        for part in message_parts:
                            self.connection.privmsg(self.channel, part)
                    except (IndexError, ValueError):
                        message_parts = split_message(MSG_INVALID_RATE_LIMIT, 512)
                        for part in message_parts:
                            self.connection.privmsg(self.channel, part)
                else:
                    message_parts = split_message(MSG_NO_ADMIN_PRIV.format(sender_username), 512)
                    for part in message_parts:
                        self.connection.privmsg(self.channel, part)

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
            formatted_input = f"<{timestamp}> <{sender_username}> {input_text}"
            conversation_history.append(formatted_input)
            while len(conversation_history) > MAX_PAST_INTERACTIONS:
                conversation_history.pop(0)
            chatroom_contexts[self.channel] = conversation_history

            print(formatted_input)  # Now it's safe to print formatted_input

            # Only respond if the message starts with the bot's nickname and the bot is not muted
            # and enough time has passed since the last response
            # Only respond if the bot is set to respond to all messages or if the message starts with the bot's nickname.
            # if input_text.startswith(self.nickname + ":") and (mute_end_time is None or datetime.now() >= mute_end_time):
            # Also check that the bot is not muted and enough time has passed since the last response.
            # Check if the bot is not muted and enough time has passed since the last response.
            print("Checking if bot is muted")
            if (mute_end_time is None or datetime.now() >= mute_end_time):                
                print("Bot is not muted")
                print("Checking if bot can send a message based on rate limit")
                if datetime.now() - last_response_time >= timedelta(seconds=RATE_LIMIT_SECONDS):
                    print("Bot can send a message based on rate limit")
                    print("Checking if bot should respond to all messages")

                    # If RESPOND_TO_ALL is True, respond to all messages.
                    if RESPOND_TO_ALL:

                        # Add the following check for ANSWER_PROBABILITY
                        if random.random() < ANSWER_PROBABILITY:

                            formatted_input = f"<{timestamp}> <{sender_username}> {self.nickname}: {input_text}"
                            print("Bot should respond to all messages")
                            response = self.interact_model(self, input_text, sender_username, formatted_input)
                            print(f"Response from interact_model: {response}")
                            
                            # response_parts = split_message(response, 500)  # Split the response into parts

                            max_bytes = 500 - len('PRIVMSG') - len(self.channel) - len(':') - 2
                            response_parts = split_message(response, max_bytes)


                            print(f"Response parts: {response_parts}")
                            for part in response_parts:
                                self.connection.privmsg(self.channel, part)
                                print(f"Sent message part: {part}")
                            last_response_time = datetime.now()  # Update the last response time
                            print("Rate limit has expired. Answering to messages again...")  # Console message for rate limit expiration
                    
                    # If RESPOND_TO_ALL is False, only respond to messages that start with the bot's nickname.
                    elif input_text.startswith(self.nickname + ":"):
                        print("Bot should respond only to messages that start with its name")
                        response = self.interact_model(self, input_text, sender_username, formatted_input)
                        response_parts = split_message(response, 512)  # Split the response into parts
                        for part in response_parts:
                            self.connection.privmsg(self.channel, part)
                        last_response_time = datetime.now()  # Update the last response time
                        print("Rate limit has expired. Answering to messages again...")  # Console message for rate limit expiration
                else:
                    # Send a rate limit warning to the user, if the bot_is_verbose flag is True
                    if bot_is_verbose:
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

        # Check if the model output is a function call
        model_output = response['choices'][0]['message']
        if model_output['role'] == 'assistant' and 'type' in model_output and model_output['type'] == 'function_call':
            function_name = model_output['content']['name']
            function_args = model_output['content']['args']

            # If the function is 'quit', instruct the bot to quit
            if function_name == 'quit':
                print("Received quit command from the model.")
                bot.quit()  # Assuming you have a quit method in your Bot class
        else:
            # If the model output is not a function call, parse the output and add it to the conversation history
            output_text = model_output['content']
            output_text_clean = ""

            # If the bot is set to replace emojis, do it
            if USE_EMOJI_DICT:
                output_text_clean = output_text
                print(f"Before replacement: {output_text_clean}")
                for emoji, replacement in emoji_dict.items():
                    # debug
                    # print(f"Replacing {emoji} with {replacement}")
                    output_text_clean = output_text_clean.replace(emoji, replacement + ' ')  # Add space after each replacement
                print(f"After replacement: {output_text_clean}")

                output_text = output_text_clean  # Add this line
                output_text_clean = output_text_clean.strip()  # Remove leading and trailing whitespace

            # If the bot is not set to replace emojis, use the original output text
            else:
                output_text_clean = output_text

            # If RESPOND_TO_ALL is False and the input starts with the bot's name, parse the output
            if not RESPOND_TO_ALL and input_text.startswith(bot.nickname + ":"):
                output_text_clean = output_text.split("> ", 2)[-1]
                output_text_clean = output_text_clean.split(": ", 1)[-1]  # splits at the first colon followed by a space
            else:
                # Use the raw output text if RESPOND_TO_ALL is True, but remove the timestamp and bot's nick
                output_text_clean = output_text.split("> ", 2)[-1]  # splits at the second '>'
                output_text_clean = output_text_clean.strip()  # remove leading and trailing whitespace

            # Add the cleaned output_text to the conversation history
            conversation_history.append(f"<{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}> <{NICKNAME}> {output_text_clean}")

            # Update the chatroom's conversation history in chatroom_contexts
            chatroom_contexts[bot.channel] = conversation_history

            # convert sentence breaks to lowercase
            if CONVERT_TO_LOWER:
                sentences = re.split('([.!?] )', output_text_clean)
                sentences = [sentence[0].lower() + sentence[1:] if sentence else '' for sentence in sentences]
                output_text_clean = "".join(sentences)

            # Remove newline and carriage return characters
            # IMPORTANT: these are pretty much mandatory; otherwise the client will crash.
            return output_text_clean.replace("\n", " ").replace("\r", " ")

    def start(self):
        self.connect()
        self.reactor.process_forever()

if __name__ == "__main__":
    bot = Bot(SERVER, CHANNEL, NICKNAME)
    bot.start()
