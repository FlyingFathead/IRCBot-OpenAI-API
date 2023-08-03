# IRC-GPT2-Chatbot
# by FlyingFathead & ChaosWhisperer | v0.26 | 03/AUG/2023
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

MAX_TOKENS = 3096
MAX_PAST_INTERACTIONS = 20  # the number of past interactions to remember

# set debug mode True/False
# not in use rn
debug = True

# Replace 'user_contexts' with 'chatroom_contexts'
chatroom_contexts = {}

# (for multi-user mode) Initialize an empty dictionary for each user's context
user_contexts = {}

# Set verbosity flag (True/False)
bot_is_verbose = False

# Time in seconds between each response
# For example, a value of 60 would allow one response per minute
RATE_LIMIT_SECONDS = 10

# Time when the last response was sent
last_response_time = datetime.now() - timedelta(days=1)  # Set to a day ago
# last_response_time = datetime.now()

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
MSG_GOAWAY_SUCCESS = "Now it's time for me to go, I hope to see you again some day! 😢"

# Define messages (alternative, in Finnish):
""" MSG_RATE_LIMIT = "Sori! Keke on nyt tauolla, koita myöhemmin uudelleen!"
MSG_NO_ADMIN_PRIV = "Virhe: Sori vaan {}, mutta sulla ei ole oikeutta säädellä mua!"
MSG_INVALID_RATE_LIMIT = "Virhe: Virheellinen arvo vastausten aikarajoituksille. Käyttöohje: !ratelimit <sekuntia>"
MSG_RATE_LIMIT_SET = "Vastausten rajoitus asetettu {} sekuntiin käyttäjän {} toimesta."
MSG_INVALID_MUTE_SYNTAX = "Virhe: epäkelpo mute-viestin syntaksi. Käyttöohje: !mute <minuuttia>"
MSG_NO_MUTE_PRIV = "Virhe: Pahoitteluni, arvon {}, mutta minua et noin vaan hiljennä! Sinulla ei ole siihen tarvittavia oikeuksia."
MSG_MUTE_SUCCESS = "ChatKeke on nyt vaiti {} minuuttia käyttäjän {} pyynnöstä! Tui tui!"
MSG_NO_GOAWAY_PRIV = "Virhe: Valitettavasti, {} sinulla ei ole oikeuksia lähettää minua pois! Ni! "
MSG_GOAWAY_SUCCESS = "Nyt minun on näköjään aika mennä, toivottavasti nähdään taas pian! 😢" """

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
SERVER="<IRC server hostmask or ip>"

# the IRC server port you want the bot to connect to
PORT=6667

# the nick you want the bot to use
NICKNAME="AIbot"

# the real name of the bot (displayed on /whois)
REALNAME="Original ChatKeke[TM]. Powered by OpenAI API"

# the username of the bot
USERNAME="AIbot"

# the channel you want the bot to join to
CHANNEL="#OpenAI"

# the IRC network in question, for chatbot's reference
# (can be i.e. Freenode, EFnet, Undernet, QuakeNet, DALnet, IRCnet...)
NETWORK="EFnet" 

# The nickname and/or contact details of the bot's admin
BOT_ADMIN_INFO = "<ADMIN'S NICKNAME / BOT OWNER INFO>"

# API system message (sent to the bot as instructions)
api_system_message =f"You're {NICKNAME}, an IRC bot. Answer within the limits of IRC message length (less than 400 character replies only). Your handle is {NICKNAME}, you are on {NETWORK}, on channel {CHANNEL}. Your admin's contact: {BOT_ADMIN_INFO}."

# Respond to all messages, or only when the bot is addressed?
# If True, the bot will respond to all messages. If False, it will only respond to messages that start with its nickname.
RESPOND_TO_ALL = True

# Replace unicode emojis with ASCII? True = yes, False = no
USE_EMOJI_DICT = True

# Emoji replacement dictionary location
# Finnish emoji replacement dictionary
# EMOJI_DICT_FILE = './emoji_dict_finnish.txt'

# English emoji replacement dictionary
EMOJI_DICT_FILE = './emoji_dict.txt'

# Convert the first character of each sentence to lowercase? True = yes, False = no
CONVERT_TO_LOWER = True

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

# split messages that are too long
#def split_message(message, max_length):
#    return [message[i:i+max_length] for i in range(0, len(message), max_length)]

""" def split_message(message, max_length):
    # Subtract the length of other parts of the IRC message from max_length
    max_length -= len("PRIVMSG {} :".format(CHANNEL)) + len("\r\n") + len(NICKNAME)
    return [message[i:i+max_length] for i in range(0, len(message), max_length)] """

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
            messages.append(current_message)
            current_message = word + " "
            current_bytes = word_bytes
    if current_message:
        messages.append(current_message)
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
                        formatted_input = f"<{timestamp}> <{sender_username}> {self.nickname}: {input_text}"
                        print("Bot should respond to all messages")
                        response = self.interact_model(self, input_text, sender_username, formatted_input)
                        print(f"Response from interact_model: {response}")
                        response_parts = split_message(response, 512)  # Split the response into parts
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
