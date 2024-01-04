# IRC chatbot for OpenAI API (GPT-3.5, GPT-4...)
# ===
# NOTE: You will need the OpenAI API key to run this as-is!
# Please get your API key from: https://openai.com/
# ===
# by FlyingFathead & ChaosWhisperer
# https://github.com/FlyingFathead/IRCBot-OpenAI-API/

version_number = "0.32.1"

#   =======
# > imports
#   =======

# time & logging
from datetime import datetime, timedelta
import time
import logging
import json
import random

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
from openai import OpenAI

#   ======
# > config
#   ======

# Specify the name of the config file
config_filename = 'config.json'  # `config.json`` for English config, you can specify your own...

# Configuration: open our config file from `config.json`
try:
    with open(config_filename) as config_file:
        config = json.load(config_file)
except FileNotFoundError:
    print(f"Error: The {config_filename} file was not found.")
    sys.exit(1)
except json.JSONDecodeError:
    print(f"Error: The {config_filename} file is not a valid JSON file.")
    sys.exit(1)

# Language of the bot; load configfile accordingly
LANGUAGE = config['DEFAULT']['LANGUAGE']

# the openai model to use
OPENAI_MODEL = config['DEFAULT']['OPENAI_MODEL']

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

# Load the reply delay from the config file
REPLY_DELAY_SECONDS = config['DEFAULT']['REPLY_DELAY_SECONDS']

# ===============
# Preset messages
# ===============
# Get the selected language from the "DEFAULT" section
selected_language = config["DEFAULT"]["LANGUAGE"]

# Select the appropriate messages based on the selected language
if selected_language == 'ENGLISH':
    MESSAGES = config['MESSAGES']
elif selected_language == 'FINNISH':
    MESSAGES = config['MESSAGES_FI']
else:
    print(f'Error: Unknown language "{selected_language}"')
    sys.exit(1)

# MESSAGES
MSG_RATE_LIMIT = MESSAGES["MSG_RATE_LIMIT"]
MSG_NO_ADMIN_PRIV = MESSAGES["MSG_NO_ADMIN_PRIV"]
MSG_INVALID_RATE_LIMIT = MESSAGES["MSG_INVALID_RATE_LIMIT"]
MSG_RATE_LIMIT_SET = MESSAGES["MSG_RATE_LIMIT_SET"]
MSG_INVALID_MUTE_SYNTAX = MESSAGES["MSG_INVALID_MUTE_SYNTAX"]
MSG_NO_MUTE_PRIV = MESSAGES["MSG_NO_MUTE_PRIV"]
MSG_MUTE_SUCCESS = MESSAGES["MSG_MUTE_SUCCESS"]
MSG_NO_GOAWAY_PRIV = MESSAGES["MSG_NO_GOAWAY_PRIV"]
MSG_GOAWAY_SUCCESS = MESSAGES["MSG_GOAWAY_SUCCESS"]

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

# the channel password (if the channel uses one)
CHANNEL_PASSWORD = config['DEFAULT'].get('CHANNEL_PASSWORD')  # Use .get() to return None if the key doesn't exist

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
if LANGUAGE == 'ENGLISH':
    EMOJI_DICT_FILE = config['EMOJI_DICT']['ENGLISH']
elif LANGUAGE == 'FINNISH':
    EMOJI_DICT_FILE = config['EMOJI_DICT']['FINNISH']
else:
    print(f'Error: Unknown language "{LANGUAGE}"')
    sys.exit(1)

# Convert the first character of each sentence to lowercase? True = yes, False = no
CONVERT_TO_LOWER = config['DEFAULT']['CONVERT_TO_LOWER']

# API system message (sent to the bot as instructions)
api_system_message_template = config['DEFAULT']['api_system_message']
api_system_message = api_system_message_template.format(NICKNAME=NICKNAME, NETWORK=NETWORK, CHANNEL=CHANNEL, BOT_ADMIN_INFO=BOT_ADMIN_INFO, SERVER=SERVER)

# ===============
# API key reading
# ===============
# Initialize variables
api_key = None

# First, try to get the API key from an environment variable
api_key = os.getenv('OPENAI_API_KEY')

# If the environment variable is not set, try to read the key from a file
if not api_key:
    try:
        with open('api_token.txt', 'r') as file:
            api_key = file.read().strip()
            if not api_key:
                raise ValueError("API token file is empty")
    except FileNotFoundError:
        print("Error: OPENAI_API_KEY not set as an environment variable and api_token.txt file not found.")
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

# Now initialize the OpenAI client with the API key
client = OpenAI(api_key=api_key)

# ~~~
#   ==========
# > let's roll
#   ==========

# Variable to hold the mute end time
mute_end_time = None

# Time when the last response was sent
last_response_time = datetime.now() - timedelta(days=1)  # Set to a day ago
# last_response_time = datetime.now()

# Replace 'user_contexts' with 'chatroom_contexts'
chatroom_contexts = {}

# (for multi-user mode) Initialize an empty dictionary for each user's context
user_contexts = {}

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
    def __init__(self, server, channel, nickname, channel_password, messages, bot_is_verbose):
        self.bot_is_verbose = bot_is_verbose  # New instance variable
        self.message_count = 0
        self.reactor = irc.client.Reactor()
        # self.reactor.server().errors = 'ignore'  # Ignore encoding errors; treat inbound text as-is
        self.server = server
        self.channel = channel
        self.channel_password = channel_password
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
            self.connection = self.reactor.server().connect(
                self.server, 
                PORT, 
                self.nickname, 
                username=USERNAME, # Pass the USERNAME here
            )
        except irc.client.ServerConnectionError as x:
            logging.error(f"Failed to connect to {self.server}: {x}")
            sys.exit(1)

        # Print successful connection
        logging.info(f"Connected to: {self.server}")

        # Join the channel with the password if it's provided
        if self.channel_password:
            self.connection.join(self.channel, self.channel_password)
        else:
            self.connection.join(self.channel)

        # Print channel join information
        logging.info(f"Joining channel: {self.channel}")

        self.connection.add_global_handler("welcome", self.on_connect)
        self.connection.add_global_handler("pubmsg", self.on_pubmsg)
        self.connection.add_global_handler("privmsg", self.on_privmsg)

    def on_connect(self, connection, event):
    # Join the channel after the connection is established
        print("[INFO] Connection to server established. Joining channel.")
        self.connection.join(self.channel)

    # Commands to take in as `/msg`'s from admins
    def on_privmsg(self, connection, event):
        global RATE_LIMIT_SECONDS        
        sender_username = event.source.nick  # Get the sender's username from the IRC event
        input_text = event.arguments[0]  # Get the text of the message

        # Only process commands if the sender is an admin
        if sender_username in ADMIN_NICKNAMES:
            # Handle rate limit command
            if input_text.startswith("!ratelimit"):
                try:
                    new_rate_limit = int(input_text.split(" ")[1])  # Get the new rate limit from the command
                    previous_rate_limit = RATE_LIMIT_SECONDS  # Store the previous rate limit
                    RATE_LIMIT_SECONDS = new_rate_limit  # Update the rate limit

                    # Print the rate limit change to the console
                    logging.info(f"User {sender_username} changed rate limit from {previous_rate_limit} to {new_rate_limit}")

                    message_parts = split_message(MSG_RATE_LIMIT_SET.format(new_rate_limit, sender_username), 512)
                    for part in message_parts:
                        self.connection.privmsg(sender_username, part)  # Send PM
                except (IndexError, ValueError):
                    message_parts = split_message(MSG_INVALID_RATE_LIMIT, 512)
                    for part in message_parts:
                        self.connection.privmsg(sender_username, part)  # Send PM
            # Other admin commands would go here...
        else:
            message_parts = split_message(MSG_NO_ADMIN_PRIV.format(sender_username), 512)
            for part in message_parts:
                self.connection.privmsg(sender_username, part)  # Send PM

    # Public message responses
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
            # print(formatted_input)

            # Handle rate limit command
            if input_text.startswith("!ratelimit"):
                if sender_username in ADMIN_NICKNAMES:
                    try:
                        new_rate_limit = int(input_text.split(" ")[1])  # Get the new rate limit from the command
                        previous_rate_limit = RATE_LIMIT_SECONDS  # Store the previous rate limit
                        RATE_LIMIT_SECONDS = new_rate_limit  # Update the rate limit

                        # Print the rate limit change to the console
                        logging.info(f"User {sender_username} changed rate limit from {previous_rate_limit} to {new_rate_limit}")

                        if bot_is_verbose:
                            message_parts = split_message(MSG_RATE_LIMIT_SET.format(new_rate_limit, sender_username), 512)
                            for part in message_parts:
                                self.connection.privmsg(self.channel, part)
                    except (IndexError, ValueError):
                        if bot_is_verbose:
                            message_parts = split_message(MSG_INVALID_RATE_LIMIT, 512)
                            for part in message_parts:
                                self.connection.privmsg(self.channel, part)
                else:
                    if bot_is_verbose:
                        message_parts = split_message(MSG_NO_ADMIN_PRIV.format(sender_username), 512)
                        for part in message_parts:
                            self.connection.privmsg(self.channel, part)

            # Handle mute command
            if input_text.startswith("!mute"):
                if sender_username in ADMIN_NICKNAMES:
                    try:
                        mute_duration = int(input_text.split(" ")[1])  # Get the number of minutes from the command
                        mute_end_time = datetime.now() + timedelta(minutes=mute_duration)  # Calculate the mute end time
                        logging.info(f"User {sender_username} muted the bot for {mute_duration} minutes.")
                        if bot_is_verbose:
                            self.connection.privmsg(self.channel, MSG_MUTE_SUCCESS.format(mute_duration, sender_username))
                    except (IndexError, ValueError):
                        if bot_is_verbose:
                            self.connection.privmsg(self.channel, MSG_INVALID_MUTE_SYNTAX)
                else:
                    if bot_is_verbose:
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
                            time.sleep(REPLY_DELAY_SECONDS)  # Pause for a set number of seconds before sending the message
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
                    if self.bot_is_verbose:
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

        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=conversation
        )

        # Check if the model output is a function call
        # model_output = response['choices'][0]['message']
        # If the response is a custom object, you might need to use a specific method to get the desired data.
        # For example, response.get_choices() or similar. This is a placeholder and should be replaced with the correct method.
        try:

            # new way of implementing in `openai` python library v1.6.1
            model_output = response.choices[0].message.content.strip()
            output_text = model_output  # Initialize output_text with model_output

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

            # Example of processing the output as plain text
            # output_text_clean = model_output.strip()

            # Add the cleaned output_text to the conversation history
            conversation_history.append(f"<{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}> <{NICKNAME}> {output_text_clean}")

            # Update the chatroom's conversation history in chatroom_contexts
            chatroom_contexts[bot.channel] = conversation_history

            """ # Add the cleaned output_text to the conversation history
            conversation_history.append(f"<{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}> <{NICKNAME}> {output_text_clean}")

            # Update the chatroom's conversation history in chatroom_contexts
            chatroom_contexts[bot.channel] = conversation_history """

            # convert sentence breaks to lowercase
            if CONVERT_TO_LOWER:
                sentences = re.split('([.!?] )', output_text_clean)
                sentences = [sentence[0].lower() + sentence[1:] if sentence else '' for sentence in sentences]
                output_text_clean = "".join(sentences)

            # Remove newline and carriage return characters
            # IMPORTANT: these are pretty much mandatory; otherwise the client will crash.
            return output_text_clean.replace("\n", " ").replace("\r", " ")

        except AttributeError:
            print("Error: Unable to access response data. Please check the API documentation for correct usage.")
            return ""

    def start(self):
        self.connect()
        self.reactor.process_forever()

if __name__ == "__main__":
    bot = Bot(SERVER, CHANNEL, NICKNAME, CHANNEL_PASSWORD, MESSAGES, bot_is_verbose)
    bot.start()
