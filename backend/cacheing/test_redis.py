import os
import redis
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

REDIS_URL = os.getenv("REDIS_URL")

if not REDIS_URL:
    raise EnvironmentError("REDIS_URL is not set in the environment")

print(f"Connecting to Redis at: {REDIS_URL}")

client = redis.from_url(REDIS_URL, decode_responses=True)

# Ping
pong = client.ping()
print(f"PING: {'OK' if pong else 'FAILED'}")

# Set/Get round-trip
client.set("glp:test_key", "hello_redis", ex=30)
value = client.get("glp:test_key")
print(f"SET/GET: {'OK' if value == 'hello_redis' else f'FAILED (got {value!r})'}")

# Cleanup
client.delete("glp:test_key")
print("Connection test complete.")