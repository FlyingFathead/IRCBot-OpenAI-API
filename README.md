# IRC Bot for OpenAI-API
Python-based simple IRC (intenet relay chat) chatroom bot that uses OpenAI API (GPT-3.5 / GPT-4).

Hey, buddy! Wanna shove that GPT-3.5 or GPT-4 OpenAI API into good'ole IRC as a chatbot? Now it's possible!

1. Just install the required packages with `pip install -r requirements.txt`
2. Crank your OpenAI access token into either an environment variable or into `api_token.txt` within the same directory.
3. Edit the Python file for your bot details and channels.
4. Launch `python IRCbot-OpenAI-API.py` and off you go!

The bot has a chat history memory but only does API calls whenever it's addressed with lines starting with the bot's nick with a  : , so that it's not babbling with replies to every single thing that's being said. You "might" want to rate limit it on bigger channels.

More options & functionalities, such as token counting and improved rate limiting + fallback methods are WIP.

---
Brought to you by [FlyingFathead](https://github.com/FlyingFathead) & ChaosWhisperer. 

Contact: flyingfathead <|> protonmail <|> com
