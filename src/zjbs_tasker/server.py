from redis import Redis
from rq import Queue

from zjbs_tasker.settings import settings

redis_config = settings.REDIS_HOST_PORT.split(":")
redis_connection = Redis(host=redis_config[0], port=redis_config[1])
queue = Queue(name="tasker", connection=redis_connection)
