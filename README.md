# IRC Bot for OpenAI-API
Python-based simple IRC (intenet relay chat) chatroom bot that uses OpenAI API (GPT-3.5 / GPT-4).

Hey, buddy! Want to push your GPT-3.5 or GPT-4 OpenAI API using chatbot into good'ole IRC? Now it's possible!

Just install the required packages with `pip install -r requirements.txt`, crank your OpenAI access token into either an environment variable or into `api_token.txt` within the same dir, edit the Python file for your bot details and channels, and off you go!

The bot has a chat history memory but only does API calls whenever it's addressed with lines starting with the bot's nick with a  : , so that it's not babbling with replies to every single thing that's being said. You "might" want to rate limit it on bigger channels.

---
Brought to you by [FlyingFathead](https://github.com/FlyingFathead) & ChaosWhisperer. 

Contact: flyingfathead <|> protonmail <|> com
