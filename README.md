# IRC Bot for OpenAI-API
Python-based simple IRC (intenet relay chat) chatroom bot that uses OpenAI API (GPT-3.5 / GPT-4).

Hey, buddy! Wanna shove that GPT-3.5 or GPT-4 OpenAI API into good'ole IRC as a chatbot? Now it's possible!

# What's new
`Aug 3, 2023 (v.029)`: Bot now supports password protected channels (i.e. to prevent public abuse).

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

# Install

1. Install the required packages with `pip install -r requirements.txt`
2. Crank your OpenAI access token into either an environment variable or into `api_token.txt` within the same directory.
3. Edit the Python file for your bot configuration. Set up things such as admin nicks etc. Change what you don't fancy into your liking.
4. Launch `python IRCbot-OpenAI-API.py` and off you go!

The bot has a chat history memory but only does API calls whenever it's addressed with lines starting with the bot's nick with a  : , so that it's not babbling with replies to every single thing that's being said. You "might" want to rate limit it on bigger channels.

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
