import contextlib
import enum
import json
import logging
import os.path

import sqlalchemy as sql
from sqlalchemy.ext import declarative as sql_declarative
from sqlalchemy.orm import session as sql_session

from dancebooks.config import config

_Base = sql.orm.declarative_base()


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


class BackupType(enum.StrEnum):
	nas = "nas"
	s3 = "s3"


class Backup(_Base):
	__tablename__ = "backups"
	__table_args__ = {"schema": "service"}

	id = sql.schema.Column(sql.types.BigInteger, primary_key=True)
	type = sql.schema.Column(sql.types.Enum(BackupType), default=BackupType.s3)
	path = sql.schema.Column(sql.types.String, nullable=False)
	provenance = sql.schema.Column(sql.types.String, nullable=False)
	aspect_ratio_x = sql.schema.Column(sql.types.BigInteger, nullable=False)
	aspect_ratio_y = sql.schema.Column(sql.types.BigInteger, nullable=False)
	image_size_x = sql.schema.Column(sql.types.BigInteger, nullable=False)
	image_size_y = sql.schema.Column(sql.types.BigInteger, nullable=False)
	note = sql.schema.Column(sql.types.String, nullable=False)

	@property
	def name(self):
		return os.path.basename(self.path)

_engine = sql.create_engine(
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
