# -*- coding:utf-8 -*-
import hashlib
import json
import logging
import os
import re
import uuid
import werkzeug.utils
import werkzeug.wrappers
from mako import exceptions
from mako.lookup import TemplateLookup
# from openerp.addons.web import http
import openerp
from openerp import SUPERUSER_ID
from openerp.http import request
from parser import parse_user_msg
from ..tools.client import Client
from openerp import http
import base64
import urllib2
import urllib
from ..tools.WXBizMsgCrypt import WXBizMsgCrypt
from openerp.tools.translate import _
import time,datetime,calendar
import boto3,os
from PIL import Image, ImageFont, ImageDraw
from openerp import tools
import cStringIO


MsgId = {}

_logger = logging.getLogger(__name__)


class Home(http.Controller):
    @http.route(['/wxapi',
                 '/wxapi/<string:db>/<string:app_id>',
                 '/wxapi/<string:db>/<string:app_id>?signature=<string:signature>&timestamp=<string:timestamp>&nonce=<string:nonce>',
                 ], type='http', auth="none", csrf=False)
    def WX_api(self, db=None, app_id=None, signature=None, timestamp=None, nonce=None, **kw):
        _logger.info("--------weinxin---in--------")
        if db and app_id and signature and timestamp and nonce:
            kw['db'] = db
            kw['app_id'] = app_id
            kw['signature'] = signature
            kw['timestamp'] = timestamp
            kw['nonce'] = nonce
            request.session.db = db
            self.obj_users = request.registry['tl.weixin.users']
            self.obj_account = request.registry['tl.weixin.app']
            #历史消息
            self.obj_message_history = request.registry['tl.weixin.msg.history']
            if self.check_signature(signature, timestamp, nonce):
                redirect = parse_user_msg(request.httprequest.data)
                cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
                domain = [('appid', '=', app_id)]
                records = self.obj_account.search_read(cr, openerp.SUPERUSER_ID, domain, ['name'], context=context)
                if records:
                    context['account_id'] = records[0]['id']
                    context['type'] = 'weixin'
                else:
                    _logger.error(u'没有对应的记录')
                    assert records
                if redirect is None:
                    return kw['echostr']
                # 文本消息
                if redirect.type == 'text':
                    return self.user_post_message_text(cr, pool, uid, redirect, kw, context)
                # 图片消息
                if redirect.type == 'image':
                    return self.user_post_message_image(cr, pool, uid, redirect, kw, context)
                # 语音消息
                if redirect.type == 'voice':
                    return self.user_post_message_voice(cr, pool, uid, redirect, kw, context)
                # 视频消息
                if redirect.type == 'video':
                    return self.user_post_message_video(cr, pool, uid, redirect, kw, context)
                # 小视频消息
                if redirect.type == 'shortvideo':
                    return self.user_post_message_shortvideo(cr, pool, uid, redirect, kw, context)
                # 地理位置消息
                if redirect.event == 'location':
                    return self.user_post_message_location(cr, pool, uid, redirect, kw, context)
                # 链接消息
                if redirect.event == 'link':
                    return self.user_post_message_link(cr, pool, uid, redirect, kw, context)
                # 关注/取消关注事件
                if redirect.event in ['subscribe', 'unsubscribe']:
                    return self.user_post_message_subscribe_unsubscribe(cr, pool, uid, redirect, kw, context)
                # 链接消息、点击菜单拉取消息时的事件推送
                if redirect.event == 'click':
                    return self.user_post_message_click(cr, pool, uid, redirect, kw, context)
                # 点击菜单跳转链接时的事件推送
                if redirect.event == 'view':
                    return self.user_post_message_view(cr, pool, uid, redirect, kw, context)
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
        L = [timestamp, nonce, 'watchword']
        L.sort()
        s = L[0] + L[1] + L[2]

        return hashlib.sha1(s).hexdigest() == signature

    def user_post_message_text(self, cr, pool, uid, redirect, kw, context):
        """
        用户发来一条短信 记录到数据库
        """
        # 增加全局来控制 微信响应
        if str(redirect.id) in MsgId:
            return ''
        MsgId[str(redirect.id)] = redirect.id
        context['property'] = u'文本'
        context['property_note'] = redirect.raw
        # 创建或者更新关注着信息
        self.obj_users.create_or_update_user_by_openid(cr, SUPERUSER_ID, context['account_id'], redirect.source,
                                                       context)
        context['msg_id'] = redirect.id
        val = {
            'to_user_name': redirect.target,
            'from_user_name': redirect.source,
            'create_time': redirect.time,
            'msg_type': redirect.type,
            'xml_content': redirect.raw,
            'content': redirect.content,
            'msg_id': redirect.id,
            'app_id': context['account_id']
        }
        self.obj_message_history.create(cr, SUPERUSER_ID, val,context)
        del MsgId[str(redirect.id)]
        return ''

    def user_post_message_click(self, cr, pool, uid, redirect, kw, context):
        # 增加全局来控制 微信响应
        event_id = redirect.source+str(redirect.time)
        if event_id in MsgId:
            return ''
        MsgId[event_id] = event_id
        context['property'] = u'链接'
        context['property_note'] = redirect.raw
        # 创建或者更新关注着信息
        self.obj_users.create(cr, SUPERUSER_ID, context['account_id'], redirect.source,
                                                       context)
        val = {
            'to_user_name': redirect.target,
            'from_user_name': redirect.source,
            'create_time': redirect.time,
            'msg_type': redirect.event,
            'xml_content': redirect.raw,
            'event_key':redirect.eventkey,
            'msg_event_id':event_id,
            'app_id': context['account_id']
        }
        self.obj_message_history.create(cr, SUPERUSER_ID, val,context)
        del MsgId[str(redirect.id)]
        return ''

    def user_post_message_view(self, cr, pool, uid, redirect, kw, context):
        """
        用户发来单击事件 记录到数据库
        """
        # 增加全局来控制 微信响应
        event_id = redirect.source+str(redirect.time)
        if event_id in MsgId:
            return ''
        MsgId[event_id] = event_id
        context['property'] = u'链接'
        context['property_note'] = redirect.raw
        # 创建或者更新关注着信息
        self.obj_users.create_or_update_user_by_openid(cr, SUPERUSER_ID, context['account_id'], redirect.source, context)
        val = {
            'to_user_name': redirect.target,
            'from_user_name': redirect.source,
            'create_time': redirect.time,
            'msg_type': redirect.event,
            'xml_content': redirect.raw,
            'event_key':redirect.eventkey,
            'msg_event_id':event_id,
            'app_id': context['account_id']
        }
        self.obj_message_history.create(cr, SUPERUSER_ID, val,context)
        del MsgId[str(redirect.id)]
        return ''

    def user_post_message_link(self, cr, pool, uid, redirect, kw, context):
        """
        用户发来一条链接 记录到数据库
        """
        # 增加全局来控制 微信响应
        event_id = redirect.source+str(redirect.time)
        if event_id in MsgId:
            return ''
        MsgId[event_id] = event_id

        context['property'] = u'链接'
        context['property_note'] = redirect.raw
        # 创建或者更新关注着信息
        self.obj_users.create_or_update_user_by_openid(cr, SUPERUSER_ID, context['account_id'], redirect.source,
                                                       context)
        val = {
            'to_user_name': redirect.target,
            'from_user_name': redirect.source,
            'create_time': redirect.time,
            'msg_type': redirect.event,
            'xml_content': redirect.raw,
            'event_key':redirect.event_key,
            'msg_event_id':event_id,
            'title':redirect.title,
            'description':redirect.description,
            'url':redirect.url,
            'app_id': context['account_id']
        }
        self.obj_message_history.create(cr, SUPERUSER_ID, val,context)
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
                                                       ('app_id', '=', context['account_id'])])
        if len(ids) == 0:
            ids = self.obj_users.get_user_info(cr, SUPERUSER_ID, [], redirect.source, context=context)
            ids = [ids]
            context = {'img': redirect.img, 'media_id': redirect.MediaId}
        # 取出用户在系统的ID
        o = self.obj_users.browse(cr, SUPERUSER_ID, ids, context)
        client_o = Client(pool, cr, o.app_id.id, o.app_id.appid,
                          o.app_id.appsecret, o.app_id.access_token,
                          o.app_id.token_expires_at)
        media_id = client_o.download_media(redirect.mediaid)
        f = urllib2.urlopen(media_id.url)
        attach_vals = {
            'name': '%s.jpg' % (redirect.mediaid),
            'datas_fname': '%s.%s' % (redirect.mediaid, f.headers.subtype),
            'datas': base64.encodestring(f.read()),
            'mimetype':media_id.headers['content-type'],

            # 'file_type': format,
            # 'type_weixin': 'image',
            # 'account_id': o.app_id.id,
            'description': redirect.source,
            'res_model': 'dhn.weixin.users',
        }
        attachment_id = pool.get('ir.attachment').create(cr, SUPERUSER_ID, attach_vals, context)
        attachment = pool.get('ir.attachment').browse(cr,SUPERUSER_ID,attachment_id,context)
        context['property'] = u'图片'
        context['user_pos'] = 'image'
        context['property_note'] = redirect.raw
        # img = '<img src="%s" alt="%s" />' % (redirect.img, redirect.MediaId)  # width="100%" height="100%"
        # message_id = self.obj_users.message_post(cr, SUPERUSER_ID, ids,
        #                                          body=(u'<span class="label label-success">图片</span><br>'),
        #                                          context=context)
        # parm = {
        #     'attachment_ids': [(4, attachment_id)],
        # }
        # pool.get('mail.message').write(cr, SUPERUSER_ID, message_id, parm, context=context)

        #下载图片到本地static
        # path = os.path.dirname(os.path.abspath("__file__"))+"\\liuhao\\tl_weixin\\static\\web_img\\"+str(redirect.id)+".jpg"
        # urllib.urlretrieve(redirect.img, path)


        #media_url 文件存储在本地的位置   格式   /web/img
        val = {
            'to_user_name': redirect.target,
            'from_user_name': redirect.source,
            'create_time': redirect.time,
            'msg_type': redirect.type,
            'xml_content': redirect.raw,
            'media_url':attachment.local_url+'.jpg',
            'media_id':redirect.mediaid,
            'msg_id': redirect.id,
            'app_id': context['account_id']
        }
        self.obj_message_history.create(cr, SUPERUSER_ID, val,context)
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
        if str(redirect.id) in MsgId:
            return ''
        MsgId[str(redirect.id)] = redirect.id

        ids = self.obj_users.search(cr, SUPERUSER_ID, [('openid', '=', redirect.source),
                                                       ('app_id', '=', context['account_id'])])
        if len(ids) == 0:
            ids = self.obj_users.get_user_info(cr, SUPERUSER_ID, [], redirect.source, context=context)
            ids = [ids]
        # 取出用户在系统的ID
        context['media_id'] = redirect.media_id
        context['format'] = redirect.format
        o = self.obj_account.browse(cr, SUPERUSER_ID, context['account_id'], context)
        client_o = Client(pool, cr, o.id, o.appid, o.appsecret, o.access_token, o.token_expires_at)
        media_id = client_o.download_media(redirect.media_id)

        f = urllib2.urlopen(media_id.url)
        attach_vals = {
            'name': '%s' % (redirect.media_id),
            'datas_fname': '%s.%s' % (redirect.media_id, f.headers.subtype),
            'datas': base64.encodestring(f.read()),
            'mimetype':media_id.headers['content-type'],

            'description': redirect.source,
            'res_model': 'dhn.weixin.users',
        }
        attachment_id = pool.get('ir.attachment').create(cr, SUPERUSER_ID, attach_vals, context)
        attachment = pool.get('ir.attachment').browse(cr,SUPERUSER_ID,attachment_id,context)
        context['property'] = u'语音'
        context['user_pos'] = 'voice'
        context['property_note'] = redirect.raw
        #media_url 文件存储在本地的位置   格式   /web/img
        val = {
            'to_user_name': redirect.target,
            'from_user_name': redirect.source,
            'create_time': redirect.time,
            'msg_type': redirect.type,
            'xml_content': redirect.raw,
            'media_id':redirect.media_id,
            'format':redirect.format,
            'msg_id': redirect.id,
            'app_id': context['account_id'],
            'media_url': attachment.local_url+'.arm'
        }
        self.obj_message_history.create(cr, SUPERUSER_ID, val,context)
        del MsgId[str(redirect.id)]
        return ''
    #视频记录未完成
    def user_post_message_video(self, cr, pool, uid, redirect, kw, context):
        """
        用户发来一条视频 记录到数据库
        """
        # 增加全局来控制 微信响应
        if str(redirect.id) in MsgId:
            return ''
        MsgId[str(redirect.id)] = redirect.id
        ids = self.obj_users.search(cr, SUPERUSER_ID, [('openid', '=', redirect.source),
                                                       ('app_id', '=', context['account_id'])])
        if len(ids) == 0:
            ids = self.obj_users.get_user_info(cr, SUPERUSER_ID, [], redirect.source, context=context)
            ids = [ids]

        o = self.obj_account.browse(cr, SUPERUSER_ID, context['account_id'], context)
        client_o = Client(pool, cr, o.id, o.appid, o.appsecret, o.access_token, o.token_expires_at)
        media_id = client_o.download_media(redirect.media_id)
        f = urllib2.urlopen(media_id.url)
        attach_vals = {
            'name': '%s' % (redirect.media_id),
            'datas_fname': '%s.%s' % (redirect.media_id, f.headers.subtype),
            'datas': base64.encodestring(f.read()),
            'mimetype':media_id.headers['content-type'],

            'description': redirect.source,
            'res_model': 'dhn.weixin.users',
        }
        attachment_id = pool.get('ir.attachment').create(cr, SUPERUSER_ID, attach_vals, context)
        attachment = pool.get('ir.attachment').browse(cr,SUPERUSER_ID,attachment_id,context)
        #media_url 文件存储在本地的位置   格式   /web/img
        val = {
            'to_user_name': redirect.target,
            'from_user_name': redirect.source,
            'create_time': redirect.time,
            'msg_type': redirect.type,
            'xml_content': redirect.raw,
            'media_id':redirect.media_id,
            'thumb_media_id':redirect.thumb_media_id,
            'msg_id': redirect.id,
            'app_id': context['account_id'],
            'media_url': attachment.local_url+'.mp4'
        }
        self.obj_message_history.create(cr, SUPERUSER_ID, val,context)

        del MsgId[str(redirect.id)]

        return ''
    #记录数据库未完成
    def user_post_message_shortvideo(self, cr, pool, uid, redirect, kw, context):
        """
        用户发来一条小视频 记录到数据库
        """
        # 增加全局来控制 微信响应
        if str(redirect.id) in MsgId:
            return ''
        MsgId[str(redirect.id)] = redirect.id
        ids = self.obj_users.search(cr, SUPERUSER_ID, [('openid', '=', redirect.source),
                                                       ('app_id', '=', context['account_id'])])
        if len(ids) == 0:
            ids = self.obj_users.get_user_info(cr, SUPERUSER_ID, [], redirect.source, context=context)
            ids = [ids]

        o = self.obj_account.browse(cr, SUPERUSER_ID, context['account_id'], context)
        client_o = Client(pool, cr, o.id, o.appid, o.appsecret, o.access_token, o.token_expires_at)
        media_id = client_o.download_media(redirect.media_id)
        f = urllib2.urlopen(media_id.url)
        attach_vals = {
            'name': '%s' % (redirect.media_id),
            'datas_fname': '%s.%s' % (redirect.media_id, f.headers.subtype),
            'datas': base64.encodestring(f.read()),
            'mimetype':media_id.headers['content-type'],

            'description': redirect.source,
            'res_model': 'dhn.weixin.users',
        }
        attachment_id = pool.get('ir.attachment').create(cr, SUPERUSER_ID, attach_vals, context)
        attachment = pool.get('ir.attachment').browse(cr,SUPERUSER_ID,attachment_id,context)
        #media_url 文件存储在本地的位置   格式   /web/img
        val = {
            'to_user_name': redirect.target,
            'from_user_name': redirect.source,
            'create_time': redirect.time,
            'msg_type': redirect.type,
            'xml_content': redirect.raw,
            'media_id':redirect.media_id,
            'thumb_media_id':redirect.thumb_media_id,
            'msg_id': redirect.id,
            'app_id': context['account_id'],
            'media_url': attachment.local_url+'.mp4'
        }
        self.obj_message_history.create(cr, SUPERUSER_ID, val,context)

        return ''

    def user_post_message_location(self, cr, pool, uid, redirect, kw, context):
        """
        用户发来一条位置信息 记录到数据库
        """
        # 增加全局来控制 微信响应
        event_id = redirect.source+str(redirect.time)
        if event_id in MsgId:
            return ''
        MsgId[event_id] = event_id
        ids = self.obj_users.search(cr, SUPERUSER_ID, [('openid', '=', redirect.source),
                                                       ('app_id', '=', context['account_id'])])
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

            val = {
                'to_user_name': redirect.target,
                'from_user_name': redirect.source,
                'create_time': redirect.time,
                'msg_type': redirect.event,
                'xml_content': redirect.raw,
                'msg_event_id':event_id,
                'location_x':redirect.latitude,
                'location_y':redirect.longitude,
                'precision':redirect.precision,
                'app_id': context['account_id']
            }
            self.obj_message_history.create(cr, SUPERUSER_ID, val,context)

        except Exception, e:
            _logger.info(e.message)
        finally:
            del MsgId[event_id]
            return ''

    def user_post_message_subscribe_unsubscribe(self, cr, pool, uid, redirect, kw, context):
        """
        用户关注 关注新建，取消关注更新 记录到数据库
         """
        # 增加全局来控制 微信响应
        event_id = redirect.source+str(redirect.time)
        if event_id in MsgId:
            return ''
        MsgId[event_id] = event_id
        ids = self.obj_users.search(cr, SUPERUSER_ID, [('openid', '=', redirect.source),
                                                       ('app_id', '=', context['account_id'])])

        domain = [('appid', '=', kw['app_id'])]
        records = self.obj_account.search_read(cr, openerp.SUPERUSER_ID, domain,
                                               ['name', 'appid', 'appsecret', 'access_token', 'token_expires_at'],
                                               context=context)[0]
        context['account_id'] = records['id']

        val = {
            'to_user_name': redirect.target,
            'from_user_name': redirect.source,
            'create_time': redirect.time,
            'msg_type': redirect.event,
            'xml_content': redirect.raw,
            'msg_event_id':event_id,
            'app_id': context['account_id']
        }
        self.obj_message_history.create(cr, SUPERUSER_ID, val,context)

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
            del MsgId[event_id]
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




class TlweixinClient(http.Controller):

    # __bucketname=openerp.tools.config['s3_bucketname']
    # __region = openerp.tools.config['s3_region']
    # __aws_access_key_id = openerp.tools.config['s3_access_key_id']
    # __aws_secret_access_key = openerp.tools.config['s3_secret_access_key']
    # __session = boto3.Session(aws_access_key_id=__aws_access_key_id,
    #               aws_secret_access_key=__aws_secret_access_key,
    #               region_name=__region)
    # __s3=__session.resource('s3')

    @http.route('/web_editor/attachment/add', type='http', auth='user', methods=['POST'])
    def attach(self, func, upload=None, url=None, disable_optimization=None, **kwargs):
        # the upload argument doesn't allow us to access the files if more than
        # one file is uploaded, as upload references the first file
        # therefore we have to recover the files from the request object
        Attachments = request.registry['ir.attachment']  # registry for the attachment table

        uploads = []
        message = None
        if not upload: # no image provided, storing the link and the image name
            name = url.split("/").pop()                       # recover filename
            attachment_id = Attachments.create(request.cr, request.uid, {
                'name': name,
                'type': 'url',
                'url': url,
                'public': True,
                'res_model': 'ir.ui.view',
            }, request.context)
            uploads += Attachments.read(request.cr, request.uid, [attachment_id], ['name', 'mimetype', 'checksum', 'url'], request.context)
        else:                                                  # images provided
            try:
                attachment_ids = []

                for c_file in request.httprequest.files.getlist('upload'):
                    pngtype = c_file.filename.split('.')[1]
                    if pngtype in ['png','jpg', u'png', u'jpg', 'JPEG', u'JPEG']:
                        url, read_data = self.imageUploadS3(c_file)
                        exit_args = [('url', '=', str(url))]
                        exit_ids = Attachments.search(request.cr, request.uid, exit_args)
                        if not exit_ids:
                            len_data = base64.encodestring(read_data)
                            file_size = len(len_data.decode('base64'))
                            attachment_id = Attachments.create(request.cr, request.uid, {
                                'name': c_file.filename,
                                # 'datas': read_data.encode('base64'),
                                'datas_fname': c_file.filename,
                                'public': True,
                                'res_model': 'ir.ui.view',
                                's3_file_size': file_size,
                                'type': 'url',
                                'url': url,
                                's3target': 's3',
                            }, request.context)
                            attachment_ids.append(attachment_id)
                        else:
                            attachment_ids += exit_ids

                    else:
                        data = c_file.read()
                        try:
                            image = Image.open(cStringIO.StringIO(data))
                            w, h = image.size
                            if w*h > 42e6: # Nokia Lumia 1020 photo resolution
                                raise ValueError(
                                    u"Image size excessive, uploaded images must be smaller "
                                    u"than 42 million pixel")
                            if not disable_optimization and image.format in ('PNG', 'JPEG'):
                                data = tools.image_save_for_web(image)
                        except IOError, e:
                            pass

                        attachment_id = Attachments.create(request.cr, request.uid, {
                            'name': c_file.filename,
                            'datas': data.encode('base64'),
                            'datas_fname': c_file.filename,
                            'public': True,
                            'res_model': 'ir.ui.view',
                        }, request.context)
                        attachment_ids.append(attachment_id)

                uploads += Attachments.read(request.cr, request.uid, attachment_ids, ['name', 'mimetype', 'checksum', 'url'], request.context)
            except Exception, e:
                _logger.exception("Failed to upload image to attachment")
                message = unicode(e)

        return """<script type='text/javascript'>
            window.parent['%s'](%s, %s);
        </script>""" % (func, json.dumps(uploads), json.dumps(message))

    #图片上传s3
    def imageUploadS3(self, ufile, permision="public-read"):
        if(permision not in ("public-read","private","bucket-owner-read")):
            return "指定的权限不存在！"
        pngtype = ufile.filename.split('.')[1]
        read_data = ufile.read()
        datas = base64.encodestring(read_data)
        sha = hashlib.sha1(datas).hexdigest()
        uid = request.session.uid
        company_id = request.registry['res.users'].browse(request.cr, uid, uid, context=request.context).company_id.id
        born_uuid = request.registry['res.company'].browse(request.cr,uid,company_id,context=request.context).born_uuid
        dir = born_uuid
        cname = sha
        uploadfile=dir.strip()+"/"+cname.strip()+"."+pngtype
        # 是否已经上传过
        # bol = self.isexists(uploadfile)
        ob=self.__s3.Object(self.__bucketname, uploadfile)
        ufile.seek(0)
        result=ob.put(Body=ufile.stream,ServerSideEncryption='AES256',StorageClass='STANDARD',ACL=permision)

        return 'https://s3.cn-north-1.amazonaws.com.cn/'+self.__bucketname+'/'+uploadfile, read_data

        
    def isexists(self,uploadfile):
        try:
            self.__s3.Object(self.__bucketname,uploadfile).get()
            return True
        except:
            return False
        
