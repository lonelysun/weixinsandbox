# -*- coding: utf-8 -*-
##############################################################################
#  AUTHOR: SongHb
#  EMAIL: songhaibin1990@gmail.com
#  VERSION : 1.0   NEW  2016-03-18 15:35:50
#  UPDATE : NONE
#  Copyright (C) 2011-2016 www.wevip.com All Rights Reserved
##############################################################################
import hashlib
import json
import logging
import os
import re
import uuid
import time
import werkzeug.utils
import werkzeug.wrappers
from mako import exceptions
from mako.lookup import TemplateLookup
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT

# from openerp.addons.web import http

import openerp
from openerp import SUPERUSER_ID
from openerp.http import request
from .parser import parse_open_auth_msg
from .open_client import OpenWXClient

from openerp import http
import base64
import urllib2
from ..tools.WXBizMsgCrypt import WXBizMsgCrypt

MsgId = {}

_logger = logging.getLogger(__name__)

token = 'spamtest'


class Open_Weixin(http.Controller):
    @http.route(['/wx_auth_event_notify',
                 '/wx_auth_event_notify/<string:db>/<string:app_id>',
                 '/wx_auth_event_notify/<string:db>/<string:app_id>?signature=<string:signature>&timestamp=<string:timestamp>&nonce=<string:nonce>&encrypt_type=<string:encrypt_type>&msg_signature=<string:msg_signature>',
                 ], type='http', auth="none", csrf=False)
    def wx_auth_event_notify(self, db=None, app_id=None, signature=None, timestamp=None, nonce=None, encrypt_type=None,
                             msg_signature=None, **kw):
        _logger.info("--------wx_auth_event_notify---in--------")
        if db and signature and timestamp and nonce:
            kw['db'] = db
            kw['signature'] = signature
            kw['timestamp'] = timestamp
            kw['nonce'] = nonce
            kw['encrypt_type'] = encrypt_type
            kw['msg_signature'] = msg_signature
            request.session.db = db

            if self.check_signature(signature, timestamp, nonce):
                cr, uid, context, pool = request.cr, openerp.SUPERUSER_ID, request.context, request.registry
                domain = [('app_id', '=', app_id)]
                records = request.registry['tl.open.weixin.app'].search_read(cr, uid, domain,
                                                                             ['name', 'encoding_AES_key',
                                                                              'last_encoding_AES_key'],
                                                                             context=context)
                encoding_AES_key = ''
                last_encoding_AES_key = ''
                if records:
                    context['account_id'] = records[0]['id']
                    encoding_AES_key = records[0]['encoding_AES_key']
                    context['encoding_AES_key'] = encoding_AES_key
                    last_encoding_AES_key = records[0]['last_encoding_AES_key']
                    context['encoding_AES_key'] = last_encoding_AES_key
                    context['type'] = 'open_weixin'
                else:
                    _logger.error(u'开放平台表种没有与%s对应的配置' % app_id)
                    assert records
                from_xml = request.httprequest.data
                decrypt_odj = WXBizMsgCrypt(token, encoding_AES_key, app_id)
                ret, decryp_xml = decrypt_odj.DecryptMsg(from_xml, msg_signature, timestamp, nonce)
                if ret == 0:
                    redirect = parse_open_auth_msg(decryp_xml)
                    print redirect
                elif ret == -40005:
                    # 如果是-40005(WXBizMsgCrypt_ValidateAppid_Error) 错误 则将使用上次设置的encoding_AES_key尝试解密
                    decrypt_odj = WXBizMsgCrypt(token, last_encoding_AES_key, app_id)
                    ret, decryp_xml = decrypt_odj.DecryptMsg(from_xml, msg_signature, timestamp, nonce)
                    redirect = parse_open_auth_msg(decryp_xml)
                else:
                    _logger.error('---WXBizMsgCrypt DecryptMsg Error Code: %s---' % ret)
                if ret == 0:
                    # 推送component_verify_ticket
                    if redirect.info_type == 'component_verify_ticket':
                        return self.weixin_post_component_verify_ticket_event(cr, pool, uid, redirect, kw, context)
                    # 授权成功通知
                    if redirect.info_type == 'authorized':
                        return self.weixin_post_authorized_event(cr, pool, uid, redirect, kw, context)
        return ''

    @http.route(['/wx_auth/<string:db>',
                 # '/wx_auth/<string:db>/<string:app_id>',
                 # '/wx_auth/<string:db>/<string:app_id>?signature=<string:signature>&timestamp=<string:timestamp>&nonce=<string:nonce>&encrypt_type=<string:encrypt_type>&msg_signature=<string:msg_signature>',
                 ], type='http', auth="none", csrf=False)
    # def wx_auth_callback(self, db=None, app_id=None, signature=None, timestamp=None, nonce=None, encrypt_type=None,
    #                          msg_signature=None, **kw):
    def wx_auth_callback(self, db=None, **kw):
        _logger.info("--------wx_auth_callback---in--------")
        if db:
            kw['db'] = db
            # kw['signature'] = signature
            # kw['timestamp'] = timestamp
            # kw['nonce'] = nonce
            # kw['encrypt_type'] = encrypt_type
            # kw['msg_signature'] = msg_signature
            request.session.db = db
            print request.httprequest.data
            print kw

        # if db and signature and timestamp and nonce:
        #     kw['db'] = db
        #     kw['signature'] = signature
        #     kw['timestamp'] = timestamp
        #     kw['nonce'] = nonce
        #     kw['encrypt_type'] = encrypt_type
        #     kw['msg_signature'] = msg_signature
        #     request.session.db = db
        #
        #     if self.check_signature(signature, timestamp, nonce):
        #         cr, uid, context, pool = request.cr, openerp.SUPERUSER_ID, request.context, request.registry
        #         domain = [('app_id', '=', app_id)]
        #         records = request.registry['tl.open.weixin.app'].search_read(cr, uid, domain,
        #                                                                      ['name', 'encoding_AES_key',
        #                                                                       'last_encoding_AES_key'],
        #                                                                      context=context)
        #         encoding_AES_key = ''
        #         last_encoding_AES_key = ''
        #         if records:
        #             context['account_id'] = records[0]['id']
        #             encoding_AES_key = records[0]['encoding_AES_key']
        #             context['encoding_AES_key'] = encoding_AES_key
        #             last_encoding_AES_key = records[0]['last_encoding_AES_key']
        #             context['encoding_AES_key'] = last_encoding_AES_key
        #             context['type'] = 'open_weixin'
        #         else:
        #             _logger.error(u'开放平台表种没有与%s对应的配置' % app_id)
        #             assert records
        #         from_xml = request.httprequest.data
        #         decrypt_odj = WXBizMsgCrypt(token, encoding_AES_key, app_id)
        #         ret, decryp_xml = decrypt_odj.DecryptMsg(from_xml, msg_signature, timestamp, nonce)
        #         if ret == 0:
        #             redirect = parse_open_auth_msg(decryp_xml)
        #         elif ret == -40005:
        #             # 如果是-40005(WXBizMsgCrypt_ValidateAppid_Error) 错误 则将使用上次设置的encoding_AES_key尝试解密
        #             decrypt_odj = WXBizMsgCrypt(token, last_encoding_AES_key, app_id)
        #             ret, decryp_xml = decrypt_odj.DecryptMsg(from_xml, msg_signature, timestamp, nonce)
        #             redirect = parse_open_auth_msg(decryp_xml)
        #         else:
        #             _logger.error('---WXBizMsgCrypt DecryptMsg Error Code: %s---' % ret)
        #         if ret == 0 and redirect.info_type == 'component_verify_ticket':
        #             return self.weixin_post_component_verify_ticket_event(cr, pool, uid, redirect, kw, context)
        return u'授权成功'

    def check_signature(self, signature, timestamp, nonce):
        """
        验证消息真实性
        :param selp:
        :param signature:
        :param timestamp:
        :param nonce:
        :return:
        """
        L = [timestamp, nonce, token]
        L.sort()
        s = L[0] + L[1] + L[2]

        return hashlib.sha1(s).hexdigest() == signature

    def weixin_post_component_verify_ticket_event(self, cr, pool, uid, redirect, kw, context):
        """
         微信推送component_verify_ticket,记录到数据库
        """
        if str(redirect.create_time) + 'component_verify_ticket' in MsgId:
            return 'success'
        MsgId[str(redirect.create_time) + 'component_verify_ticket'] = redirect.create_time
        vals = {'component_verify_ticket': redirect.component_verify_ticket}
        request.registry['tl.open.weixin.app'].write(cr, uid, context['account_id'], vals, context=context)
        _logger.info('----component_verify_ticket field values successfully written-----')
        del MsgId[str(redirect.create_time) + 'component_verify_ticket']
        return 'success'

    def weixin_post_authorized_event(self, cr, pool, uid, redirect, kw, context):
        """
         授权成功通知
        """
        if str(redirect.create_time) + 'authorized' in MsgId:
            return 'success'
        MsgId[str(redirect.create_time) + 'authorized'] = redirect.create_time
        wx_open_obj = request.registry['tl.open.weixin.app']
        o = wx_open_obj.browse(cr, uid, context['account_id'], context=context)

        client_obj = OpenWXClient(pool, cr, o.id, o.app_id, o.app_secret,
                                  o.component_verify_ticket, o.component_access_token, o.token_expires_at)
        json = client_obj.api_query_auth(redirect.authorization_code)
        if "errcode" in json:
            _logger.warn(u"获取授权信息失败，%s[%s]" % (json["errmsg"], json["errcode"]))
        else:
            authorization_info = json["authorization_info"],
            authorizer_appid = authorization_info['authorizer_appid']
            authorizer_access_token = authorization_info['authorizer_access_token']
            authorizer_refresh_token = authorization_info['authorizer_refresh_token']
            func_info = authorization_info['func_info']
            expires_in = time.localtime(int(time.time()) + authorization_info.get("expires_in", 0))
            expires_at = time.strftime(DEFAULT_SERVER_DATETIME_FORMAT, expires_in)

            vals = {
                'component_access_token': json["authorization_info"],
                'date_token': datetime.now(),
                'token_expires_at': expires_at,
            }
            self.write(cr, uid, ids, vals)
        # vals = {'component_verify_ticket': redirect.component_verify_ticket}
        # request.registry['tl.open.weixin.app'].write(cr, uid, context['account_id'], vals, context=context)
        _logger.info('----authorized successfully processed-----')
        del MsgId[str(redirect.create_time) + 'authorized']
        return 'success'
