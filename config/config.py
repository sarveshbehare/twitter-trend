import os
from dotenv import load_dotenv

load_dotenv()

# MongoDB configuration
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
DB_NAME = 'twitter_trends'
COLLECTION_NAME = 'trends'

# Twitter credentials
TWITTER_USERNAME = os.getenv('TWITTER_USERNAME')
TWITTER_PASSWORD = os.getenv('TWITTER_PASSWORD')

# Twitter URLs
TWITTER_LOGIN_URL = 'https://twitter.com/login'
TWITTER_HOME_URL = 'https://twitter.com/home'