# -*- coding: utf-8 -*-
##############################################################################
#  COMPANY: BONN
#  AUTHOR: SongHb
#  EMAIL: songhaibin1990@gmail.com
#  VERSION : 1.0   NEW  2016/03/18
#  UPDATE : NONE
#  Copyright (C) 2011-2016 www.wevip.com All Rights Reserved
##############################################################################

from .open_client import OpenWXClient
from openerp.osv import fields, osv
import logging
from datetime import *
import time
import openerp
from PIL import Image
import io
import base64
import urllib2
import json
import string
import random
from openerp import SUPERUSER_ID
from openerp import _
from openerp.exceptions import UserError, ValidationError
from openerp import api, fields, models
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT

try:
    import cStringIO as StringIO
except ImportError:
    import StringIO

_logger = logging.getLogger(__name__)


# 接口信息
class tl_open_weixin_app(models.Model):
    _name = 'tl.open.weixin.app'
    _description = "tl.open.weixin.app"

    # 获取默认公司
    def _default_company_id(self, cr, uid, context=None):
        if not context.get('company_id', False):
            company_id = self.pool.get('res.users').browse(cr, uid, uid, context).company_id.id
        else:
            company_id = context.get('company_id', False)
        return company_id

    name = fields.Char(u'开放平台', required=True)
    component_access_token = fields.Text(u'Access Token')
    app_id = fields.Char(u'AppID(应用ID)', required=True)
    app_secret = fields.Char(u'AppSecret(应用密钥)', required=True)
    component_verify_ticket = fields.Char(u'ComponentVerifyTicket(验证票据)',
                                          help=u"出于安全考虑，在第三方平台创建审核通过后，微信服务器每隔10分钟会向第三方的消息接收地址推送一次component_verify_ticket，用于获取第三方平台接口调用凭据")
    encoding_AES_key = fields.Char(u'消息加解密Key',
                                   help=u"公众号消息加解密Key", required=True)
    last_encoding_AES_key = fields.Char(u'上一次使用的消息加解密Key',
                                        help=u"当公众号消息加解密Key加解密失败后,应尝试使用上一次使用的消息加解密Key加解密.", readonly="1")

    date_token = fields.Datetime(u'Token生效时间', readonly="1")
    token_expires_at = fields.Datetime(u'Token失效时间', readonly="1")

    # pre_auth_code = fields.Text(u'预授权码', readonly="1")
    # date_pre_auth_code = fields.Datetime(u'预授权码生效时间', readonly="1")
    # pre_auth_expires_at = fields.Datetime(u'预授权码失效时间', readonly="1")
    # jsapi_ticket = fields.Text(u'JsApi Ticket', help=u"jsapi_ticket是公众号用于调用微信JS接口的临时票据。正常情况下，jsapi_ticket的有效期为7200秒.")
    # jsapi_ticket_date = fields.Datetime(u'JsApi Ticket生效时间', readonly="1")
    # jsapi_ticket_expires_at = fields.Integer(u'JsApi Ticket失效时间', readonly="1")
    company_id = fields.Many2one('res.company', u'公司', select=True)
    # page_ids = fields.One2many('tl.weixin.page', 'app_id', u'摇一摇页面', )
    # device_ids = fields.One2many('tl.device', 'app_id', u'设备', )
    # shop_id = fields.Many2one('tl.shop', u'商户')
    # user_ids = fields.One2many('tl.weixin.users', 'app_id', u'关注者')
    # group_ids = fields.One2many('tl.device.group', 'app_id', u'设备分组')
    # mch_id = fields.Char(u'微信支付商户号', help=u"微信支付分配的商户号")
    # security_key = fields.Char(u'加密KEY', help=u"key设置路径：微信商户平台(pay.weixin.qq.com)-->账户设置-->API安全-->密钥设置")
    # image = openerp.fields.Binary(u"微信公众二维码", attachment=True, help=u"建议尺寸：宽60像素，高60像素")
    # primary_industry = fields.Many2one('tl.weixin.industry', string=u'主营行业', domain=[('code', '>', 0)],
    #                                    help=u'需要选择公众账号服务所处的2个行业，每月可更改1次所选行业')
    # secondary_industry = fields.Many2one('tl.weixin.industry', string=u'副营行业', domain=[('code', '>', 0)],
    #                                      help=u'需要选择公众账号服务所处的2个行业，每月可更改1次所选行业')

    _defaults = {
        'company_id': _default_company_id,
    }

    @api.multi
    def write(self, vals):
        # 修改encoding_AES_key后将原值赋给last_encoding_AES_key
        if 'encoding_AES_key' in vals:
            vals['last_encoding_AES_key'] = self.encoding_AES_key
        return super(tl_open_weixin_app, self).write(vals)

    def grant_token(self, cr, uid, ids, context=None):
        """
        获取 Access Token
        """
        o = self.browse(cr, uid, ids[0], context)
        if not o.component_verify_ticket:
            _logger.warn(u"暂时还没有接收到微信推送的ComponentVerifyTicket验证票据,请10分钟后重试.")
            raise UserError(_(u'暂时还没有接收到微信推送的ComponentVerifyTicket验证票据,请10分钟后重试.'))
        client_obj = OpenWXClient(self.pool, cr, o.id, o.app_id, o.app_secret, o.component_verify_ticket,
                                  o.component_access_token, o.token_expires_at)
        json = client_obj.grant_token()
        if "errcode" in json:
            _logger.warn(u"获取Access Token失败，%s[%s]" % (json["errmsg"], json["errcode"]))
            raise UserError(_(u"获取Access Token失败，%s[%s]" % (json["errmsg"], json["errcode"])))
        else:
            expires_in = time.localtime(int(time.time()) + json.get("expires_in", 0))
            expires_at = time.strftime(DEFAULT_SERVER_DATETIME_FORMAT, expires_in)
            vals = {
                'component_access_token': json["component_access_token"],
                'date_token': datetime.now(),
                'token_expires_at': expires_at,
            }
            self.write(cr, uid, ids, vals)
            return json["component_access_token"]

    # 获取预授权码并跳转授权页
    @api.multi
    def get_pre_auth_page_url(self):
        """
        获取预授权码并跳转授权页
        """

        client_obj = OpenWXClient(self.pool, self._cr, self.id, self.app_id, self.app_secret,
                                  self.component_verify_ticket, self.component_access_token, self.token_expires_at)
        json = client_obj.api_create_preauthcode()
        if "errcode" in json:
            _logger.warn(u"获取预授权码，%s[%s]" % (json["errmsg"], json["errcode"]))
            raise UserError(_(u"获取预授权码失败，%s[%s]" % (json["errmsg"], json["errcode"])))
        else:
            pre_auth_code = json["pre_auth_code"]
            redirect_uri = 'http://shb.ngrok.cc/wx_auth/born90'
            url = "https://mp.weixin.qq.com/cgi-bin/componentloginpage?component_appid=%s&pre_auth_code" \
                  "=%s&redirect_uri=%s" % (self.app_id, pre_auth_code, redirect_uri)
            self.ensure_one()
            client_action = {'type': 'ir.actions.act_url',
                             'target': 'self',
                             'url': url
                             }
            return client_action
