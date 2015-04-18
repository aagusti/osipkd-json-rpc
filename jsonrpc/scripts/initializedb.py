import os
import sys
import transaction

from sqlalchemy import engine_from_config

from pyramid.paster import (
    get_appsettings,
    setup_logging,
    )

from ..models import (
    init_model,
    DBSession,
    Base,
    )
    
import initial_data


ALEMBIC_CONF = """    
[alembic]
script_location = ziggurat_foundations:migrations
sqlalchemy.url = {{db_url}}

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
"""    
    


def usage(argv):
    cmd = os.path.basename(argv[0])
    print('usage: %s <config_uri>\n'
          '(example: "%s development.ini")' % (cmd, cmd))
    sys.exit(1)


def main(argv=sys.argv):
    if len(argv) != 2:
        usage(argv)
    config_uri = argv[1]
    setup_logging(config_uri)
    settings = get_appsettings(config_uri)
    # Create Ziggurat tables
    alembic_ini_file = 'alembic.ini'
    if not os.path.exists(alembic_ini_file):
        alembic_ini = ALEMBIC_CONF.replace('{{db_url}}',
                                           settings['sqlalchemy.url'])
        f = open(alembic_ini_file, 'w')
        f.write(alembic_ini)
        f.close()
    bin_path = os.path.split(sys.executable)[0]
    alembic_bin = os.path.join(bin_path, 'alembic')
    command = '%s upgrade head' % alembic_bin
    os.system(command)
    os.remove(alembic_ini_file)
    # Insert data
    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)
    init_model()
    initial_data.insert()
