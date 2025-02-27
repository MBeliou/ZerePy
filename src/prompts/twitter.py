# Twitter prompts
POST_TWEET_PROMPT = (
    "Generate an engaging tweet. Don't include any hashtags, links or emojis. Keep it under 280 characters."
    "The tweets should be pure commentary, do not shill any coins or projects apart from {agent_name}. Do not repeat any of the"
    "tweets that were given as example. Avoid the words AI and crypto.")

REPLY_TWEET_PROMPT = (
    "Generate a friendly, engaging reply to this tweet: {tweet_text}. Keep it under 280 characters. Don't include any usernames, hashtags, links or emojis. ")
