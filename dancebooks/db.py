import contextlib
import logging
import os.path

import sqlalchemy
from sqlalchemy import schema as sql_schema
from sqlalchemy import types as sql_types
from sqlalchemy.ext import declarative as sql_declarative
from sqlalchemy.orm import session as sql_session

from dancebooks.config import config

_Base = sql_declarative.declarative_base()

class Backup(_Base):
	__tablename__ = "backups"
	__table_args__ = {"schema": "service"}

	id = sql_schema.Column(sql_types.BigInteger, primary_key=True)
	path = sql_schema.Column(sql_types.String, nullable=False)
	provenance = sql_schema.Column(sql_types.String, nullable=False)
	aspect_ratio_x = sql_schema.Column(sql_types.BigInteger, nullable=False)
	aspect_ratio_y = sql_schema.Column(sql_types.BigInteger, nullable=False)
	image_size_x = sql_schema.Column(sql_types.BigInteger, nullable=False)
	image_size_y = sql_schema.Column(sql_types.BigInteger, nullable=False)
	note = sql_schema.Column(sql_types.String, nullable=False)

	@property
	def name(self):
		return os.path.basename(self.path)

_engine = sqlalchemy.create_engine(
	config.db.connection_url,
	connect_args=config.db.options
)
_session_maker = sql_session.sessionmaker(bind=_engine)

@contextlib.contextmanager
def make_transaction():
	try:
		txn = _session_maker()
		yield txn
	except Exception:
		logging.exception("Rolling session back due to exception")
		txn.rollback()
	finally:
		txn.close()

__all__ = [Backup, make_transaction]
