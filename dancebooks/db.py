import contextlib
import json
import logging
import os.path

import sqlalchemy
from sqlalchemy import schema as sql_schema
from sqlalchemy import types as sql_types
from sqlalchemy.ext import declarative as sql_declarative
from sqlalchemy.orm import session as sql_session

from dancebooks.config import config

_Base = sqlalchemy.orm.declarative_base()


# Cudos to Sansha B:
# https://stackoverflow.com/questions/5022066/how-to-serialize-sqlalchemy-result-to-json
#
# Stack Overflow driven development is one honking great idea — let's do more of those!
class SqlAlchemyEncoder(json.JSONEncoder):

	def default(self, obj):
		if isinstance(obj.__class__, sql_declarative.DeclarativeMeta):
			# an SQLAlchemy class
			return {
				col.name: obj.__getattribute__(col.name)
				for col in obj.__table__.columns
			}
		else:
			# fallbak to default
			return super().default(obj)


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
