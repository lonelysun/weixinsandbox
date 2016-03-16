# -*- coding: utf-8 -*-
##############################################################################
#  COMPANY: BONN
#  AUTHOR: KIWI
#  EMAIL: arborous@gmail.com
#  VERSION : 1.0   NEW  2015/12/12
#  UPDATE : NONE
#  Copyright (C) 2011-2016 www.mychinavip.com All Rights Reserved
##############################################################################

import re
import random
import json
import six
import time
from hashlib import sha1

string_types = (six.string_types, six.text_type, six.binary_type)

def check_token(token):
    return re.match('^[A-Za-z0-9]{3,32}$', token)


def to_text(value, encoding="utf-8"):
    if isinstance(value, six.text_type):
        return value
    if isinstance(value, six.binary_type):
        return value.decode(encoding)
    return six.text_type(value)


def to_binary(value, encoding="utf-8"):
    if isinstance(value, six.binary_type):
        return value
    if isinstance(value, six.text_type):
        return value.encode(encoding)
    return six.binary_type(value)


def is_string(value):
    return isinstance(value, string_types)


def generate_token(length=''):
    if not length:
        length = random.randint(3, 32)
    length = int(length)
    assert 3 <= length <= 32
    token = []
    letters = 'abcdefghijklmnopqrstuvwxyz' \
              'ABCDEFGHIJKLMNOPQRSTUVWXYZ' \
              '0123456789'
    for _ in range(length):
        token.append(random.choice(letters))
    return ''.join(token)


def json_loads(s):
    s = to_text(s)
    return json.loads(s)


def json_dumps(d):
    return json.dumps(d)


def pay_sign_dict(appid, pay_sign_key, add_noncestr=True, add_timestamp=True, add_appid=True, **kwargs):
    """
    支付参数签名
    """
    assert pay_sign_key, "PAY SIGN KEY IS EMPTY"
    if add_appid:
        kwargs.update({'appid': appid})
    if add_noncestr:
        kwargs.update({'noncestr': generate_token()})
    if add_timestamp:
        kwargs.update({'timestamp': int(time.time())})
    params = kwargs.items()
    _params = [(k.lower(), v) for k, v in kwargs.items() if k.lower() != "appid"] + [('appid', appid), ('appkey', pay_sign_key)]
    _params.sort()
    sign = sha1('&'.join(["%s=%s" % (str(p[0]), str(p[1])) for p in _params])).hexdigest()
    sign_type = 'SHA1'
    return dict(params), sign, sign_type


def smart_str(s, encoding='utf-8', strings_only=False, errors='strict'):
    if not isinstance(s, basestring):
        try:
            return str(s)
        except UnicodeEncodeError:
            if isinstance(s, Exception):
                return ' '.join([smart_str(arg, encoding, strings_only,
                        errors) for arg in s])
            return unicode(s).encode(encoding, errors)
    elif isinstance(s, unicode):
        return s.encode(encoding, errors)
    elif s and encoding != 'utf-8':
        return s.decode('utf-8', errors).encode(encoding, errors)
    else:
        return s

def params_filter(params):
    ks = params.keys()
    ks.sort()
    newparams = {}
    prestr = ''
    for k in ks:
        v = params[k]
        k = smart_str(k, 'utf-8')
        if k not in ('sign','sign_type') and v != '':
            newparams[k] = smart_str(v, 'utf-8')
            prestr += '%s=%s&' % (k, newparams[k])
    prestr = prestr[:-1]
    return newparams, prestr


def json2xml(json):
        string = ""
        for k, v in json.items():
            string = string + "<%s>" % (k) + str(v) + "</%s>" % (k)

        return string