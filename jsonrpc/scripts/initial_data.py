import re
from sqlalchemy import (
    Table,
    MetaData,
    )
from sqlalchemy.orm import sessionmaker
from sqlalchemy.schema import PrimaryKeyConstraint
from sqlalchemy.sql.expression import text
import transaction
from ..models import (
    Base,
    BaseModel,
    CommonModel,
    DBSession,
    User,
    )


fixtures = [
        ('users', [
            dict(
                id=0,
                email='anonymous@local',
                user_name='anonymous',
                status=0,
                ),
            dict(
                id=1,
                email='admin@local',
                user_name='admin',
                password='admin',
                status=1,
                ),
            ]),
    ] 

SQL_TABLE = """
SELECT c.oid, n.nspname, c.relname
  FROM pg_catalog.pg_class c
  LEFT JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
  WHERE c.relname = :table_name
    AND pg_catalog.pg_table_is_visible(c.oid)
  ORDER BY 2, 3
"""

SQL_TABLE_SCHEMA = """
SELECT c.oid, n.nspname, c.relname
  FROM pg_catalog.pg_class c
  LEFT JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
  WHERE c.relname = :table_name
    AND n.nspname = :schema
  ORDER BY 2, 3
"""

SQL_FIELDS = """
SELECT a.attname,
  pg_catalog.format_type(a.atttypid, a.atttypmod),
  (SELECT substring(pg_catalog.pg_get_expr(d.adbin, d.adrelid) for 128)
     FROM pg_catalog.pg_attrdef d
     WHERE d.adrelid = a.attrelid
       AND d.adnum = a.attnum
       AND a.atthasdef),
  a.attnotnull, a.attnum,
  (SELECT c.collname
     FROM pg_catalog.pg_collation c, pg_catalog.pg_type t
     WHERE c.oid = a.attcollation
       AND t.oid = a.atttypid
       AND a.attcollation <> t.typcollation) AS attcollation,
  NULL AS indexdef,
  NULL AS attfdwoptions
  FROM pg_catalog.pg_attribute a
  WHERE a.attrelid = :table_id AND a.attnum > 0 AND NOT a.attisdropped
  ORDER BY a.attnum"""

def table_seq(table_name):
    engine = DBSession.bind
    t = table_name.split('.')
    if t[1:]:
        schema = t[0]
        table_name = t[1]
        sql = text(SQL_TABLE_SCHEMA)
        q = engine.execute(sql, schema=schema, table_name=table_name)
    else:
        sql = text(SQL_TABLE)
        q = engine.execute(sql, table_name=table_name)
    r = q.fetchone()
    table_id = r.oid
    sql = text(SQL_FIELDS)
    q = engine.execute(sql, table_id=table_id)
    regex = re.compile("nextval\('(.*)'\:")
    for r in q.fetchall():
        if not r.substring:
            continue
        if r.substring.find('nextval') == -1:
            continue
        match = regex.search(r.substring)
        return match.group(1)


def set_sequence(orm):
    row = DBSession.query(orm).order_by('id DESC').first()
    last_id = row.id
    seq_name = table_seq(orm.__table__.name)
    sql = "SELECT setval('%s', %d)" % (seq_name, last_id)
    engine = DBSession.bind
    engine.execute(sql)
    
def insert():
    engine = DBSession.bind
    tablenames = insert_(engine, fixtures)
    metadata = MetaData(engine)
    for item in fixtures:
        tablename = item[0]
        if tablename not in tablenames:
            continue
        class T(Base):
            __table__ = Table(tablename, metadata, autoload=True)
        set_sequence(T)
    transaction.commit()
    
def get_pkeys(table):
    r = []
    for c in table.constraints:
        if c.__class__ is not PrimaryKeyConstraint:
            continue
        for col in c:
            r.append(col.name)
    return r

def insert_(engine, fixtures): 
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    metadata = MetaData(engine)
    tablenames = []
    for tablename, data in fixtures:
        if tablename == 'users':
            T = User
            table = T.__table__
        else:
            table = Table(tablename, metadata, autoload=True)
            class T(Base, BaseModel, CommonModel):
                __table__ = table

        q = session.query(T).limit(1)
        if q.first():
            continue
        tablenames.append(tablename)
        keys = get_pkeys(table)
        for d in data:
            filter_ = {}
            for key in keys:
                val = d[key]
                filter_[key] = val
            q = session.query(T).filter_by(**filter_)
            if q.first():
                continue
            tbl = T()
            tbl.from_dict(d)
            if tablename == 'users' and 'password' in d:
                tbl.password = d['password']
            m = session.add(tbl)
    session.commit()
    return tablenames
