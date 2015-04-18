import re
import transaction
from ..models import DBSession


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

def get_table_seq(table_name): 
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

def set_sequence(orm, seq_name):
    row = DBSession.query(orm).order_by('id DESC').first()
    last_id = row.id
    seq_name = get_table_seq(orm.__tablename__)
    sql = "SELECT setval('%s', %d)" % (seq_name, last_id)
    engine = DBSession.bind    
    engine.execute(sql)

def set_sequences(ORMs):
    for orm in ORMs:
        set_sequence(orm)
    
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
    sequences = []
    for tablename, data in fixtures: 
        table = Table(tablename, metadata, autoload=True)
        class T(Base, BaseModel):
            __table__ = table

        keys = get_pkeys(table)
        for d in data:
            filter_ = {}
            for key in keys:
                val = d[key]
                filter_[key] = val
            q = session.query(T).filter_by(**filter_)
            if q.first():
                continue
            u = T()
            u.from_dict(d)
            m = session.add(u)

        seq_name = get_table_seq(tablename)
        if seq_name:
            sequences.append((T, seq_name))
    session.commit()
    set_sequences(sequences)
