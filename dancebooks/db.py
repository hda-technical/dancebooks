import sqlalchemy
from sqlalchemy import schema as sql_schema
from sqlalchemy import types as sql_types
from sqlalchemy.ext import declarative as sql_declarative
from sqlalchemy.orm import session as sql_session

from dancebooks.config import config

_Base = sql_declarative.declarative_base()

class Backup(_Base):
	__tablename__ = "service.backups"
	
	id = sql_schema.Column(sql_types.BigInteger, primary_key=True)
	path = sql_schema.Column(sql_types.String, nullable=False)
	provenance = sql_schema.Column(sql_types.String, nullable=False)
	aspect_ratio_x = sql_schema.Column(sql_types.BigInteger, nullable=False)
	aspect_ratio_y = sql_schema.Column(sql_types.BigInteger, nullable=False)
	image_size_x = sql_schema.Column(sql_types.BigInteger, nullable=False)
	image_size_y = sql_schema.Column(sql_types.BigInteger, nullable=False)
	note = sql_schema.Column(sql_types.String, nullable=False)

_engine = sqlalchemy.create_engine(config.db.connection_url)
_session_maker = sql_session.sessionmaker(bind=_engine)

def make_transaction():
	return _session_maker()

__all__ = [Backup, make_transaction]