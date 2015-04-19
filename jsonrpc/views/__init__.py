from datetime import datetime
from pyramid.view import view_config
from pyramid.httpexceptions import (
    HTTPFound,
    HTTPForbidden,
    )
from pyramid.security import (
    remember,
    forget,
    authenticated_userid,
    )
import hmac    
import hashlib
import base64
import transaction
import colander
from deform import (
    Form,
    ValidationFailure,
    widget,
    )
from sqlalchemy.sql.expression import text 
    
from ..models import (
    DBSession,
    User,
    CommonModel
    )

from ..tools import (
    dict_to_simple_value,
    date_from_str,
    FixLength,
    get_settings,
    split_tablename,
    DateType,
    DateTimeType,
    )
    
########
# Home #
########
@view_config(route_name='home', renderer='templates/home.pt', permission='view')
def view_home(request):
    return dict(project='jsonrpc')


#########
# Login #
#########
class Login(colander.Schema):
    username = colander.SchemaNode(colander.String())
    password = colander.SchemaNode(colander.String(),
                    widget=widget.PasswordWidget())

LIMIT = 1000
CODE_OK = 0
CODE_NOT_FOUND = -1
CODE_INVALID_LOGIN = -10

# http://deformdemo.repoze.org/interfield/
def login_validator(form, value):
    user = form.user
    if not user:
        raise colander.Invalid(form, 'Login failed')
    if not user.user_password:
        raise colander.Invalid(form, 'Login failed')        
    if not user.check_password(value['password']):
        raise colander.Invalid(form, 'Login failed')

def get_login_headers(request, user):
    headers = remember(request, user.email)
    user.last_login_date = datetime.now()
    DBSession.add(user)
    DBSession.flush()
    transaction.commit()
    return headers

@view_config(context=HTTPForbidden, renderer='templates/login.pt')
@view_config(route_name='login', renderer='templates/login.pt')
def view_login(request):
    if authenticated_userid(request):
        return HTTPFound(location=request.route_url('home'))
    schema = Login(validator=login_validator)
    form = Form(schema, buttons=('login',))
    if 'login' in request.POST: 
        controls = request.POST.items()
        identity = request.POST.get('username')
        user = schema.user = User.get_by_identity(identity)
        try:
            c = form.validate(controls)
        except ValidationFailure, e:
            request.session['login failed'] = e.render()
            return HTTPFound(location=request.route_url('login'))
        headers = get_login_headers(request, user)        
        return HTTPFound(location=request.route_url('home'),
                          headers=headers)
    elif 'login failed' in request.session:
        r = dict(form=request.session['login failed'])
        del request.session['login failed']
        return r
    return dict(form=form.render())

@view_config(route_name='logout')
def view_logout(request):
    headers = forget(request)
    return HTTPFound(location = request.route_url('home'),
                      headers = headers)    


###################
# Change password #
###################
class Password(colander.Schema):
    old_password = colander.SchemaNode(colander.String(),
                                       widget=widget.PasswordWidget())
    new_password = colander.SchemaNode(colander.String(),
                                       widget=widget.PasswordWidget())
    retype_password = colander.SchemaNode(colander.String(),
                                          widget=widget.PasswordWidget())

                                          
def password_validator(form, value):
    if not form.request.user.check_password(value['old_password']):
        raise colander.Invalid(form, 'Invalid old password.')
    if value['new_password'] != value['retype_password']:
        raise colander.Invalid(form, 'Retype mismatch.')
                                          

@view_config(route_name='password', renderer='templates/password.pt',
             permission='edit')
def view_password(request):
    schema = Password(validator=password_validator)
    form = Form(schema, buttons=('save','cancel'))
    if request.POST:
        if 'save' in request.POST:
            schema.request = request
            controls = request.POST.items()
            try:
                c = form.validate(controls)
            except ValidationFailure, e:
                request.session['invalid password'] = e.render()
                return HTTPFound(location=request.route_url('password'))
            user = request.user
            user.password = c['new_password']
            DBSession.add(user)
            DBSession.flush()
            transaction.commit()
            request.session.flash('Your password has been changed.')
        return HTTPFound(location=request.route_url('home'))
    elif 'invalid password' in request.session:
        r = dict(form=request.session['invalid password'])
        del request.session['invalid password']
        return r
    return dict(form=form.render())

############
# Base ORM #
############
class BaseORM(object): # abstract
    def __init__(self, db_base, db_session, tablename):
        db_base = db_base
        self.db_session = db_session
        schema, tablename = split_tablename(tablename)
        args = dict(autoload=True)
        if schema:
            args['schema'] = schema

        class cls(db_base, CommonModel):
            __tablename__ = tablename 
            __table_args__ = args

        self.cls = cls

    def get_count(self, q):
        r = q.first()
        page_count = r.jml / LIMIT
        if r.jml % LIMIT > 0:
            page_count += 1
        return r.jml, page_count

    def get_rows(self, q, offset=-1):
        if offset < 0:
            return q
        return q.offset(offset).limit(LIMIT)

########        
# Auth #
########
def auth(username, signature, fkey):
    settings = get_settings()
    sql = "SELECT {password} AS password FROM {table} WHERE {id} = :id"
    sql = sql.format(table=settings.auth_table, id=settings.auth_key_field,
            password=settings.auth_password_field)
    engine = DBSession.bind
    q = engine.execute(text(sql), id = username)
    user = q.first()
    if not user:
        return
    
    #utc_date = datetime.utcnow()
    #tStamp = utc_date-datetime.strptime('1970-01-01 00:00:00','%Y-%m-%d %H:%M:%S'); 
    #fkey = int(tStamp.total_seconds())

    value = "%s&%s" % (username,int(fkey)); 

    key = str(user.password)
    
    lsignature = hmac.new(key, msg=value, digestmod=hashlib.sha256).digest()
    encodedSignature = base64.encodestring(lsignature).replace('\n', '')
    
    if encodedSignature==signature:
       return user


def auth_from_rpc(request):
    user = auth(request.environ['HTTP_USERID'], request.environ['HTTP_SIGNATURE'], request.environ['HTTP_KEY'])
    if user:
        return dict(code=CODE_OK, message='OK')
    #return dict(code=CODE_OK, message='OK')
    return dict(code=CODE_INVALID_LOGIN, message='Gagal login')
            
###################        
# Table Structure #
###################
def change_column_def(c):
    if hasattr(c.type, 'precision'):
        if c.type.precision > 10:
            return Column(Float, nullable=c.nullable, name=c.name,
                    primary_key=c.primary_key)
        return Column(Integer, nullable=c.nullable, name=c.name,
                primary_key=c.primary_key)
    if hasattr(c.server_default, 'arg') and \
        hasattr(c.server_default.arg, 'text') and \
        c.server_default.arg.text.strip().lower() == 'sysdate': # Oracle
        return Column(DateTime, nullable=c.nullable, name=c.name,
            default=func.now)
    return c
        
def column_info(c):
    if c.primary_key:
        other = 'key'
    elif c.nullable:
        other = 'nullable'
    else:
        other = ''
    size = ''
    if c.type.python_type in (StringType, UnicodeType):
        typ = 'string'
        size = c.type.length
    elif c.type.python_type == IntType:
        typ = 'integer'
    elif c.type.python_type == FloatType:
        typ = 'float'
    elif c.type.python_type == DateType:
        typ = 'date'
    elif c.type.python_type == DateTimeType:
        typ = 'datetime'
    else:
        typ = c.type
    return (c.name, typ, size, other)

def table_structure(metadata, tablename):
    settings = get_settings()
    schema, tablename = split_tablename(tablename)
    t = Table(tablename, metadata, autoload=True, schema=schema)
    r = dict(table = tablename)
    cols = []
    for c in t.columns:
        c = change_column_def(c)
        info = column_info(c)
        cols.append(info)
    r['columns'] = cols
    return r
    