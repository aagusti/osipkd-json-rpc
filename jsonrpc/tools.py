import os
import re
from types import (
    StringType,
    UnicodeType,
    BooleanType,
    LongType,
    IntType,
    )
from decimal import Decimal
    
from datetime import (
    datetime,
    timedelta,
    date
    )
import locale
import pytz
from pyramid.threadlocal import get_current_registry    

kini = datetime.now()    
DateType = type(kini.date())
DateTimeType = type(kini)
TimeType = type(kini.time())
DecimalType = type(Decimal(0))

def dmy(tgl):
    return tgl.strftime('%d-%m-%Y')
    
def dmyhms(t):
    return t.strftime('%d-%m-%Y %H:%M:%S')  
    
def hms(t):
    return t.strftime('%H:%M:%S')      

def to_simple_value(v):
    typ = type(v)
    if typ is DateType:
        return v.isoformat() #dmy(v)
    if typ is DateTimeType:
        return v.isoformat() #dmyhms(v)
    if typ is TimeType:
        return hms(v)
    if typ is DecimalType:
        return float(v) 
    if typ in (LongType, IntType):
        #if v < MININT or v > MAXINT:
        return str(v)
    if v == 0:
        return '0'
    if typ in [UnicodeType, StringType]:
        return v.strip()
    if v is None:
        return ''
    return v
    
def dict_to_simple_value(d):
    r = {}
    for key in d:
        val = d[key]
        if type(key) not in (UnicodeType, StringType):
            key = str(key)
        r[key] = to_simple_value(val)
    return r
    
def date_from_str(value):
    separator = None
    value = value.split()[0] # dd-mm-yyyy HH:MM:SS  
    for s in ['-', '/']:
        if value.find(s) > -1:
            separator = s
            break    
    if separator:
        t = map(lambda x: int(x), value.split(separator))
        y, m, d = t[2], t[1], t[0]
        if d > 999: # yyyy-mm-dd
            y, d = d, y
    else: # if len(value) == 8: # yyyymmdd
        y, m, d = int(value[:4]), int(value[4:6]), int(value[6:])
    return date(y, m, d)        
    
################
# Phone number #
################
MSISDN_ALLOW_CHARS = map(lambda x: str(x), range(10)) + ['+']

def get_msisdn(msisdn, country='+62'):
    for ch in msisdn:
        if ch not in MSISDN_ALLOW_CHARS:
            return
    try:
        i = int(msisdn)
    except ValueError, err:
        return
    if not i:
        return
    if len(str(i)) < 7:
        return
    if re.compile(r'^\+').search(msisdn):
        return msisdn
    if re.compile(r'^0').search(msisdn):
        return '%s%s' % (country, msisdn.lstrip('0'))

################
# Money format #
################
def should_int(value):
    int_ = int(value)
    return int_ == value and int_ or value

def thousand(value, float_count=None):
    if float_count is None: # autodetection
        if type(value) in (IntType, LongType):
            float_count = 0
        else:
            float_count = 2
    return locale.format('%%.%df' % float_count, value, True)

def money(value, float_count=None, currency=None):
    if value < 0:
        v = abs(value)
        format_ = '(%s)'
    else:
        v = value
        format_ = '%s'
    if currency is None:
        currency = locale.localeconv()['currency_symbol']
    s = ' '.join([currency, thousand(v, float_count)])
    return format_ % s

###########    
# Pyramid #
###########    
def get_settings():
    return get_current_registry().settings
    
def get_timezone():
    settings = get_settings()
    return pytz.timezone(settings.timezone)

########    
# Time #
########
one_second = timedelta(1.0/24/60/60)
TimeZoneFile = '/etc/timezone'
if os.path.exists(TimeZoneFile):
    DefaultTimeZone = open(TimeZoneFile).read().strip()
else:
    DefaultTimeZone = 'Asia/Jakarta'

def as_timezone(tz_date):
    localtz = get_timezone()
    if not tz_date.tzinfo:
        tz_date = create_datetime(tz_date.year, tz_date.month, tz_date.day,
                                  tz_date.hour, tz_date.minute, tz_date.second,
                                  tz_date.microsecond)
    return tz_date.astimezone(localtz)    

def create_datetime(year, month, day, hour=0, minute=7, second=0,
                     microsecond=0):
    tz = get_timezone()        
    return datetime(year, month, day, hour, minute, second,
                     microsecond, tzinfo=tz)

def create_date(year, month, day):    
    return create_datetime(year, month, day)
    
def create_now():
    tz = get_timezone()
    return datetime.now(tz)
    
##############
# Fix Length #
##############
class FixLength(object):
    def __init__(self, struct):
        self.set_struct(struct)

    def set_struct(self, struct):
        self.struct = struct
        self.fields = {}
        new_struct = []
        for s in struct:
            name = s[0]
            size = s[1:] and s[1] or 1
            typ = s[2:] and s[2] or 'A' # N: numeric, A: alphanumeric
            self.fields[name] = {'value': None, 'type': typ, 'size': size}
            new_struct.append((name, size, typ))
        self.struct = new_struct

    def set(self, name, value):
        self.fields[name]['value'] = value

    def get(self, name):
        return self.fields[name]['value']
 
    def __setitem__(self, name, value):
        self.set(name, value)        

    def __getitem__(self, name):
        return self.get(name)
 
    def get_raw(self):
        s = ''
        for name, size, typ in self.struct:
            v = self.fields[name]['value']
            pad_func = typ == 'N' and right or left
            if typ == 'N':
                v = v or 0
                i = int(v)
                if v == i:
                    v = i
            else:
                v = v or ''
            s += pad_func(v, size)
        return s

    def set_raw(self, raw):
        awal = 0
        for t in self.struct:
            name = t[0]
            size = t[1:] and t[1] or 1
            akhir = awal + size
            value = raw[awal:akhir]
            if not value:
                return
            self.set(name, value)
            awal += size
        return True

    def from_dict(self, d):
        for name in d:
            value = d[name]
            self.set(name, value)
    

############
# Database #
############
def split_tablename(tablename):
    t = tablename.split('.')
    if t[1:]:
        schema = t[0]
        tablename = t[1]
    else:
        schema = None
    return schema, tablename

###########
# Pyramid #
###########
def get_settings():
    reg = get_current_registry()
    return reg.settings
