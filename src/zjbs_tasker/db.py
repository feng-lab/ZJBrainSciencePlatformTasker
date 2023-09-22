import databases
import sqlalchemy

from zjbs_tasker.settings import settings

database = databases.Database(settings.DATABASE_URL)
metadata = sqlalchemy.MetaData()
