from dotenv import load_dotenv
load_dotenv()

import redis
import os

REDIS_URL = os.getenv('REDIS_URL')

client = redis.Redis.from_url(REDIS_URL)