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
# from openerp.addons.web import http

import openerp
from openerp import SUPERUSER_ID
from openerp.http import request
from .parser import parse_open_auth_msg
from ..tools.client import Client
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
                    if redirect.info_type == 'component_verify_ticket':
                        return self.weixin_post_component_verify_ticket_event(cr, pool, uid, redirect, kw, context)
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
        return ''

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
        return 'success'

    def user_post_message_click(self, cr, pool, uid, redirect, kw, context):
        # 增加全局来控制 微信响应
        if str(redirect.id) in MsgId:
            return ''
        MsgId[str(redirect.id)] = redirect.id
        context['property'] = u'链接'
        context['property_note'] = redirect.raw
        # 创建或者更新关注着信息
        self.obj_users.create_or_update_user_by_openid(cr, SUPERUSER_ID, context['account_id'], redirect.source,
                                                       context)

        del MsgId[str(redirect.id)]
        return ''

    def user_post_message_view(self, cr, pool, uid, redirect, kw, context):
        """
        用户发来单击事件 记录到数据库
        """
        # 增加全局来控制 微信响应
        if str(redirect.id) in MsgId:
            return ''
        MsgId[str(redirect.id)] = redirect.id
        context['property'] = u'链接'
        context['property_note'] = redirect.raw
        # 创建或者更新关注着信息
        self.obj_users.create_or_update_user_by_openid(cr, SUPERUSER_ID, context['account_id'], redirect.source,
                                                       context)
        del MsgId[str(redirect.id)]
        return ''

    def user_post_message_link(self, cr, pool, uid, redirect, kw, context):
        """
        用户发来一条链接 记录到数据库
        """
        # 增加全局来控制 微信响应
        if str(redirect.id) in MsgId:
            return ''
        MsgId[str(redirect.id)] = redirect.id

        context['property'] = u'链接'
        context['property_note'] = redirect.raw
        # 创建或者更新关注着信息
        self.obj_users.create_or_update_user_by_openid(cr, SUPERUSER_ID, context['account_id'], redirect.source,
                                                       context)

        del MsgId[str(redirect.id)]
        return ''

    def user_post_message_image(self, cr, pool, uid, redirect, kw, context):
        """
        用户发来一条图片 记录到数据库
       """
        # 增加全局来控制 微信响应
        if str(redirect.id) in MsgId:
            return ''
        MsgId[str(redirect.id)] = redirect.id

        ids = self.obj_users.search(cr, SUPERUSER_ID, [('openid', '=', redirect.source),
                                                       ('weixin_account_users', '=', context['account_id'])])
        if len(ids) == 0:
            ids = self.obj_users.get_user_info(cr, SUPERUSER_ID, [], redirect.source, context=context)
            ids = [ids]
            context = {'img': redirect.img, 'media_id': redirect.MediaId}
        # 取出用户在系统的ID
        o = self.obj_users.browse(cr, SUPERUSER_ID, ids, context)
        client_o = Client(pool, cr, o.weixin_account_users.id, o.weixin_account_users.appid,
                          o.weixin_account_users.appsecret, o.weixin_account_users.access_token,
                          o.weixin_account_users.token_expires_at)
        media_id = client_o.download_media(redirect.MediaId)
        f = urllib2.urlopen(media_id.url)
        attach_vals = {
            'name': '%s' % (redirect.MediaId),
            'datas_fname': '%s.%s' % (redirect.MediaId, f.headers.subtype),
            'datas': base64.encodestring(f.read()),
            'file_type': format,
            'type_weixin': 'image',
            'account_id': o.weixin_account_users.id,
            'description': redirect.source,
            'res_model': 'dhn.weixin.users',
        }
        attachment_id = pool.get('ir.attachment').create(cr, SUPERUSER_ID, attach_vals, context)
        context['property'] = u'图片'
        context['user_pos'] = 'image'
        context['property_note'] = redirect.raw
        # img = '<img src="%s" alt="%s" />' % (redirect.img, redirect.MediaId)  # width="100%" height="100%"
        message_id = self.obj_users.message_post(cr, SUPERUSER_ID, ids,
                                                 body=(u'<span class="label label-success">图片</span><br>'),
                                                 context=context)
        parm = {
            'attachment_ids': [(4, attachment_id)],
        }
        pool.get('mail.message').write(cr, SUPERUSER_ID, message_id, parm, context=context)

        del MsgId[str(redirect.id)]

        return ''
        # *********以下是存入指定文件夹
        # context = {'img': redirect.img, 'media_id': redirect.MediaId}
        # file_path = obj.download_media_image(cr, SUPERUSER_ID, ids, context)
        # # img = '<img src="%s" alt="%s" />' % (redirect.img, redirect.MediaId)  # width="100%" height="100%"
        # img = '<img src="%s" alt="%s" />' % (file_path, redirect.MediaId)  # width="100%" height="100%"
        # context['property'] = u'图片'
        # context['property_note'] = redirect.raw
        # if obj.message_post(cr, SUPERUSER_ID, ids, body=_(u'<span class="label label-success">图片</span><br>' + img),
        # context=context) > 0:
        #     return ''

    def user_post_message_voice(self, cr, pool, uid, redirect, kw, context):
        """
        用户发来一条语音 记录到数据库
        """
        # 增加全局来控制 微信响应
        _logger.info('-----user_post_message_voice-------')
        if str(redirect.id) in MsgId:
            _logger.info('-----returt 。。。-------')
            return ''
        MsgId[str(redirect.id)] = redirect.id

        ids = self.obj_users.search(cr, SUPERUSER_ID, [('openid', '=', redirect.source),
                                                       ('weixin_account_users', '=', context['account_id'])])
        if len(ids) == 0:
            ids = self.obj_users.get_user_info(cr, SUPERUSER_ID, [], redirect.source, context=context)
            ids = [ids]
        # 取出用户在系统的ID
        context['media_id'] = redirect.media_id
        context['format'] = redirect.format
        o = self.obj_account.browse(cr, SUPERUSER_ID, context['account_id'], context)
        # _logger.info('pool')
        # _logger.info(pool)
        # _logger.info(self.pool)
        # _logge.info('pool')
        client_o = Client(pool, cr, o.id, o.appid, o.appsecret, o.access_token, o.token_expires_at)
        _logger.info('--------client_o-----------')
        media_id = client_o.download_media(redirect.media_id)
        #         _logge.info('media_id')
        _logger.info(media_id)

        f = urllib2.urlopen(media_id.url)
        _logger.info('--------f  open-----------')
        attach_vals = {
            'name': '%s' % (redirect.media_id),
            'datas_fname': '%s.%s' % (redirect.media_id, f.headers.subtype),
            'datas': base64.encodestring(f.read()),
            'file_type': format,
            'type_weixin': 'voice',
            'account_id': o.id,
            'description': redirect.source,
        }
        _logger.info('--------attach_vals-----------')
        _logger.info(attach_vals)

        attachment_id = pool.get('ir.attachment').create(cr, SUPERUSER_ID, attach_vals, context)
        context['property'] = u'语音'
        context['user_pos'] = 'voice'
        context['property_note'] = redirect.raw
        # 存入本地
        # file_path = obj.download_media_voice(cr, SUPERUSER_ID, ids, context)
        #         _logger.info( "---------------dddddd----")
        #         sa = base64.b64encode(f.read())
        #         sb = base64.encodestring(f.read())
        #         _logger.info( "--1111111-------------dddddd----")
        # _logge.info( media_id.url)
        # _logge.info( f.url)
        audio = """<audio controls="controls">
                   <source src="%s" />
                   </audio> """ % (f.url,)
        #         audio = """<audio controls>
        #                    <source src="data:audio/mp3;base64,UklGRhwMAABXQVZFZm10IBAAAAABAAEAgD4AAIA+AAABAAgAZGF0Ya4LAACAgICAgICAgICAgICAgICAgICAgICAgICAf3hxeH+AfXZ1eHx6dnR5fYGFgoOKi42aloubq6GOjI2Op7ythXJ0eYF5aV1AOFFib32HmZSHhpCalIiYi4SRkZaLfnhxaWptb21qaWBea2BRYmZTVmFgWFNXVVVhaGdbYGhZbXh1gXZ1goeIlot1k6yxtKaOkaWhq7KonKCZoaCjoKWuqqmurK6ztrO7tbTAvru/vb68vbW6vLGqsLOfm5yal5KKhoyBeHt2dXBnbmljVlJWUEBBPDw9Mi4zKRwhIBYaGRQcHBURGB0XFxwhGxocJSstMjg6PTc6PUxVV1lWV2JqaXN0coCHhIyPjpOenqWppK6xu72yxMu9us7Pw83Wy9nY29ve6OPr6uvs6ezu6ejk6erm3uPj3dbT1sjBzdDFuMHAt7m1r7W6qaCupJOTkpWPgHqAd3JrbGlnY1peX1hTUk9PTFRKR0RFQkRBRUVEQkdBPjs9Pzo6NT04Njs+PTxAPzo/Ojk6PEA5PUJAQD04PkRCREZLUk1KT1BRUVdXU1VRV1tZV1xgXltcXF9hXl9eY2VmZmlna3J0b3F3eHyBfX+JgIWJiouTlZCTmpybnqSgnqyrqrO3srK2uL2/u7jAwMLFxsfEv8XLzcrIy83JzcrP0s3M0dTP0drY1dPR1dzc19za19XX2dnU1NjU0dXPzdHQy8rMysfGxMLBvLu3ta+sraeioJ2YlI+MioeFfX55cnJsaWVjXVlbVE5RTktHRUVAPDw3NC8uLyknKSIiJiUdHiEeGx4eHRwZHB8cHiAfHh8eHSEhISMoJyMnKisrLCszNy8yOTg9QEJFRUVITVFOTlJVWltaXmNfX2ZqZ21xb3R3eHqAhoeJkZKTlZmhpJ6kqKeur6yxtLW1trW4t6+us7axrbK2tLa6ury7u7u9u7vCwb+/vr7Ev7y9v8G8vby6vru4uLq+tri8ubi5t7W4uLW5uLKxs7G0tLGwt7Wvs7avr7O0tLW4trS4uLO1trW1trm1tLm0r7Kyr66wramsqaKlp52bmpeWl5KQkImEhIB8fXh3eHJrbW5mYGNcWFhUUE1LRENDQUI9ODcxLy8vMCsqLCgoKCgpKScoKCYoKygpKyssLi0sLi0uMDIwMTIuLzQ0Njg4Njc8ODlBQ0A/RUdGSU5RUVFUV1pdXWFjZGdpbG1vcXJ2eXh6fICAgIWIio2OkJGSlJWanJqbnZ2cn6Kkp6enq62srbCysrO1uLy4uL+/vL7CwMHAvb/Cvbq9vLm5uba2t7Sysq+urqyqqaalpqShoJ+enZuamZqXlZWTkpGSkpCNjpCMioqLioiHhoeGhYSGg4GDhoKDg4GBg4GBgoGBgoOChISChISChIWDg4WEgoSEgYODgYGCgYGAgICAgX99f398fX18e3p6e3t7enp7fHx4e3x6e3x7fHx9fX59fn1+fX19fH19fnx9fn19fX18fHx7fHx6fH18fXx8fHx7fH1+fXx+f319fn19fn1+gH9+f4B/fn+AgICAgH+AgICAgIGAgICAgH9+f4B+f35+fn58e3t8e3p5eXh4d3Z1dHRzcXBvb21sbmxqaWhlZmVjYmFfX2BfXV1cXFxaWVlaWVlYV1hYV1hYWVhZWFlaWllbXFpbXV5fX15fYWJhYmNiYWJhYWJjZGVmZ2hqbG1ub3Fxc3V3dnd6e3t8e3x+f3+AgICAgoGBgoKDhISFh4aHiYqKi4uMjYyOj4+QkZKUlZWXmJmbm52enqCioqSlpqeoqaqrrK2ur7CxsrGys7O0tbW2tba3t7i3uLe4t7a3t7i3tre2tba1tLSzsrKysbCvrq2sq6qop6alo6OioJ+dnJqZmJeWlJKSkI+OjoyLioiIh4WEg4GBgH9+fXt6eXh3d3V0c3JxcG9ubWxsamppaWhnZmVlZGRjYmNiYWBhYGBfYF9fXl5fXl1dXVxdXF1dXF1cXF1cXF1dXV5dXV5fXl9eX19gYGFgYWJhYmFiY2NiY2RjZGNkZWRlZGVmZmVmZmVmZ2dmZ2hnaGhnaGloZ2hpaWhpamlqaWpqa2pra2xtbGxtbm1ubm5vcG9wcXBxcnFycnN0c3N0dXV2d3d4eHh5ent6e3x9fn5/f4CAgIGCg4SEhYaGh4iIiYqLi4uMjY2Oj5CQkZGSk5OUlJWWlpeYl5iZmZqbm5ybnJ2cnZ6en56fn6ChoKChoqGio6KjpKOko6SjpKWkpaSkpKSlpKWkpaSlpKSlpKOkpKOko6KioaKhoaCfoJ+enp2dnJybmpmZmJeXlpWUk5STkZGQj4+OjYyLioqJh4eGhYSEgoKBgIB/fn59fHt7enl5eHd3dnZ1dHRzc3JycXBxcG9vbm5tbWxrbGxraWppaWhpaGdnZ2dmZ2ZlZmVmZWRlZGVkY2RjZGNkZGRkZGRkZGRkZGRjZGRkY2RjZGNkZWRlZGVmZWZmZ2ZnZ2doaWhpaWpra2xsbW5tbm9ub29wcXFycnNzdHV1dXZ2d3d4eXl6enp7fHx9fX5+f4CAgIGAgYGCgoOEhISFhoWGhoeIh4iJiImKiYqLiouLjI2MjI2OjY6Pj46PkI+QkZCRkJGQkZGSkZKRkpGSkZGRkZKRkpKRkpGSkZKRkpGSkZKRkpGSkZCRkZCRkI+Qj5CPkI+Pjo+OjY6Njo2MjYyLjIuMi4qLioqJiomJiImIh4iHh4aHhoaFhoWFhIWEg4SDg4KDgoKBgoGAgYCBgICAgICAf4CAf39+f35/fn1+fX59fHx9fH18e3x7fHt6e3p7ent6e3p5enl6enl6eXp5eXl4eXh5eHl4eXh5eHl4eXh5eHh3eHh4d3h4d3h3d3h4d3l4eHd4d3h3eHd4d3h3eHh4eXh5eHl4eHl4eXh5enl6eXp5enl6eXp5ent6ent6e3x7fHx9fH18fX19fn1+fX5/fn9+f4B/gH+Af4CAgICAgIGAgYCBgoGCgYKCgoKDgoOEg4OEg4SFhIWEhYSFhoWGhYaHhoeHhoeGh4iHiIiHiImIiImKiYqJiYqJiouKi4qLiouKi4qLiouKi4qLiouKi4qLi4qLiouKi4qLiomJiomIiYiJiImIh4iIh4iHhoeGhYWGhYaFhIWEg4OEg4KDgoOCgYKBgIGAgICAgH+Af39+f359fn18fX19fHx8e3t6e3p7enl6eXp5enl6enl5eXh5eHh5eHl4eXh5eHl4eHd5eHd3eHl4d3h3eHd4d3h3eHh4d3h4d3h3d3h5eHl4eXh5eHl5eXp5enl6eXp7ent6e3p7e3t7fHt8e3x8fHx9fH1+fX59fn9+f35/gH+AgICAgICAgYGAgYKBgoGCgoKDgoOEg4SEhIWFhIWFhoWGhYaGhoaHhoeGh4aHhoeIh4iHiIeHiIeIh4iHiIeIiIiHiIeIh4iHiIiHiIeIh4iHiIeIh4eIh4eIh4aHh4aHhoeGh4aHhoWGhYaFhoWFhIWEhYSFhIWEhISDhIOEg4OCg4OCg4KDgYKCgYKCgYCBgIGAgYCBgICAgICAgICAf4B/f4B/gH+Af35/fn9+f35/fn1+fn19fn1+fX59fn19fX19fH18fXx9fH18fXx9fH18fXx8fHt8e3x7fHt8e3x7fHt8e3x7fHt8e3x7fHt8e3x7fHt8e3x8e3x7fHt8e3x7fHx8fXx9fH18fX5+fX59fn9+f35+f35/gH+Af4B/gICAgICAgICAgICAgYCBgIGAgIGAgYGBgoGCgYKBgoGCgYKBgoGCgoKDgoOCg4KDgoOCg4KDgoOCg4KDgoOCg4KDgoOCg4KDgoOCg4KDgoOCg4KDgoOCg4KDgoOCg4KDgoOCg4KCgoGCgYKBgoGCgYKBgoGCgYKBgoGCgYKBgoGCgYKBgoGCgYKBgoGCgYKBgoGBgYCBgIGAgYCBgIGAgYCBgIGAgYCBgIGAgYCBgIGAgYCAgICBgIGAgYCBgIGAgYCBgIGAgYCBgExJU1RCAAAASU5GT0lDUkQMAAAAMjAwOC0wOS0yMQAASUVORwMAAAAgAAABSVNGVBYAAABTb255IFNvdW5kIEZvcmdlIDguMAAA" />
        #                    </audio> """
        # _logge.info(audio)
        _logger.info("--------will---in----message_post----")
        message_id = self.obj_users.message_post(cr, SUPERUSER_ID, ids,
                                                 body=(
                                                     u'<span class="label label-info">语1音</span> <br>' + audio),
                                                 context=context)
        # _logge.info( "--333333-------------dddddd----")
        parm = {
            'attachment_ids': [(4, attachment_id)],
        }
        pool.get('mail.message').write(cr, SUPERUSER_ID, message_id, parm)

        del MsgId[str(redirect.id)]
        t = int(time.time())
        reply2 = reply.TextReply(redirect, content="aa加密了么？", time=t)
        #         reply2 = reply.TransferCustomerServiceReply(redirect, time=t)
        _logger.info("dddd")

        _logger.info(reply2.render())
        token = 'watchword'
        encodingAESKey = 'jb4CLcLln4fbXRS4O4uUvD42a9cpPuYIEVk1ZdACd4w'
        appid = 'wxb817de12da86b9b4'
        nonce = kw['nonce']
        encryp_test = WXBizMsgCrypt(token, encodingAESKey, appid)
        ret, encrypt_xml = encryp_test.EncryptMsg(str(reply2.render()), nonce)
        _logger.info(encrypt_xml)
        return encrypt_xml

    def user_post_message_video(self, cr, pool, uid, redirect, kw, context):
        """
        用户发来一条视频 记录到数据库
        """
        ids = self.obj_users.search(cr, SUPERUSER_ID, [('openid', '=', redirect.source),
                                                       ('weixin_account_users', '=', context['account_id'])])
        if len(ids) > 0:
            # instructors = obj.browse(cr, SUPERUSER_ID, ids[0])
            context = {'media_id': redirect.media_id, 'ThumbMediaId': redirect.thumb_media_id}
            # format
            file_path = self.obj_users.download_media_video(cr, SUPERUSER_ID, ids, context)
            # _logge.info(file_path)
            video = """<video width="320" height="240" controls="controls">
              <source src="%s" type="video/mp4">
               Your browser does not support the video tag.
               </video> """ % (file_path,)
            context['property'] = u'视频'
            context['property_note'] = redirect.raw
            if self.obj_users.message_post(cr, SUPERUSER_ID, ids, body=_(
                            u'<span class="label label-warning">视频</span>' + video),
                                           context=context) > 0:
                return ''
        else:
            self.add_user(request, redirect, kw)
            ids = self.obj_users.search(cr, SUPERUSER_ID, [('openid', '=', redirect.source)], context=context)
            context = {'media_id': redirect.media_id, 'ThumbMediaId': redirect.thumb_media_id}
            # format
            file_path = self.obj_users.download_media_video(cr, SUPERUSER_ID, ids, context)
            # _logge.info(file_path)
            video = """<video width="320" height="240" controls="controls">
              <source src="%s" type="video/mp4">
               Your browser does not support the video tag.
               </video> """ % (file_path,)
            context['property'] = u'视频'
            context['property_note'] = redirect.raw
            if self.obj_users.message_post(cr, SUPERUSER_ID, ids, body=_(
                            u'<span class="label label-warning">视频</span>' + video),
                                           context=context) > 0:
                return ''
        return ''

    def user_post_message_shortvideo(self, cr, pool, uid, redirect, kw, context):
        """
        用户发来一条小视频 记录到数据库
        """
        ids = self.obj_users.search(cr, SUPERUSER_ID, [('openid', '=', redirect.source),
                                                       ('weixin_account_users', '=', context['account_id'])])
        if len(ids) > 0:
            # instructors = obj.browse(cr, SUPERUSER_ID, ids[0])
            context = {'media_id': redirect.media_id, 'ThumbMediaId': redirect.thumb_media_id}
            # format
            file_path = self.obj_users.download_media_video(cr, SUPERUSER_ID, ids, context)
            # _logge.info(file_path)
            video = """<video width="320" height="240" controls="controls">
              <source src="%s" type="video/mp4">
               Your browser does not support the video tag.
               </video> """ % (file_path,)
            context['property'] = u'小视频'
            context['property_note'] = redirect.raw
            if self.obj_users.message_post(cr, SUPERUSER_ID, ids, body=_(
                            u'<span class="label label-warning">小视频</span>' + video),
                                           context=context) > 0:
                return ''
        else:
            self.add_user(request, redirect, kw)
            ids = self.obj_users.search(cr, SUPERUSER_ID, [('openid', '=', redirect.source)], context=context)
            context = {'media_id': redirect.media_id, 'ThumbMediaId': redirect.thumb_media_id}
            # format
            file_path = self.obj_users.download_media_video(cr, SUPERUSER_ID, ids, context)
            # _logge.info(file_path)
            video = """<video width="320" height="240" controls="controls">
              <source src="%s" type="video/mp4">
               Your browser does not support the video tag.
               </video> """ % (file_path,)
            context['property'] = u'小视频'
            context['property_note'] = redirect.raw
            if self.obj_users.message_post(cr, SUPERUSER_ID, ids, body=_(
                            u'<span class="label label-warning">小视频</span>' + video),
                                           context=context) > 0:
                return ''
        return ''

    def user_post_message_location(self, cr, pool, uid, redirect, kw, context):
        """
        用户发来一条位置信息 记录到数据库
        """
        # 增加全局来控制 微信响应
        if str(redirect.id) in MsgId:
            return ''
        MsgId[str(redirect.id)] = redirect.id

        ids = self.obj_users.search(cr, SUPERUSER_ID, [('openid', '=', redirect.source),
                                                       ('weixin_account_users', '=', context['account_id'])])
        if len(ids) == 0:
            ids = self.obj_users.get_user_info(cr, SUPERUSER_ID, [], redirect.source, context=context)
            ids = [ids]
        try:
            property = u'<span class="label label-danger">上报位置</span>'
            map = u' <a href="http://apis.map.qq.com/uri/v1/geocoder?coord=%s,%s" target="_blank"><span class="label label-info">点我定位</span></a> ' % (
                redirect.location[0], redirect.location[1])
            location_name = """ 地理位置信息: %s""" % redirect.label
            location_x_y = """<br>地理位置维度: %s \n地理位置维度经度: %s """ % (
                str(redirect.location[0]), str(redirect.location[1]))
            location = property + location_name + map + location_x_y
            context['property'] = u'上报位置'
            context['property_note'] = redirect.raw
            self.obj_users.message_post(cr, SUPERUSER_ID, ids, body=_(location), context=context)


        except Exception, e:
            _logger.info(e.message)
        finally:
            del MsgId[str(redirect.id)]
            return ''

    def user_post_message_subscribe_unsubscribe(self, cr, pool, uid, redirect, kw, context):
        """
        用户关注 关注新建，取消关注更新 记录到数据库
         """
        # 增加全局来控制 微信响应
        if str(redirect.id) in MsgId:
            return ''
        MsgId[str(redirect.id)] = redirect.id

        ids = self.obj_users.search(cr, SUPERUSER_ID, [('openid', '=', redirect.source),
                                                       ('weixin_account_users', '=', context['account_id'])])

        domain = [('appid', '=', kw['app_id'])]
        records = self.obj_account.search_read(cr, openerp.SUPERUSER_ID, domain,
                                               ['name', 'appid', 'appsecret', 'access_token', 'token_expires_at'],
                                               context=context)[0]
        context['account_id'] = records['id']
        if redirect.type == 'subscribe':
            if len(ids) > 0:
                context['property'] = u'感谢您再次关注'
                context['property_note'] = redirect.raw
                self.obj_users.get_user_info(cr, SUPERUSER_ID, ids, redirect.source, context=context)
            else:
                self.obj_users.get_user_info(cr, SUPERUSER_ID, [], redirect.source, context=context)
                context['property'] = u'欢迎关注'
                context['property_note'] = redirect.raw
            # 发送一条关注信息
            client_obj = Client(pool, cr, records['id'], records['appid'], records['appsecret'],
                                records['access_token'], records['token_expires_at'])
            client_obj.send_text_message(redirect.source, context['property'])
            del MsgId[str(redirect.id)]
            return ''
        if redirect.type == 'unsubscribe':
            if len(ids) > 0:
                parm = {
                    'subscribe': False,
                }
                self.obj_users.write(cr, SUPERUSER_ID, ids, parm, context)
                context['property'] = u'取消关注'
                context['property_note'] = redirect.raw
                self.obj_users.message_post(cr, SUPERUSER_ID, ids,
                                            body=_(u'<span class="label label-primary">取消关注</span> ' + u"感谢您下次关注!"),
                                            context=context)
                return ''
        return ''
