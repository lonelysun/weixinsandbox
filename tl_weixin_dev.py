# -*- coding: utf-8 -*-
##############################################################################
#  COMPANY: BONN
#  AUTHOR: KIWI
#  EMAIL: arborous@gmail.com
#  VERSION : 1.0   NEW  2015/12/12
#  UPDATE : NONE
#  Copyright (C) 2011-2016 www.mychinavip.com All Rights Reserved
##############################################################################
from tools.client import Client
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
import re

from openerp import _
from openerp.exceptions import UserError, ValidationError
from openerp import api, fields, models

try:
    import cStringIO as StringIO
except ImportError:
    import StringIO

_logger = logging.getLogger(__name__)

#微信文档
#http://mp.weixin.qq.com/wiki/6/0eb3f80f152d2edb95287141e7a6ab5e.html



#消息管理



#自定义菜单


#微信多客服功能


#微信连Wi-Fi


#微信扫一扫


# 模板列表
class tl_weixin_template(models.Model):
    _name = 'tl.weixin.template'
    _description = u"消息模板"
    _rec_name = 'title'

    app_id = fields.Many2one('tl.weixin.app', u'微信公众号', required=True, help=u'微信公众号')
    company_id = fields.Many2one('res.company', u'公司', default=lambda self: self.env.user.company_id, help=u"所属公司")
    template_id = fields.Char(u'模板ID', required=True, help=u'模板ID')
    title = fields.Char(u'模板标题', required=True, help=u'模板标题')
    primary_industry = fields.Char(u'一级行业', required=True, help=u'模板所属行业的一级行业')
    deputy_industry = fields.Char(u'二级行业', required=True, help=u'模板所属行业的二级行业')
    content = fields.Text(u'模板内容', required=True, help=u'模板内容')
    example = fields.Text(u'模板示例', required=True, help=u'模板示例')


# 行业
class tl_weixin_industry(models.Model):
    _name = 'tl.weixin.industry'
    _description = u"行业代码"

    name = fields.Char(u'名称', required=True, help=u'名称')
    code = fields.Integer(u'代码', required=True, help=u'代码')
    parent_id = fields.Many2one('tl.weixin.industry',string=u'主行业', help=u'上级行业')


# 发送模板消息
class tl_weixin_message(models.Model):
    _name = 'tl.weixin.message'
    _description = u"模板消息"
    _rec_name = 'template_id'

    app_id = fields.Char(compute="_onchange_template_id", string=u'微信公众号', help=u'微信公众号')
    company_id = fields.Many2one('res.company', u'公司', default=lambda self: self.env.user.company_id, help=u"所属公司")
    user_ids = fields.Many2many('tl.weixin.users', 'tl_weixin_users_message_rel',
                            string=u'用户', help=u'给哪些用户发送消息')
    template_id = fields.Many2one('tl.weixin.template', u'模板', required=True, help=u'发送短信的模板')
    template_content = fields.Text(compute='_onchange_template_id', string=u'模板内容', help=u'选择的模板内容')
    template_example = fields.Text(compute='_onchange_template_id', string=u'模板示例', help=u'选择的模板示例')
    params_ids = fields.One2many('tl.weixin.message.params', 'message_id', string=u'模板参数', help=u'模板的参数')
    state = fields.Selection([('draft', u'草稿'), ('send', u'已发送'), ('finished', u'已送达'), ('failed', u'发送失败'),
                              ('cancel', u'无效')], u'状态', default='draft', required=True, readonly=True)
    actual_content = fields.Text(compute='_onchange_params_ids', string=u'发送的内容', help=u'模板配合参数生成的内容')
    url = fields.Char(string=u'跳转的链接', help=u"点击消息所跳转到的链接")
    result_ids = fields.One2many('tl.weixin.message.results', 'message_id',
                                 string=u'消息id', help=u"发送的消息服务器端ID")

    # 发送模板消息按钮
    @api.multi
    def send_message_button(self):
        url = self.url
        if not url:
            url = ''

        # 发送的消息POST中的data
        data = {}
        for each_param in self.params_ids:
            data[each_param.params_key] = {"value": each_param.params_value, "color": "#173177"}

        # 发送给的用户
        if not self.user_ids:
            raise UserError(_(u'请选择发送的用户!'))

        user_lst = self.user_ids

        o = self.template_id.app_id
        client_obj = Client(self.pool, self._cr, o.id, o.appid, o.appsecret, o.access_token, o.token_expires_at)

        lst = []
        for user in user_lst:
            json = client_obj.send_message(user['openid'], self.template_id.template_id, url, data)
            if "errcode" in json and json["errcode"] != 0:
                raise UserError(_(json["errmsg"]))
            else:
                self.state = 'send'
                vals = {
                    'errcode': json['errcode'],
                    'errmsg': json['errmsg'],
                    'msgid': json['msgid'],
                    'user_id': user.id
                }
                lst.append(vals)
        self.result_ids = lst
        return

    # 选择不同模板后更改模板内容、微信公众号、模板示例
    @api.onchange('template_id')
    def _onchange_template_id(self):

        if self.template_id:
            self.template_content = self.template_id.content
            self.template_example = self.template_id.example
            self.app_id = self.template_id.app_id.name

            # 解析模板内容获得擦书列表
            pat = r'\{\{(\S+).DATA}}'
            params_list = re.findall(pat, self.template_content)

            vals_list = []
            for each_param in params_list:
                vals = {
                    'params_key': each_param,
                    'params_value': False
                }
                vals_list.append((0, 0, vals))

            self.params_ids = vals_list

    # 修改模板参数后更改发送的内容
    @api.onchange('params_ids')
    def _onchange_params_ids(self):

        now_content = self.template_content

        for each_param in self.params_ids:
            params_key = each_param.params_key
            params_value = each_param.params_value

            if params_key and params_value:

                pat = r'\{\{' + params_key + r'.DATA\}\}'
                now_content = re.sub(pat, params_value, now_content)

        self.actual_content = now_content
        return


# 模板消息参数
class tl_weixin_message_params(models.Model):
    _name = 'tl.weixin.message.params'
    _description = u"模板消息参数"

    message_id = fields.Many2one('tl.weixin.message', string=u'消息', help=u"消息")
    params_key = fields.Char(string=u'参数名', help=u"模板中参数的名称")
    params_value = fields.Char(string=u'参数值', help=u'模板中参数的值')


# 模板消息发送后返回的结果
class tl_weixin_message_results(models.Model):
    _name = 'tl.weixin.message.results'
    _description = u"模板消息参数"

    message_id = fields.Many2one('tl.weixin.message', string=u'消息', help=u"消息")
    user_id = fields.Many2one('tl.weixin.users', string=u'关注者', help=u'接收消息的用户')
    msgid = fields.Char(string=u'消息ID', help=u"微信服务器识别消息的ID")
    errmsg = fields.Char(string=u'错误信息', help=u'错误信息')
    errcode = fields.Char(string=u'错误代码', help=u'错误代码')

# 微信用户组
# 模板消息发送后返回的结果
class tl_weixin_users_groups(models.Model):
    _name = 'tl.weixin.users.groups'
    _description = u"关注者的用户组"

    user_ids = fields.One2many('tl.weixin.users', 'group_id', string=u'关注者', help=u'该组的用户')

    app_id = fields.Many2one('tl.weixin.app', u'微信公众号', required=True)
    company_id = fields.Many2one('res.company', u'公司', default=lambda self: self.env.user.company_id, help=u"所属公司")

    name = fields.Char(string=u'组名', required=True, size=30, help=u"用户所属组的名字")
    groupid = fields.Integer(string=u'组ID', help=u'用户所属组的ID')
    users_count = fields.Integer(string=u'用户数量', help=u'分组内用户数量')

    @api.model
    def create(self, vals):
        auto = vals.has_key('auto')

        if auto:
            vals.pop('auto')

        if not auto:

            app_id = vals.get('app_id')
            o = self.env["tl.weixin.app"].browse(app_id)
            client_obj = Client(self.pool, self._cr, o.id, o.appid, o.appsecret, o.access_token, o.token_expires_at)
            json = client_obj.create_group(vals["name"])

            if "errcode" in json and json["errcode"] != 0:
                raise UserError(_(json["errmsg"]))
            else:
                vals["groupid"] = int(json["group"]["id"])
                vals["name"] = json["group"]["name"]

        return super(tl_weixin_users_groups, self).create(vals)

    @api.multi
    def write(self, vals):
        auto = vals.has_key('auto')

        if auto:
            vals.pop('auto')

        if not auto and vals.get('name'):
            o = self.app_id
            client_obj = Client(self.pool, self._cr, o.id, o.appid, o.appsecret, o.access_token, o.token_expires_at)
            json = client_obj.update_group(self.groupid, vals.get('name', ''))

            if "errcode" in json and json["errcode"] != 0:
                raise UserError(_(json["errmsg"]))
            else:
                return super(tl_weixin_users_groups, self).write(vals)

    @api.multi
    def unlink(self):

        o = self.app_id
        client_obj = Client(self.pool, self._cr, o.id, o.appid, o.appsecret, o.access_token, o.token_expires_at)
        json = client_obj.delete_user_group(self.groupid)

        # TODO json 返回为空，和文档上的不一样，但也删除了
        if "errcode" in json and json["errcode"] != 0:
            raise UserError(_(json["errmsg"]))
        else:
            ## 将用户移到默认组
            #　查询默认分组
            openid = (self.user_ids)[0].openid
            json = client_obj.get_group_by_id(openid)

            if "errcode" in json and json["errcode"] != 0:
                raise UserError(_(json["errmsg"]))
            else:
                group_id = self.search([('groupid','=',int(json['groupid']))]).id
                print group_id
                self.user_ids.write(
                    {
                        "group_id": group_id,
                        "auto": True
                    }
                )

            return super(tl_weixin_users_groups, self).unlink()


# 移动用户到组wizard
class tl_weixin_users_groups_wizard(osv.TransientModel):


    _name = "tl.weixin.users.groups.wizard"
    _description = u"更改用户组的用户向导"

    @api.multi
    def _get_default_user_ids(self):

        context = dict(self._context or {})
        user_model = self.env['tl.weixin.users']
        user_ids = context.get('active_model') == 'tl.weixin.users' and context.get('active_ids') or []
        return [(6, 0, user_ids)]

    user_ids = fields.Many2many('tl.weixin.users',
                                string=u'要移动的用户',default= _get_default_user_ids)
    groups_id = fields.Many2one('tl.weixin.users.groups', string=u'移动到组', help=u'将用户移动到哪个组')


    @api.multi
    def change_users_groups_button(self):

        openid_list = [user.openid for user in self.user_ids]
        to_groupid = self.groups_id.groupid

        # 增加判断如果所选用户不是用一个公众号的
        app_id_set = set([user.app_id.id for user in self.user_ids])
        if len(app_id_set) > 1:
            raise UserError(_(u'所选用户不属于同一个公众号'))
        elif list(app_id_set)[0] != self.groups_id.app_id.id:
            raise UserError(_(u'所选用户和所选组不属于同一个公众号'))


        o = self.groups_id.app_id
        client_obj = Client(self.pool, self._cr, o.id, o.appid, o.appsecret, o.access_token, o.token_expires_at)
        json = client_obj.batch_move_user_group(openid_list, to_groupid)

        if "errcode" in json and json["errcode"] != 0:
            raise UserError(_(json["errmsg"]))
        else:
            # local移动用户到对应的组
            self.user_ids.write({
                'group_id':self.groups_id.id,
                'auto': True
            })

            return
