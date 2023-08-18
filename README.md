# IRC Bot for OpenAI-API
Python-based simple IRC (intenet relay chat) chatroom bot that uses OpenAI API (GPT-3.5 / GPT-4).

Wanna shove that GPT-3.5 or GPT-4 OpenAI API into good'ole IRC as a chatbot? Now it's possible!

# What's new
`Aug 3, 2023 (v.031)`: Bot now takes in admin messages as `/msg bot !command <options>` if it needs to be adjusted on the fly. Acknowledgements of bot commands come into the private msg's if you're an admin.

`Aug 3, 2023 (v.029)`: Bot now supports joining password protected channels (i.e. to prevent abuse).

`Aug 3, 2023 (v.028)`: all config now handled via `config.json`, edit that to configure the bot. Language settings also apply to the bot's output language, so no need to change everything manually anymore. New variable, `ANSWER_PROBABILITY` sets the likelihood for the bot answering when in public mode.

`Aug 3, 2023 (v.025)`: Added some increased parsing functionalities, such as utf-8/unciode emoji to ASCII conversion tables (where utf8-emojis are not supported or wanted) and a lowercase converter to make the bot "fit" better into an IRC channel's output style.

New functions:
```
# Replace unicode emojis with ASCII? True = yes, False = no
USE_EMOJI_DICT = True
```
```
# Convert the first character of each sentence to lowercase? True = yes, False = no`
CONVERT_TO_LOWER = True
```
# Prerequisites
- at least Python 3.8 or later, probably. Tested and running OK on `Python 3.9.16`
- `openai`, `jaraco.stream` and `irc` PyPi packages
- OpenAI API key (from [openai.com](https://openai.com))

# Install

1. Install the required packages with `pip install -r requirements.txt`
2. Crank your OpenAI access token into either an environment variable or into `api_token.txt` within the same directory.
3. Edit the `config.json` for your bot configuration. Set up things such as admin nicks, your bot's details, other options etc. Change whatever you deem necessary.
4. Launch `python IRCbot-OpenAI-API.py` and off you go!

The bot has a chat history memory that you can adjust in `config.json`, the `RESPOND_TO_ALL` switch set to `true` makes the bot answer to everyone on the channel, with it set to `false`, the bot only answers to people "talking to it" (with lines starting with `<botname>:`). Rate limit adjustments are extremely handy for that, use either `!ratelimit <seconds>` on the channel or as admin, `/msg <bot> !rametlimit <seconds>`.

More options & functionalities, such as token counting and improved rate limiting + fallback methods are WIP.

# Bot commands
`!ratelimit <seconds>`: This command sets the rate limit for the bot's responses. The <seconds> parameter specifies the minimum number of seconds that should pass between each response. Example usage: !ratelimit 60 would set the rate limit to one response per minute. This command can only be used by admin users, as specified in the `ADMIN_NICKNAMES` variable.
`!mute <minutes>`: This command mutes the bot for a specified number of minutes. The <minutes> parameter specifies how long the bot should remain silent. Example usage: !mute 10 would mute the bot for 10 minutes. This command can only be used by admin users, as specified in the `ADMIN_NICKNAMES` variable.
`!goaway`: This command causes the bot to leave the chatroom. This command can only be used by admin users, as specified in the `ADMIN_NICKNAMES` variable.

The bot is programmed to respond to messages that start with its nickname, followed by a colon. For instance, if the bot's nickname is `ChatKeke`, it would respond to a message like `ChatKeke: Hello!`.

Please note that the bot will not respond if it is currently muted or if the rate limit has not yet expired.

By default, the bot uses either OpenAI's GPT-3-5 or GPT-4 model (user defined) to generate responses. It keeps a history of the chatroom's conversation to provide context for its responses. The number of past interactions that the bot remembers can be adjusted by changing the `MAX_PAST_INTERACTIONS` variable.

Enjoy!

---
Brought to you by [FlyingFathead](https://github.com/FlyingFathead) & ChaosWhisperer. 

Contact: flyingfathead <|> protonmail <|> com
