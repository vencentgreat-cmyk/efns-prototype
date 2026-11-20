"""Trusted viewer identity and explicit app-username normalization."""
import re
from uuid import NAMESPACE_URL, uuid5

MAIN_SNOWFLAKE_ADMIN_USERNAME = 'EFNSDATABASE'
MAIN_ADMIN_USER_ID = str(uuid5(NAMESPACE_URL, 'efns:main-snowflake-admin:'+MAIN_SNOWFLAKE_ADMIN_USERNAME))
_USERNAME = re.compile(r'^[A-Za-z_][A-Za-z0-9_$]{0,254}$')


def normalize_snowflake_username(value, *, allow_main=False):
    from app.security import UserValidationError
    if value is None or not str(value).strip():
        return None
    if not isinstance(value,str):
        raise UserValidationError('Snowflake username must be text.')
    value=value.strip().upper()
    if not _USERNAME.fullmatch(value):
        raise UserValidationError('Snowflake username must be an unquoted user name of up to 255 letters, digits, underscores or dollar signs, starting with a letter or underscore. Use the Snowflake username, not the login email.')
    if value==MAIN_SNOWFLAKE_ADMIN_USERNAME and not allow_main:
        raise UserValidationError('The main Snowflake Admin username is reserved and does not need a User Management entry.')
    return value


def main_admin_user():
    from app.security import User, Role
    # An explicit virtual app identity, not a password, session or database user.
    return User(MAIN_ADMIN_USER_ID,MAIN_SNOWFLAKE_ADMIN_USERNAME,MAIN_SNOWFLAKE_ADMIN_USERNAME,
        Role.ADMIN,True,False,'','',None,MAIN_SNOWFLAKE_ADMIN_USERNAME)


def resolve_snowflake_username(streamlit_module=None, *, executor_factory=None, diagnostics=None):
    """Return only a trusted viewer username, never an owner-rights SQL identity.

    CURRENT_USER is attempted only through the existing executor when the
    viewer APIs are unavailable. This owner's-rights app cannot prove that
    such a SQL identity is the viewer, so that result fails closed.
    """
    details=diagnostics if diagnostics is not None else {}
    details.update(username=None,source='Unavailable',matched_entry=None)
    if streamlit_module is None:
        import streamlit as streamlit_module
    for name in ('user','experimental_user'):
        try:
            profile=getattr(streamlit_module,name)
            value=profile.get('user_name') if hasattr(profile,'get') else getattr(profile,'user_name',None)
        except Exception:
            continue
        if value is None or (isinstance(value,str) and not value.strip()):
            continue
        try:
            username=normalize_snowflake_username(value,allow_main=True)
        except Exception:
            details['source']='st.'+name+'.user_name — invalid; access denied'
            return None
        if username==MAIN_SNOWFLAKE_ADMIN_USERNAME and value!=MAIN_SNOWFLAKE_ADMIN_USERNAME:
            details['source']='st.'+name+'.user_name; reserved principal differs; access denied'
            return None
        details.update(username=username,source='st.'+name+'.user_name')
        return username
    if executor_factory is not None:
        try:
            executor=executor_factory()
            executor.query('SELECT CURRENT_USER() AS USER_NAME')
            details['source']='CURRENT_USER() — viewer scope unverified; access denied'
        except Exception:
            details['source']='Viewer APIs and existing-session identity unavailable'
    return None
