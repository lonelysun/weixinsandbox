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
import os.path
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
    _sql_constraints = [
        ('app_id_unique', 'unique(app_id)', u'APP_ID已存在,请勿重复创建!'),
    ]

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
                             'target': 'new',
                             'url': url
                             }
            return client_action


class tl_open_weixin_merchant_lines(models.Model):
    _name = 'tl.open.weixin.merchant_lines'
    _description = "tl.open.weixin.merchant"

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


# 开放平台临时素材管理
class tl_open_weixin_material(models.Model):
    _name = "tl.open.weixin.material"
    _description = u'开放平台临时素材管理'

    # 获取默认公司
    def _default_company_id(self, cr, uid, context=None):
        if not context.get('company_id', False):
            company_id = self.pool.get('res.users').browse(cr, uid, uid, context).company_id.id
        else:
            company_id = context.get('company_id', False)
        return company_id

    app_id = fields.Many2one('tl.open.weixin.app', u'开放平台', required=True, ondelete="cascade")
    name = fields.Char(u'标题', size=255, help=u"素材的标题", required=True)
    created_at = fields.Datetime(u'上传时间', help=u'媒体文件上传时间戳', readonly="1")
    file_name = fields.Char(u'文件名称', size=512, help=u"文件名称")
    type = fields.Selection(
        [('image', u'图片'), ('video', u'视频'), ('voice', u'语音 '), ('thumb', u'缩略图')], u'素材类型',
        required=True, help=u"素材的类型，图片（image）、视频（video）、语音 （voice）")
    company_id = fields.Many2one('res.company', u'公司', select=True)
    media_id = fields.Char(u'素材编号', readonly="1")
    introduction = fields.Text(u'描述', help=u"素材的描述信息")
    annex = openerp.fields.Binary(u"附件", attachment=True,
                                  help=u"上传图文消息内的图片获取URL 请注意，本接口所上传的图片不占用公众号的素材库中图片数量的5000个的限制。图片仅支持jpg/png格式，大小必须在1MB以下")
    image = openerp.fields.Binary(u"附件", attachment=True,
                                  help=u"上传图文消息内的图片获取URL 请注意，本接口所上传的图片不占用公众号的素材库中图片数量的5000个的限制。图片仅支持jpg/png格式，大小必须在1MB以下")

    _defaults = {
        'company_id': _default_company_id,
        'type': 'image'
    }

    @api.model
    def create(self, vals):
        material = super(tl_open_weixin_material, self).create(vals)
        # 将数据提交到微信
        app_obj = self.env["tl.open.weixin.app"]
        o = app_obj.browse(int(material.app_id.id))
        if o and not material.media_id:
            client_obj = OpenWXClient(self.pool, self._cr, o.id, o.app_id, o.app_secret, o.component_verify_ticket,
                                      o.component_access_token, o.token_expires_at)
            # 视频，音频，图片
            if material.type in ['image', 'thumb']:
                src = material.image
            else:
                src = material.annex
            file_stream = StringIO.StringIO(src.decode('base64'))
            file_name = 'temp' + os.path.splitext(material.file_name)[1]
            json = client_obj.upload_material(material.type, file_stream, file_name, material.name,
                                              material.introduction)
            if "errcode" in json and json["errcode"] != 0:
                raise UserError(_(json["errmsg"]))
            else:
                created_at_timestamp = time.localtime(json['created_at'])
                created_at = time.strftime(DEFAULT_SERVER_DATETIME_FORMAT, created_at_timestamp)
                update_vals = {
                    'media_id': json['media_id'],
                    'created_at': created_at,
                }
                material.write(update_vals)
        return material

    # 重新上传临时素材
    @api.multi
    def do_re_upload(self):
        """
        获取预授权码并跳转授权页
        """
        app_obj = self.env["tl.open.weixin.app"]
        o = app_obj.browse(int(self.app_id.id))
        if o and self.media_id:
            client_obj = OpenWXClient(self.pool, self._cr, o.id, o.app_id, o.app_secret, o.component_verify_ticket,
                                      o.component_access_token, o.token_expires_at)
            # 视频，音频，图片
            if self.type in ['image', 'thumb']:
                src = self.image
            else:
                src = self.annex
            file_stream = StringIO.StringIO(src.decode('base64'))
            file_name = 'temp' + os.path.splitext(self.file_name)[1]
            json = client_obj.upload_material(self.type, file_stream, file_name, self.name,
                                              self.introduction)
            if "errcode" in json and json["errcode"] != 0:
                raise UserError(_(json["errmsg"]))
            else:
                created_at_timestamp = time.localtime(json['created_at'])
                created_at = time.strftime(DEFAULT_SERVER_DATETIME_FORMAT, created_at_timestamp)
                update_vals = {
                    'media_id': json['media_id'],
                    'created_at': created_at,
                }
                self.write(update_vals)
        return True


# 卡券开放类目
class merchant_apply_protocol(models.Model):
    _name = "merchant.apply.protocol"
    _description = u"卡券开放类目"
    _rec_name = 'category_name'

    category_id = fields.Integer(u'类目id')
    category_name = fields.Char(u'类目名')
    parent_category_id = fields.Many2one('merchant.apply.protocol', u'父级类目')


# 开放平台子商户
class tl_open_weixin_merchant(models.Model):
    _name = "tl.open.weixin.merchant"
    _description = u'开放平台子商户'

    # 获取默认公司
    def _default_company_id(self, cr, uid, context=None):
        if not context.get('company_id', False):
            company_id = self.pool.get('res.users').browse(cr, uid, uid, context).company_id.id
        else:
            company_id = context.get('company_id', False)
        return company_id

    company_id = fields.Many2one('res.company', u'公司', select=True, readonly=True,
                                 states={'draft': [('readonly', False)], 'RESULT_NOT_PASS': [('readonly', False)]}, )
    app_id = fields.Char(u'APP_ID', help=u'子商户公众号的appid', readonly=True,
                         states={'draft': [('readonly', False)], 'RESULT_NOT_PASS': [('readonly', False)]}, )
    reason = fields.Text(u'驳回原因', help=u'申请驳回的原因', readonly=True,
                         states={'draft': [('readonly', False)], 'RESULT_NOT_PASS': [('readonly', False)]}, )
    name = fields.Char(u'商户名', help=u'子商户商户名，用于显示在卡券券面,商户名称在12个汉字长度内.', readonly=True,
                       states={'draft': [('readonly', False)], 'RESULT_NOT_PASS': [('readonly', False)]}, )
    logo_meida_id = fields.Many2one('tl.open.weixin.material', u'商户logo',
                                    help=u'子商户logo，用于显示在子商户卡券的券面', readonly=True,
                                    states={'draft': [('readonly', False)], 'RESULT_NOT_PASS': [('readonly', False)]}, )
    business_license_media_id = fields.Many2one('tl.open.weixin.material', u'营业执照或个体工商户执照',
                                                help=u'营业执照或个体工商户执照扫描件的media_id', readonly=True,
                                                states={'draft': [('readonly', False)],
                                                        'RESULT_NOT_PASS': [('readonly', False)]}, )
    operator_id_card_media_id = fields.Many2one('tl.open.weixin.material', u'身份证',
                                                help=u'当子商户为个体工商户且无公章时，授权函须签名，并额外提交该个体工商户经营者身份证扫描件的media_id',
                                                readonly=True,
                                                states={'draft': [('readonly', False)],
                                                        'RESULT_NOT_PASS': [('readonly', False)]}, )
    agreement_file_media_id = fields.Many2one('tl.open.weixin.material', u'授权函',
                                              help=u'子商户与第三方签署的代理授权函的media_id', readonly=True,
                                              states={'draft': [('readonly', False)],
                                                      'RESULT_NOT_PASS': [('readonly', False)]}, )
    agent_id = fields.Many2one('tl.open.weixin.app', u'开放平台', help=u'母商户', select=True, readonly=True,
                               states={'draft': [('readonly', False)], 'RESULT_NOT_PASS': [('readonly', False)]}, )
    primary_category_id = fields.Many2one('merchant.apply.protocol', u'一级类目id', readonly=True,
                                          states={'draft': [('readonly', False)],
                                                  'RESULT_NOT_PASS': [('readonly', False)]}, )
    primary_category_code = fields.Integer(related='primary_category_id.category_id', store=True, readonly=True,
                                           string=u'一级类目id')
    secondary_category_id = fields.Many2one('merchant.apply.protocol', u'二级类目id', readonly=True,
                                            states={'draft': [('readonly', False)],
                                                    'RESULT_NOT_PASS': [('readonly', False)]}, )
    secondary_category_code = fields.Integer(related='secondary_category_id.category_id', store=True, readonly=True,
                                             string=u'二级类目id')

    is_individually_owned = fields.Boolean(u'个体工商户', readonly=True,
                                           states={'draft': [('readonly', False)],
                                                   'RESULT_NOT_PASS': [('readonly', False)]}, )
    is_update_merchant_apply_protocol = fields.Boolean(u'更新卡券开放类目', readonly=True,
                                                       states={'draft': [('readonly', False)],
                                                               'RESULT_NOT_PASS': [('readonly', False)]}, )
    submit_time = fields.Datetime(u'提交时间', readonly="1")
    state = fields.Selection(
        [('draft', u'草稿'), ('RESULT_CHECKING', u'待审核'),
         ('RESULT_NOT_PASS', u'审核驳回'), ('RESULT_PASS', u'审核通过'),
         ('RESULT_NOTHING_TO_CHECK', u'无提审记录')], u'状态', default='draft')

    _defaults = {
        'company_id': _default_company_id,
    }
    _sql_constraints = [
        ('app_id_unique', 'unique(app_id)', u'APP_ID已存在,请勿重复创建!'),
    ]

    @api.model
    def create(self, vals):
        if 'primary_category_id' not in vals or not vals.get('primary_category_id', False):
            raise UserError(_(u"一级类目id必填"))
        if 'secondary_category_id' not in vals or not vals.get('secondary_category_id', False):
            raise UserError(_(u"二级类目id必填"))
        return super(tl_open_weixin_merchant, self).create(vals)

    # 更新卡券开放类目
    @api.onchange('is_update_merchant_apply_protocol')
    def on_change_update_merchant_apply_protocol(self):
        if not self.agent_id:
            return {}
        context = dict(self._context or {})

        agent_id = self.agent_id.id
        weixin_app_obj = self.env['tl.open.weixin.app']
        app = weixin_app_obj.browse(agent_id)

        client_obj = OpenWXClient(self.pool, self._cr, app.id, app.app_id, app.app_secret, app.component_verify_ticket,
                                  app.component_access_token, app.token_expires_at)
        json = client_obj.card_get_apply_protocol()
        if "errcode" in json and json['errcode'] != 0:
            _logger.warn(u"更新卡券开放类目失败，%s[%s]" % (json["errmsg"], json["errcode"]))
            raise UserError(_(u"更新卡券开放类目失败，%s[%s]" % (json["errmsg"], json["errcode"])))
        else:
            res = {}
            self._cr.execute("""DELETE FROM merchant_apply_protocol""")
            protocol_app_obj = self.env['merchant.apply.protocol']
            for primary in json['category']:
                pvals = {'category_id': primary['primary_category_id'], 'category_name': primary['category_name']}
                primary_category_id = protocol_app_obj.create(pvals)
                for secondary in primary['secondary_category']:
                    svals = {'category_id': secondary['secondary_category_id'],
                             'category_name': secondary['category_name'],
                             'parent_category_id': primary_category_id.id,
                             }
                    protocol_app_obj.create(svals)

    # 子商户资质申请接口
    @api.multi
    def qualification_apply(self):
        if not self.agent_id:
            return {}
        context = dict(self._context or {})

        agent_id = self.agent_id.id
        if len(unicode(self.name)) > 12:
            raise UserError(_(u"商户名称应该在12个汉字长度内"))
        args = {
            "appid": self.app_id,
            "name": self.name,
            "logo_media_id": self.logo_meida_id.media_id,
            "business_license_media_id": self.business_license_media_id.media_id,
            "agreement_file_media_id": self.agreement_file_media_id.media_id,
            "primary_category_id": self.primary_category_id.category_id,
            "secondary_category_id": self.secondary_category_id.category_id
        }
        if self.is_individually_owned:
            args['operator_id_card_media_id'] = self.operator_id_card_media_id.media_id

        weixin_app_obj = self.env['tl.open.weixin.app']
        app = weixin_app_obj.browse(agent_id)

        client_obj = OpenWXClient(self.pool, self._cr, app.id, app.app_id, app.app_secret, app.component_verify_ticket,
                                  app.component_access_token, app.token_expires_at)
        json = client_obj.merchant_qualification_apply(args)
        if "errcode" in json and json['errcode'] != 0:
            if json['errcode'] == 40007:
                _logger.warn(u"申请资料过期,有效期为3天,请重新上传后在申请(%s[%s])." % (json["errmsg"], json["errcode"]))
                raise UserError(u"申请资料过期,有效期为3天,请重新上传后在申请(%s[%s])." % (json["errmsg"], json["errcode"]))
            if json['errcode'] == 61022:
                _logger.warn(u"资料正在审核中,不可重复提交(%s[%s])." % (json["errmsg"], json["errcode"]))
                raise UserError(u"资料正在审核中,不可重复提交(%s[%s])." % (json["errmsg"], json["errcode"]))
            else:
                _logger.warn(u"子商户资质申请失败,失败原因:%s[%s]." % (json["errmsg"], json["errcode"]))
                raise UserError(u"子商户资质申请失败,失败原因:%s[%s]." % (json["errmsg"], json["errcode"]))
        else:
            self.write({'state': 'RESULT_CHECKING', 'submit_time': datetime.now()})
            return True

    # 子商户资质审核查询接口
    @api.multi
    def qualification_query(self):
        context = dict(self._context or {})

        agent_id = self.agent_id.id
        weixin_app_obj = self.env['tl.open.weixin.app']
        app = weixin_app_obj.browse(agent_id)

        client_obj = OpenWXClient(self.pool, self._cr, app.id, app.app_id, app.app_secret, app.component_verify_ticket,
                                  app.component_access_token, app.token_expires_at)
        json = client_obj.merchant_qualification_query(self.app_id)
        if "errcode" in json and json['errcode'] != 0:
            _logger.warn(u"子商户资质审核查询失败,失败原因:%s[%s]." % (json["errmsg"], json["errcode"]))
            raise UserError(u"子商户资质审核查询失败,失败原因:%s[%s]." % (json["errmsg"], json["errcode"]))
        else:
            if "result" in json and json['result'] != self.state:
                self.write({'state': json['result']})
            return True
