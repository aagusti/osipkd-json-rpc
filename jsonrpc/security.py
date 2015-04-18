from pyramid.security import authenticated_userid
from .models import (
    User,
    UserGroup,
    Group,
    DBSession,
    )

def group_finder(login, request):
    u = User.get_by_identity(login)
    if not u or not u.status:
        return # None means logout
    if u.id == 1:
        return ['Admin']
    r = []        
    for group_id in UserGroup.get_by_user(u):
        group = DBSession.query(Group).get(group_id)
        r.append(group.group_name)
    return r
        
def get_user(request):
    username = authenticated_userid(request)
    if not username:
        return
    return User.get_by_identity(username)
