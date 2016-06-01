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
import hashlib
import uuid
import copy
import calendar

from openerp import _
from openerp.exceptions import UserError, ValidationError
from openerp import api, fields, models
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
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
class tl_weixin_template_message(models.Model):
    _name = 'tl.weixin.template.message'
    _description = u"模板消息"
    _rec_name = 'template_id'

    app_id = fields.Many2one('tl.weixin.app',string=u'微信公众号', required=True, help=u'微信公众号')
    company_id = fields.Many2one('res.company', u'公司', default=lambda self: self.env.user.company_id, help=u"所属公司")
    user_ids = fields.Many2many('tl.weixin.users', 'tl_weixin_users_template_message_rel',
                            string=u'用户', help=u'给哪些用户发送消息')
    template_id = fields.Many2one('tl.weixin.template', u'模板', required=True, help=u'发送短信的模板')
    template_content = fields.Text(compute='_onchange_template_id', string=u'模板内容', help=u'选择的模板内容')
    template_example = fields.Text(compute='_onchange_template_id', string=u'模板示例', help=u'选择的模板示例')
    params_ids = fields.One2many('tl.weixin.template.message.params', 'message_id', string=u'模板参数', help=u'模板的参数')
    state = fields.Selection([('draft', u'草稿'), ('send', u'已发送'), ('finished', u'已送达'), ('failed', u'发送失败'),
                              ('cancel', u'无效')], u'状态', default='draft', required=True, readonly=True)
    actual_content = fields.Text(compute='_onchange_params_ids', string=u'发送的内容', help=u'模板配合参数生成的内容')
    url = fields.Char(string=u'跳转的链接', help=u"点击消息所跳转到的链接")
    result_ids = fields.One2many('tl.weixin.template.message.results', 'message_id',
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

    # 选择公众号筛选模板
    @api.onchange('app_id')
    def _onchange_app_id(self):
        if self.app_id:

            # 增加筛选，筛选选择的公众号下的模板
            templates = self.env['tl.weixin.template'].search([('app_id','=',self.app_id.id)])
            template_ids = [template.id for template in templates]

            # 增加对发送的用户筛选，为选择的公众号下的用户
            users = self.app_id.user_ids
            user_ids = [user.id for user in users]

            return {'domain':{'template_id':[('id','in',template_ids)],
                              'user_ids':[('id','in',user_ids)]
                              }}



    # 选择不同模板后更改模板内容、微信公众号、模板示例
    @api.onchange('template_id')
    def _onchange_template_id(self):

        if self.template_id:
            self.template_content = self.template_id.content
            self.template_example = self.template_id.example
            # self.app_id = self.template_id.app_id.name

            # 解析模板内容获得参数列表
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
class tl_weixin_template_message_params(models.Model):
    _name = 'tl.weixin.template.message.params'
    _description = u"模板消息参数"

    message_id = fields.Many2one('tl.weixin.template.message', string=u'消息', help=u"消息")
    params_key = fields.Char(string=u'参数名', help=u"模板中参数的名称")
    params_value = fields.Char(string=u'参数值', help=u'模板中参数的值')


# 模板消息发送后返回的结果
class tl_weixin_template_message_results(models.Model):
    _name = 'tl.weixin.template.message.results'
    _description = u"模板消息结果"

    message_id = fields.Many2one('tl.weixin.template.message', string=u'消息', help=u"消息")
    user_id = fields.Many2one('tl.weixin.users', string=u'关注者', help=u'接收消息的用户')
    msgid = fields.Char(string=u'消息ID', help=u"微信服务器识别消息的ID")
    errmsg = fields.Char(string=u'错误信息', help=u'错误信息')
    errcode = fields.Char(string=u'错误代码', help=u'错误代码')

# 微信用户组
class tl_weixin_users_groups(models.Model):
    _name = 'tl.weixin.users.groups'
    _description = u"关注者的用户组"

    user_ids = fields.One2many('tl.weixin.users', 'group_id', string=u'关注者', help=u'该组的用户')

    app_id = fields.Many2one('tl.weixin.app', u'微信公众号', required=True)
    company_id = fields.Many2one('res.company', u'公司', default=lambda self: self.env.user.company_id, help=u"所属公司")

    name = fields.Char(string=u'组名', required=True, size=30, help=u"分组名称")
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
            openid = self.user_ids[0].openid
            json = client_obj.get_group_by_id(openid)

            if "errcode" in json and json["errcode"] != 0:
                raise UserError(_(json["errmsg"]))
            else:
                group_id = self.search([('groupid', '=', int(json['groupid']))]).id
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
    _description = u"更改用户组的向导"

    @api.multi
    def _get_default_user_ids(self):

        context = dict(self._context or {})
        user_model = self.env['tl.weixin.users']
        user_ids = context.get('active_model') == 'tl.weixin.users' and context.get('active_ids') or []
        return [(6, 0, user_ids)]

    user_ids = fields.Many2many('tl.weixin.users',
                                string=u'要移动的用户',default= _get_default_user_ids)
    groups_id = fields.Many2one('tl.weixin.users.groups', string=u'移动到组', help=u'将用户移动到哪个组')



    @api.onchange('user_ids')
    def _onchange_user_ids(self):
        if self.user_ids:
            app_id_set = set([user.app_id.id for user in self.user_ids])
            if len(app_id_set) > 1:
                raise UserError(_(u'所选用户不属于同一个公众号'))

            # 找出所选用户所在的微信公众号　所存在的分组
            groups = self.user_ids[0].app_id.user_group_ids
            group_ids = [group.id for group in groups]
            return {'domain': {
                              'groups_id': [('id', 'in', group_ids)]
                              }}




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

# 群发消息
class tl_weixin_group_message(models.Model):
    _name = 'tl.weixin.group.message'
    _description = u"群发消息"
    _rec_name = 'app_id'

    app_id = fields.Many2one('tl.weixin.app', required=True, string=u'微信公众号', help=u'发送消息的公众号')
    group_id = fields.Many2one('tl.weixin.users.groups', string='组', help=u'群发消息的组')
    company_id = fields.Many2one('res.company', u'公司', default=lambda self: self.env.user.company_id, help=u"所属公司")
    user_ids = fields.Many2many('tl.weixin.users','tl_weixin_group_message_rel',string=u'用户', help=u'给哪些用户发送消息')
    group_user_ids = fields.One2many(related="group_id.user_ids")
    material_id = fields.Many2one('tl.weixin.material', string=u'素材',help=u"群发选择的素材")
    send_type = fields.Selection([('group',u'按组群发'),('openid', u'按用户群发'),('all',u'全部发送')],
                                 string=u'发送方式', default='group', required=True, help=u"按哪种方式群发")
    msgtype = fields.Selection(
        [('mpnews', u'图文'), ('text', u'文本'), ('voice', u'语音'),
         ('image', u'图片'), ('mpvideo', u'视频'), ('wxcard', u'卡券消息')], string=u'消息类型',
        required=True, default='mpnews',
        help=u"素材的类型，图文（mpnews）、文本（text） 语音 （voice）、图片（image）、视频（mpvideo）、卡券消息（wxcard）")
    content = fields.Text(u'文本消息内容')
    # is_to_all = fields.Boolean(u'用于设定是否向全部用户发送')
    state = fields.Selection([('draft', u'草稿'), ('send', u'已发送'), ('finished', u'已送达'), ('failed', u'发送失败'),
                              ('cancel', u'无效'), ('delete', u'已删除')], u'状态', default='draft', required=True, readonly=True)

    errcode = fields.Char(string=u'错误码', help=u"错误码")
    errmsg = fields.Char(string=u'错误信息', help=u"错误信息")
    msg_id = fields.Char(string=u'消息发送任务ID', help=u"消息发送任务的ID")
    msg_data_id = fields.Char(string=u'消息数据ID', help=u"消息的数据ID，该字段只有在群发图文消息时，才会出现。")

    send_time = fields.Datetime(u'消息发送时间')

    # TODO 图文素材内置图片功能还没有
    # 接口上的发送图文消息说明中不是用的素材接口中上传的那种，而是通过另外两个接口得到的素材media_id
    # 我不知道实际该用哪个,暂时用永久图文素材中的
    # title = fields.Char(u'消息标题', help=u'消息的标题')
    # description = fields.Char(u'消息描述', help=u'消息的描述')


    @api.onchange('app_id','msgtype')
    def _onchange_app_id_msgtype(self):
        if self.app_id:
            group_ids = [group.id for group in self.app_id.user_group_ids]
            user_ids = [user.id for user in self.app_id.user_ids]

            if self.msgtype == 'mpnews':
                domain = [('app_id','=',self.app_id.id),('type','=','news')]
            elif self.msgtype == 'voice':
                domain = [('app_id','=',self.app_id.id),('type','=','voice')]
            elif self.msgtype == 'image':
                domain = [('app_id','=',self.app_id.id),('type','=','image')]
            elif self.msgtype == 'voice':
                domain = [('app_id','=',self.app_id.id),('type','=','voice')]
            elif self.msgtype == 'mpvideo':
                domain = [('app_id','=',self.app_id.id),('type','=','video')]

            # NEXT 'wxcard'还未开发，所以此处先不做筛选
            elif self.msgtype in ['text','wxcard',]:
                domain = [('app_id','=',self.app_id.id)]

            materials = self.env['tl.weixin.material'].search(domain)
            material_ids = [material.id for material in materials]

            return {'domain':{'group_id':[('id','in',group_ids)],
                              'user_ids':[('id','in', user_ids)],
                              'material_id':[('id','in',material_ids)]
                              }}



    @api.multi
    def send_group_message_button(self):

        o = self.app_id
        client_obj = Client(self.pool, self._cr, o.id, o.appid, o.appsecret, o.access_token, o.token_expires_at)

        content = ''
        # 根据消息类型配置对应的数据
        if self.msgtype == 'text':
            content = self.content
        elif self.msgtype in ['image','voice', 'mpnews']:
            # 针对图文信息暂时定为用永久图文素材库中的
            content = self.material_id.media_id
        elif self.msgtype == 'mpvideo':
            raise UserError(_(u'视频发送还在完善中'))

            # NEXT 完善发送视频（上传视频素材还没写）
            # NEXT  此处接口需要确认，任务接口中将变量写成了常量字符串
            # 如果是上传的视频，此处视频的media_id需通过POST请求到下述接口特别地得到
            # https://file.api.weixin.qq.com/cgi-bin/media/uploadvideo?access_token=ACCESS_TOKEN

            json = client_obj.uploadvideo(self.material_id.media_id, self.title, self.description)
            if "errcode" in json and json["errcode"] != 0:
                raise UserError(_(json["errmsg"]))
            else:
                content = json['media_id']
        elif self.msgtype == 'wxcard':
            # 卡券接口还没写
            raise UserError(_(u'暂不支持卡券'))

        # 根据选择的发送方式发送
        if self.send_type == 'group':
            json = client_obj.send_mass_group(False, self.group_id.groupid, self.msgtype, content)
            if "errcode" in json and json["errcode"] != 0:
                raise UserError(_(json["errmsg"]))
            else:
                self.state = 'send'
                self.errcode = json.get('errcode', '')
                self.errmsg = json.get('errmsg', '')
                self.msg_id = json.get('msg_id', '')
                self.msg_data_id = json.get('msg_data_id', '')
                self.send_time = datetime.now()


        elif self.send_type == 'openid':
            user_list = [user.openid for user in self.user_ids]
            if len(user_list) < 2:
                raise UserError(_(u'群发请至少选择两位用户'))
            json = client_obj.send_mass_openid(self.msgtype, user_list, content)
            if "errcode" in json and json["errcode"] != 0:
                raise UserError(_(json["errmsg"]))
            else:
                self.state = 'send'
                self.errcode = json.get('errcode', '')
                self.errmsg = json.get('errmsg', '')
                self.msg_id = json.get('msg_id', '')
                self.msg_data_id = json.get('msg_data_id', '')
                self.send_time = datetime.now()

        elif self.send_type == 'all':
            json = client_obj.send_mass_group(True, 0, self.msgtype, content)
            if "errcode" in json and json["errcode"] != 0:
                raise UserError(_(json["errmsg"]))
            else:
                self.state = 'send'
                self.errcode = json.get('errcode', '')
                self.errmsg = json.get('errmsg', '')
                self.msg_id = json.get('msg_id', '')
                self.msg_data_id = json.get('msg_data_id', '')
                self.send_time = datetime.now()
        return

    @api.multi
    def delete_message_button(self):
        if self.msgtype not in ['mpnews', 'mpvideo']:
            raise UserError(_(u'删除群发消息只能删除图文消息和视频消息，其他类型的消息一经发送，无法删除'))

        if self.state != 'send':
            raise UserError(_(u'只有状态为"已发送"的消息才能删除'))

        if not self.msg_id:
            raise UserError(_(u'该群发不存在msg_id'))

        timeArray = time.strptime(self.send_time, DEFAULT_SERVER_DATETIME_FORMAT)
        time_stamp = int(time.mktime(timeArray))
        if int(time.time()) - time_stamp >= 1800:
            raise UserError(_(u'群发只有在刚发出的半小时内可以删除，发出半小时之后将无法被删除'))

        o = self.app_id
        client_obj = Client(self.pool, self._cr, o.id, o.appid, o.appsecret, o.access_token, o.token_expires_at)
        json = client_obj.send_preview_del_msg_id(self.msg_id)

        if "errcode" in json and json["errcode"] != 0:
            raise UserError(_(json["errmsg"]))
        else:
            self.state = 'delete'

        return

    @api.multi
    def get_state_button(self):

        if not self.msg_id:
            raise UserError(_(u'该群发不存在msg_id'))

        o = self.app_id
        client_obj = Client(self.pool, self._cr, o.id, o.appid, o.appsecret, o.access_token, o.token_expires_at)
        json = client_obj.send_mass_get(self.msg_id)

        if "errcode" in json and json["errcode"] != 0:
            raise UserError(_(json["errmsg"]))
        elif json.get('msg_status', False) == 'SEND_SUCCESS':
            self.state = 'finished'
        else:
            raise UserError(_(u'发送失败'))

        return




# 预览消息
class tl_weixin_preview_message(models.Model):
    _name = 'tl.weixin.preview.message'
    _description = u"预览消息"
    _rec_name = 'app_id'

    app_id = fields.Many2one('tl.weixin.app', required=True, string=u'微信公众号', help=u'发送消息的公众号')
    company_id = fields.Many2one('res.company', u'公司', default=lambda self: self.env.user.company_id, help=u"所属公司")
    user_id = fields.Many2one('tl.weixin.users',string=u'用户', help=u'接受预览消息的用户')
    material_id = fields.Many2one('tl.weixin.material', string=u'素材', help=u"群发选择的素材")
    msgtype = fields.Selection(
        [('mpnews', u'图文'), ('text', u'文本'), ('voice', u'语音'),
         ('image', u'图片'), ('mpvideo', u'视频'), ('wxcard', u'卡券消息')], string=u'消息类型',
        required=True, default='mpnews',
        help=u"素材的类型，图文（mpnews）、文本（text） 语音 （voice）、图片（image）、视频（mpvideo）、卡券消息（wxcard）")
    content = fields.Text(u'文本消息内容')
    state = fields.Selection([('draft', u'草稿'), ('send', u'已发送'), ('finished', u'已送达'), ('failed', u'发送失败'),
                              ('cancel', u'无效')], u'状态', default='draft', required=True, readonly=True)
    send_time = fields.Datetime(u'消息发送时间')
    errcode = fields.Char(string=u'错误码', help=u"错误码")
    errmsg = fields.Char(string=u'错误信息', help=u"错误信息")
    msg_id = fields.Char(string=u'消息发送任务ID', help=u"消息发送任务的ID")


    @api.onchange('app_id','msgtype')
    def _onchange_app_id_msgtype(self):
        if self.app_id:
            user_ids = [user.id for user in self.app_id.user_ids]

            if self.msgtype == 'mpnews':
                domain = [('app_id','=',self.app_id.id),('type','=','news')]
            elif self.msgtype == 'voice':
                domain = [('app_id','=',self.app_id.id),('type','=','voice')]
            elif self.msgtype == 'image':
                domain = [('app_id','=',self.app_id.id),('type','=','image')]
            elif self.msgtype == 'voice':
                domain = [('app_id','=',self.app_id.id),('type','=','voice')]
            elif self.msgtype == 'mpvideo':
                domain = [('app_id','=',self.app_id.id),('type','=','video')]

            # NEXT 'wxcard'还未开发，所以此处先不做筛选

            elif self.msgtype in ['text','wxcard',]:
                domain = [('app_id','=',self.app_id.id)]

            materials = self.env['tl.weixin.material'].search(domain)
            material_ids = [material.id for material in materials]

            return {'domain':{
                              'user_id':[('id','in', user_ids)],
                              'material_id':[('id','in',material_ids)]
                              }}


    @api.multi
    def send_preview_message_button(self):
        o = self.app_id
        client_obj = Client(self.pool, self._cr, o.id, o.appid, o.appsecret, o.access_token, o.token_expires_at)

        content = ''
        # 根据消息类型配置对应的数据
        if self.msgtype == 'text':
            content = self.content
        elif self.msgtype in ['image','voice', 'mpnews']:
            # 针对图文信息暂时定为用永久图文素材库中的
            content = self.material_id.media_id
        elif self.msgtype == 'mpvideo':
            raise UserError(_(u'视频发送还在完善中'))

            # NEXT 此处接口需要确认，我任务接口中将变量写成了常量字符串
            # 如果是上传的视频，此处视频的media_id需通过POST请求到下述接口特别地得到
            # https://file.api.weixin.qq.com/cgi-bin/media/uploadvideo?access_token=ACCESS_TOKEN
            json = client_obj.uploadvideo(self.material_id.media_id, self.title, self.description)
            if "errcode" in json and json["errcode"] != 0:
                raise UserError(_(json["errmsg"]))
            else:
                content = json['media_id']
        elif self.msgtype == 'wxcard':
            # 卡券接口还没写
            raise UserError(_(u'暂不支持卡券'))


        json = client_obj.send_preview(self.user_id.openid, self.msgtype, content)
        if "errcode" in json and json["errcode"] != 0:
            raise UserError(_(json["errmsg"]))
        else:
            self.state = 'send'
            self.errcode = json.get('errcode', '')
            self.errmsg = json.get('errmsg', '')
            self.msg_id = json.get('msg_id', '')
            self.send_time = datetime.now()

        return

# 客服账号
class tl_weixin_kfaccount(models.Model):
    _name = 'tl.weixin.kfaccount'
    _description = u"客服账号"
    _rec_name = 'kf_account'

    app_id = fields.Many2one('tl.weixin.app', required=True, string=u'微信公众号', help=u'发送消息的公众号')
    company_id = fields.Many2one('res.company', u'公司', default=lambda self: self.env.user.company_id, help=u"所属公司")

    kf_account = fields.Char(string=u'客服账号', required=True, help=u"完整客服账号，格式为：账号前缀@公众号微信号")
    kf_id = fields.Char(string=u'客服工号', help=u"客服工号")
    kf_nick = fields.Char(string=u'客服昵称', required=True, help=u"客服昵称，最长6个汉字或12个英文字符")
    password = fields.Char(string=u'客服密码', help=u"客服账号登录密码，格式为密码明文的32位加密MD5值。该密码仅用于在公众平台官网的多客服功能中使用，若不使用多客服功能，则不必设置密码")

    kf_headimgurl = fields.Text(string=u'头像url', help=u"头像图片文件必须是jpg格式，推荐使用640*640大小的图片以达到最佳效果")
    image = openerp.fields.Binary(string=u"图片", attachment=True,
                                  help=u"头像图片文件必须是jpg格式，推荐使用640*640大小的图片以达到最佳效果")

    @api.onchange('app_id')
    def _onchange_app_id(self):
        if self.app_id:
            if self.app_id.account_name:
                self.kf_account = '@' + self.app_id.account_name
            else:
                raise UserError(_(u'该账号不存在有效的微信号，请先设置微信号'))

        return




    @api.model
    def create(self, vals):
        auto = vals.has_key('auto')

        if auto:
            vals.pop('auto')

        if not auto:

            # 增加判断账号格式,客服帐号名包含非法字符(仅允许英文+数字)(illegal character in kf_account)
            kf_account = vals['kf_account']
            account_name = self.env['tl.weixin.app'].search([('id', '=', vals['app_id'])]).account_name

            if not account_name:
                raise UserError(_(u'该账号不存在有效的微信号，请先设置微信号'))


            pat = r'^\w+@' + account_name + r'$'
            if not re.search(pat, kf_account):
                raise UserError(_(u'客服账号的格式为：账号前缀@公众号的微信号, 账号前缀仅允许英文+数字，前缀不能为空'))

            app_id = vals.get('app_id')
            o = self.env["tl.weixin.app"].browse(app_id)
            client_obj = Client(self.pool, self._cr, o.id, o.appid, o.appsecret, o.access_token, o.token_expires_at)

            # 对密码处理
            if vals.get('password', False):
                m = hashlib.md5()
                m.update(vals['password'])
                password = m.hexdigest()
            else:
                password = ''

            json = client_obj.add_kfaccount(kf_account, vals['kf_nick'], password)

            if "errcode" in json and json["errcode"] != 0:
                raise UserError(_(json["errmsg"]))

            #设置头像
            if vals.get('image', False):
                url = self.set_headimg(app_id, vals.get('image'))
                if url:
                    vals['url'] = url
                else:
                    raise UserError(_(u'设置头像错误'))

        return super(tl_weixin_kfaccount, self).create(vals)


    # TODO 修改和删除　还没调试好，　官方文档说明不清楚
    @api.multi
    def write(self, vals):
        auto = vals.has_key('auto')

        if auto:
            vals.pop('auto')

        if not auto:
            o = self.app_id
            client_obj = Client(self.pool, self._cr, o.id, o.appid, o.appsecret, o.access_token, o.token_expires_at)

            if vals.get('kf_account', False) or vals.get('kf_nick', False) or vals.get('password', False):
                #判断是否修改了客服账号
                if vals.get('kf_account', False):
                    kf_account = vals.get('kf_account')
                else:
                    kf_account = self.kf_account

                #判断是否修改了客服昵称
                if vals.get('kf_nick', False):
                    kf_nick = vals.get('kf_nick')
                else:
                    kf_nick = self.kf_nick


                # 判断是否存在微信号
                account_name = self.app_id.account_name
                if not account_name:
                    raise UserError(_(u'该账号不存在有效的微信号，请先设置微信号'))

                pat = r'^\w+@' + account_name + r'$'
                if not re.search(pat, kf_account):
                    raise UserError(_(u'客服账号的格式为：账号前缀@公众号的微信号, 账号前缀仅允许英文+数字，前缀不能为空'))


                # 对密码处理
                if vals.get('password', False):
                    m = hashlib.md5()
                    m.update(vals['password'])
                    password = m.hexdigest()
                elif self.password:
                    password = self.password
                else:
                    password = ''


                json = client_obj.update_kfaccount(kf_account, kf_nick, password)

                if "errcode" in json and json["errcode"] != 0:
                    raise UserError(_(json["errmsg"]))

            #设置头像

            if vals.get('image', False):
                url = self.set_headimg(o.id, vals.get('image'))
                if url:
                    vals['url'] = url
                else:
                    raise UserError(_(u'设置头像错误'))

        return super(tl_weixin_kfaccount, self).write(vals)


    # TODO　所有的删除得考虑一个问题，如果本地有数据，而服务器没有，这是点击删除，本地的会删不掉
    # 同样的，如果将super移动到前面, 会导致本地删掉，服务器出错的话服务器就没有删掉
    @api.multi
    def unlink(self):

        o = self.app_id
        client_obj = Client(self.pool, self._cr, o.id, o.appid, o.appsecret, o.access_token, o.token_expires_at)

        if self.password:
            m = hashlib.md5()
            m.update(self.password)
            password = m.hexdigest()
        else:
            password = ''

        json = client_obj.delete_kfaccount(self.kf_account, self.kf_nick, password)

        if "errcode" in json and json["errcode"] != 0:
            raise UserError(_(json["errmsg"]))

        return super(tl_weixin_kfaccount, self).unlink()

    @api.multi
    def set_headimg(self, app_id, binary_img):

        o = self.env['tl.weixin.app'].browse(int(app_id))
        client_obj = Client(self.pool, self._cr, o.id, o.appid, o.appsecret, o.access_token, o.token_expires_at)

        src = binary_img
        image_stream = StringIO.StringIO(src.decode('base64'))
        image = Image.open(image_stream)

        file_format = image.format
        if file_format not in ('JPG','JPEG'):
            raise UserError(_(u'图片格式限定 JPG/JPEG'))

        output = StringIO.StringIO()
        image.save(output, file_format)
        output.seek(0)
        output_s = output.read()


        # 临时文件名
        file_name = '%s.%s' % ('temp1', file_format)
        json = client_obj.headimg_kfaccount(self.kf_account, file_name, image_stream)
        image_stream.close()
        output.close()

        if "errcode" in json and json["errcode"] != 0:
            raise UserError(_(json["errmsg"]))
        else:
            return json['url']

# 客服消息
class tl_weixin_kfaccount_message(models.Model):
    _name = 'tl.weixin.kfaccount.message'
    _description = u"客服消息"
    _rec_name = 'app_id'

    app_id = fields.Many2one('tl.weixin.app', required=True, string=u'微信公众号', help=u'发送消息的公众号')
    company_id = fields.Many2one('res.company', u'公司', default=lambda self: self.env.user.company_id, help=u"所属公司")
    user_id = fields.Many2one('tl.weixin.users',string=u'关注者', help=u'接受预览消息的用户')
    kf_id = fields.Many2one('tl.weixin.kfaccount', string=u'客服', help=u'以哪个客服账号发送消息')
    material_id = fields.Many2one('tl.weixin.material', string=u'素材', help=u"群发选择的素材")
    msgtype = fields.Selection(
        [('mpnews', u'图文'), ('text', u'文本'), ('voice', u'语音'),
         ('image', u'图片'), ('mpvideo', u'视频'), ('wxcard', u'卡券消息')], string=u'消息类型',
        required=True, default='mpnews',
        help=u"素材的类型，图文（mpnews）、文本（text） 语音 （voice）、图片（image）、视频（mpvideo）、卡券消息（wxcard）")
    content = fields.Text(u'文本消息内容')
    state = fields.Selection([('draft', u'草稿'), ('send', u'已发送'), ('finished', u'已送达'), ('failed', u'发送失败'),
                              ('cancel', u'无效')], u'状态', default='draft', required=True, readonly=True)
    send_time = fields.Datetime(u'消息发送时间')
    errcode = fields.Char(string=u'错误码', help=u"错误码")
    errmsg = fields.Char(string=u'错误信息', help=u"错误信息")
    msg_id = fields.Char(string=u'消息发送任务ID', help=u"消息发送任务的ID")


    @api.onchange('app_id','msgtype')
    def _onchange_app_id_msgtype(self):
        if self.app_id:
            user_ids = [user.id for user in self.app_id.user_ids]

            if self.msgtype == 'mpnews':
                domain = [('app_id','=',self.app_id.id),('type','=','news')]
            elif self.msgtype == 'voice':
                domain = [('app_id','=',self.app_id.id),('type','=','voice')]
            elif self.msgtype == 'image':
                domain = [('app_id','=',self.app_id.id),('type','=','image')]
            elif self.msgtype == 'voice':
                domain = [('app_id','=',self.app_id.id),('type','=','voice')]
            elif self.msgtype == 'mpvideo':
                domain = [('app_id','=',self.app_id.id),('type','=','video')]

            # NEXT 'wxcard'还未开发，所以此处先不做筛选

            elif self.msgtype in ['text','wxcard',]:
                domain = [('app_id','=',self.app_id.id)]

            materials = self.env['tl.weixin.material'].search(domain)
            material_ids = [material.id for material in materials]

            kf_accounts = self.env['tl.weixin.kfaccount'].search([('app_id', '=', int(self.app_id.id))])
            kf_ids = [kf_account.id for kf_account in kf_accounts]

            return {'domain':{
                              'user_id':[('id', 'in', user_ids)],
                              'material_id': [('id', 'in', material_ids)],
                              'kf_id': [('id', 'in', kf_ids)]
                              }}



    @api.multi
    def send_kfaccount_message_button(self):
        o = self.app_id
        client_obj = Client(self.pool, self._cr, o.id, o.appid, o.appsecret, o.access_token, o.token_expires_at)

        if self.kf_id:
            kf_account = self.kf_id.kf_account
        else:
            kf_account = False

        content = ''
        # 根据消息类型配置对应的数据
        if self.msgtype == 'text':
            content = self.content
            json = client_obj.send_text_message(self.user_id.openid, content, kf_account)

        elif self.msgtype == 'image':
            media_id = self.material_id.media_id
            json = client_obj.send_image_message(self.user_id.openid, media_id, kf_account)

        elif self.msgtype == 'voice':
            media_id = self.material_id.media_id
            json = client_obj.send_voice_message(self.user_id.openid, media_id, kf_account)

        elif self.msgtype == 'video':
            raise UserError(_(u'视频发送还在完善中'))

        elif self.msgtype == 'music':
            raise UserError(_(u'音乐发送还在完善中'))

        elif self.msgtype == 'wxcard':
            # 卡券接口还没写
            raise UserError(_(u'暂不支持卡券'))

        elif self.msgtype == 'mpnews':
            # TODO 图文消息有两种, 我只写了一种，另外一种需改动数据结构，要重写页面
            #     点击跳转到外链
            #     点击跳转到图文消息页面
            media_id = self.material_id.media_id
            json = client_obj.send_mpnews_message(self.user_id.openid, media_id, kf_account)

        if "errcode" in json and json["errcode"] != 0:
            raise UserError(_(json["errmsg"]))
        else:
            self.state = 'send'
            self.errcode = json.get('errcode', '')
            self.errmsg = json.get('errmsg', '')
            self.msg_id = json.get('msg_id', '')
            self.send_time = datetime.now()

        return


# 菜单
class tl_weixin_menu(models.Model):
    _name = 'tl.weixin.menu'
    _description = u"自定义菜单"
    _rec_name = 'app_id'


    app_id = fields.Many2one('tl.weixin.app', required=True, string=u'微信公众号', help=u'发送消息的公众号')
    company_id = fields.Many2one('res.company', u'公司', default=lambda self: self.env.user.company_id, help=u"所属公司")

    button_ids = fields.One2many('tl.weixin.menu.button', 'menu_id', string=u'菜单')

    menuid = fields.Char(string=u'菜单ID',  help=u"菜单在服务器的ID")

    is_conditional = fields.Boolean(string=u'是否是个性化菜单', default=False)

    group_id = fields.Many2one('tl.weixin.users.groups', string=u'组')
    sex = fields.Selection([('1', u'男'), ('2', u'女')], string=u'性别', help=u"性别：男（1）女（2），不填则不做匹配")
    country_id = fields.Many2one('tl.weixin.country', string=u'国家')
    province_id = fields.Many2one('tl.weixin.province', string=u'省份')
    city_id = fields.Many2one('tl.weixin.city', string=u'城市')
    client_platform_type = fields.Selection([('1', u'IOS'), ('2', u'Android'), ('3', u'Others')], string=u'客户端版本')
    language = fields.Selection([('zh_CN', u'简体中文'), ('zh_TW', u'繁体中文TW' ), ('zh_HK', u'繁体中文HK'),
                                 ('en', u'英文'), ('id', u'印尼'), ('ms', u'马来 '),
                                 ('es', u'西班牙'), ('ko', u'韩国'), ('it', u'意大利'),
                                 ('ja', u'日本'), ('pl', u'波兰'), ('pt', u'葡萄牙'),
                                 ('ru', u'俄国'), ('th', u'泰文'), ('vi', u'越南'),
                                 ('ar', u'阿拉伯语'), ('hi', u'北印度'), ('he', u'希伯来'),
                                 ('tr', u'土耳其'), ('de', u'德语 '), ('fr', u'法语'),
                                 ], string=u'语言信息')


    # 选择公众号筛选分组
    @api.onchange('app_id')
    def _onchange_app_id(self):
        if self.app_id:

            groups = self.env['tl.weixin.users.groups'].search([('app_id', '=', self.app_id.id)])
            group_ids = [group.id for group in groups]

            return {'domain':{'group_id':[('id','in',group_ids)]}}

    # 根据国家筛选省份
    @api.onchange('country_id')
    def _onchange_country_id(self):
        if self.country_id:

            provinces = self.env['tl.weixin.province'].search([('country_id', '=', self.country_id.id)])
            province_ids = [province.id for province in provinces]

            return {'domain':{'province_id':[('id','in',province_ids)]}}
        else:

            return {'domain':{'province_id':[('id','in',[])]}}

    # 根据身份筛选城市
    @api.onchange('province_id')
    def _onchange_province_id(self):
        if self.province_id:

            citys = self.env['tl.weixin.city'].search([('province_id', '=', self.province_id.id)])
            city_ids = [city.id for city in citys]

            return {'domain':{'city_id':[('id','in',city_ids)]}}
        else:

            return {'domain':{'city_id':[('id','in',[])]}}






    @api.model
    def create(self, vals):
        auto = vals.has_key('auto')

        if auto:
            vals.pop('auto')

        if not auto:

            if vals.get('is_conditional', False) and not vals.get('group_id', False) and not vals.get('sex', False) \
            and not vals.get('country_id', False) and not vals.get('province_id', False) and not vals.get('city_id', False) \
            and not vals.get('client_platform_type', False) and not vals.get('language', False):
                raise UserError(_(u'个性化菜单的个性化选项不能都为空'))

            menu_obj = super(tl_weixin_menu, self).create(vals)

            app_id = vals.get('app_id')
            o = self.env["tl.weixin.app"].browse(app_id)
            client_obj = Client(self.pool, self._cr, o.id, o.appid, o.appsecret, o.access_token, o.token_expires_at)

            menu_data = {"button":[]}

            for each_button in menu_obj.button_ids:
                if each_button.child_ids:
                    # 存在二级菜单
                    sub_vals_lst = []
                    for each_sub in each_button.child_ids:
                        # 根据菜单类型生产相应的data
                        if each_sub.type == 'view':
                            sub_vals = {
                                "type": "view",
                                "name": each_sub.name,
                                "url": each_sub.url
                            }
                        elif each_sub.type == 'click':
                            sub_vals = {
                                "type": "click",
                                "name": each_sub.name,
                                "key": each_sub.key.value
                            }
                        elif each_sub.type == 'scancode_push':
                            sub_vals = {
                                "type": "scancode_push",
                                "name": each_sub.name,
                                "key": each_sub.key.value,
                                "sub_button": []
                            }
                        elif each_sub.type == 'scancode_waitmsg':
                            sub_vals = {
                                "type": "scancode_waitmsg",
                                "name": each_sub.name,
                                "key": each_sub.key.value,
                                "sub_button": []
                            }
                        elif each_sub.type == 'pic_sysphoto':
                            sub_vals = {
                                "type": "pic_sysphoto",
                                "name": each_sub.name,
                                "key": each_sub.key.value,
                                "sub_button": []
                            }
                        elif each_sub.type == 'pic_photo_or_album':
                            sub_vals = {
                                "type": "pic_photo_or_album",
                                "name": each_sub.name,
                                "key": each_sub.key.value,
                                "sub_button": []
                            }
                        elif each_sub.type == 'pic_weixin':
                            sub_vals = {
                                "type": "pic_weixin",
                                "name": each_sub.name,
                                "key": each_sub.key.value,
                                "sub_button": []
                            }
                        elif each_sub.type == 'location_select':
                            sub_vals = {
                                "type": "pic_weixin",
                                "name": each_sub.name,
                                "media_id": each_sub.media_id.media_id
                            }
                        elif each_sub.type == 'media_id':
                            sub_vals = {
                                "type": "media_id",
                                "name": each_sub.name,
                                "media_id": each_sub.media_id.media_id
                            }
                        elif each_sub.type == 'view_limited':
                            sub_vals = {
                                "type": "view_limited",
                                "name": each_sub.name,
                                "media_id": each_sub.media_id.media_id
                            }



                        sub_vals_lst.append(sub_vals)

                    menu_data["button"].append({
                        "name": each_button.name,
                        "sub_button": sub_vals_lst
                    })
                else:
                    # 这个菜单没有二级菜单,只有一级的
                    
                    if each_button.type == 'view':
                            button_vals = {
                                "type": "view",
                                "name": each_button.name,
                                "url": each_button.url
                            }
                    elif each_button.type == 'click':
                        button_vals = {
                            "type": "click",
                            "name": each_button.name,
                            "key": each_button.key.value
                        }
                    elif each_button.type == 'scancode_push':
                        button_vals = {
                            "type": "scancode_push",
                            "name": each_button.name,
                            "key": each_button.key.value,
                            "sub_button": []
                        }
                    elif each_button.type == 'scancode_waitmsg':
                        button_vals = {
                            "type": "scancode_waitmsg",
                            "name": each_button.name,
                            "key": each_button.key.value,
                            "sub_button": []
                        }
                    elif each_button.type == 'pic_sysphoto':
                        button_vals = {
                            "type": "pic_sysphoto",
                            "name": each_button.name,
                            "key": each_button.key.value,
                            "sub_button": []
                        }
                    elif each_button.type == 'pic_photo_or_album':
                        button_vals = {
                            "type": "pic_photo_or_album",
                            "name": each_button.name,
                            "key": each_button.key.value,
                            "sub_button": []
                        }
                    elif each_button.type == 'pic_weixin':
                        button_vals = {
                            "type": "pic_weixin",
                            "name": each_button.name,
                            "key": each_button.key.value,
                            "sub_button": []
                        }
                    elif each_button.type == 'location_select':
                        button_vals = {
                            "type": "pic_weixin",
                            "name": each_button.name,
                            "media_id": each_button.media_id.media_id
                        }
                    elif each_button.type == 'media_id':
                        button_vals = {
                            "type": "media_id",
                            "name": each_button.name,
                            "media_id": each_button.media_id.media_id
                        }
                    elif each_button.type == 'view_limited':
                        button_vals = {
                            "type": "view_limited",
                            "name": each_button.name,
                            "media_id": each_button.media_id.media_id
                        }


                    menu_data["button"].append(button_vals)



            if menu_obj.is_conditional:
                # 这是一个个性化菜单
                menu_data['matchrule'] = {
                    "group_id": menu_obj.group_id.groupid or '',
                    "sex": menu_obj.sex or '',
                    "country": menu_obj.country_id.name or '',
                    "province": menu_obj.province_id.name or '',
                    "city": menu_obj.city_id.name or '',
                    "client_platform_type": menu_obj.client_platform_type or '',
                    "language": menu_obj.language or ''
                }
                json = client_obj.create_conditional_menu(menu_data)
            else:

                json = client_obj.create_menu(menu_data)


            if "errcode" in json and json["errcode"] != 0:
                raise UserError(_(json["errmsg"]))
            else:
                if menu_obj.is_conditional:
                    # 这是一个个性化菜单
                    menu_obj.menuid = json.get('menuid', '')
            return menu_obj

        else:

            return super(tl_weixin_menu, self).create(vals)


    @api.multi
    def delete_conditional_menu(self):
        if not self.menuid:
            raise UserError(_(u'该个性化菜单不存在有效的menuid'))

        o = self.app_id
        client_obj = Client(self.pool, self._cr, o.id, o.appid, o.appsecret, o.access_token, o.token_expires_at)
        json = client_obj.delete_conditional_menu(self.menuid)
        if "errcode" in json and json["errcode"] != 0:
            raise UserError(_(json["errmsg"]))
        else:
            self.unlink()

        return





# 菜单按钮
class tl_weixin_menu_button(models.Model):
    _name = 'tl.weixin.menu.button'
    _description = u"自定义菜单按钮"
    _rec_name = 'menu_id'

    menu_id = fields.Many2one('tl.weixin.menu', string=u'菜单')

    type = fields.Selection(
        [('click', u'点击推事件'), ('view', u'跳转URL'), ('scancode_push', u'扫码推事件'),
         ('scancode_waitmsg', u'扫码推事件且弹出“消息接收中”提示框'), ('pic_sysphoto', u'弹出系统拍照发图'),
         ('pic_photo_or_album', u'弹出拍照或者相册发图'), ('pic_weixin', u'弹出微信相册发图器'),
         ('location_select', u'弹出地理位置选择器'), ('media_id', u'下发消息（除文本消息)'), ('view_limited', u'跳转图文消息URL')],
        string=u'消息类型', required=True, help=u"自定义菜单接口可实现多种类型按钮")

    name = fields.Char(string=u'菜单标题', help=u"菜单标题，不超过16个字节，子菜单不超过40个字节")
    # key = fields.Char(string=u'菜单KEY值', size=128, help=u"菜单KEY值，用于消息接口推送，不超过128字节")
    key = fields.Many2one('tl.weixin.eventkey', string=u'菜单KEY值', size=128, help=u"菜单KEY值，用于消息接口推送，不超过128字节")
    url = fields.Char(string=u'网页链接', size=1024, help=u"网页链接，用户点击菜单可打开链接，不超过1024字节")
    media_id = fields.Many2one('tl.weixin.material', string=u'素材ID', help=u'调用新增永久素材接口返回的合法media_id')

    parent_id = fields.Many2one('tl.weixin.menu.button', string=u'上级菜单')
    child_ids = fields.One2many('tl.weixin.menu.button', 'parent_id', string=u'下级菜单')

    @api.onchange('type')
    def _onchange_app_id(self):
        if self.type == 'view':
            self.url = 'http://'
        return




class tl_weixin_country(models.Model):
    _name = 'tl.weixin.country'
    _rec_name = 'name'

    name = fields.Char(u'国家')
    name_en = fields.Char(u'英文名称')


class tl_weixin_province(models.Model):
    _name = 'tl.weixin.province'
    _rec_name = 'name'

    name = fields.Char(u'省份')
    name_en = fields.Char(u'英文名称')
    country_id = fields.Many2one('tl.weixin.country')


class tl_weixin_city(models.Model):
    _name = 'tl.weixin.city'
    _rec_name = 'name'

    name = fields.Char(u'城市')
    name_en = fields.Char(u'英文名称')
    province_id = fields.Many2one('tl.weixin.province')


class tl_weixin_eventkey(models.Model):
    """
    自定义key对应的返回事件,字段可按需求更改
    """
    _name = 'tl.weixin.eventkey'
    _rec_name = 'name'

    @api.multi
    def _get_key(self):

        # 可以根据需要改写,目前采用唯一的时间戳
        return uuid.uuid1()

    app_id = fields.Many2one('tl.weixin.app', required=True, string=u'微信公众号', help=u'发送消息的公众号')
    company_id = fields.Many2one('res.company', u'公司', default=lambda self: self.env.user.company_id, help=u"所属公司")
    name = fields.Char(u'Key名称', required=True)
    value = fields.Char(string=u'Key值', default=_get_key, required=True)
    menu_type = fields.Selection(
        [('click', u'点击推事件'), ('view', u'跳转URL'), ('scancode_push', u'扫码推事件'),
         ('scancode_waitmsg', u'扫码推事件且弹出“消息接收中”提示框'), ('pic_sysphoto', u'弹出系统拍照发图'),
         ('pic_photo_or_album', u'弹出拍照或者相册发图'), ('pic_weixin', u'弹出微信相册发图器'),
         ('location_select', u'弹出地理位置选择器'), ('media_id', u'下发消息（除文本消息)'), ('view_limited', u'跳转图文消息URL')],
        string=u'点击的自定义菜单类型', help=u"点击的自定义菜单类型")
    reply_type = fields.Selection(
        [('mpnews', u'图文'), ('text', u'文本'), ('voice', u'语音'),
         ('image', u'图片'), ('mpvideo', u'视频'), ('wxcard', u'卡券消息')], string=u'消息类型',
        help=u"素材的类型，图文（mpnews）、文本（text） 语音 （voice）、图片（image）、视频（mpvideo）、卡券消息（wxcard）")
    text = fields.Text(u'文本信息内容')
    media_id = fields.Many2one('tl.weixin.material')


    _sql_constraints = [
                        ('value_uniq', 'unique(value)', 'value值唯一'),

                    ]

class tl_weixin_matchmenu(models.Model):
    """
    测试个性化菜单是否能匹配成功
    选择用户,点击测试匹配,则可以大致预览到该用户看到的菜单是哪个(主要用来查看该用户是否能看到个性化菜单)
    """
    _name = 'tl.weixin.matchmenu'
    _rec_name = 'app_id'

    app_id = fields.Many2one('tl.weixin.app', required=True, string=u'微信公众号', help=u'发送消息的公众号')
    company_id = fields.Many2one('res.company', u'公司', default=lambda self: self.env.user.company_id, help=u"所属公司")
    user_id = fields.Many2one('tl.weixin.users', required=True, string=u'匹配的用户')
    result_json = fields.Text(string=u'服务器返回的结果')
    result = fields.Text(string=u'匹配的结果')


    @api.multi
    def match_menu_button(self):
        o = self.app_id
        client_obj = Client(self.pool, self._cr, o.id, o.appid, o.appsecret, o.access_token, o.token_expires_at)
        json = client_obj.try_match_menu(self.user_id.openid)

        if "errcode" in json and json["errcode"] != 0:
            raise UserError(_(json["errmsg"]))
        else:
            if not json.get('menu', False):
                raise UserError(u'返回的数据错误')

            menu = json.get('menu')
            if not menu.get('button', False):
                raise UserError(u'返回的数据错误')

            result = '该用户可见的菜单格式为:\n\n'
            for each_button in menu['button']:
                result += '一级菜单:\n'
                result += '名称:' + each_button['name'] + '\n'

                if each_button['sub_button']:
                    # 存在二级菜单
                    for each_sub in each_button['sub_button']:
                        result += '      二级菜单:\n'
                        result += '      名称:' + each_sub['name'] + '\n'
                        result += '      类别:' + each_sub['type'] + '\n'
                        result += '\n'
                else:
                    result += '类别:' + each_button['type'] + '\n'
                    result += '\n'

            self.result_json = json
            self.result = result
        return

    # 选择公众号筛选用户
    @api.onchange('app_id')
    def _onchange_app_id(self):
        if self.app_id:

            users = self.env['tl.weixin.users'].search([('app_id', '=', self.app_id.id)])
            user_ids = [user.id for user in users]

            return {'domain':{'user_id':[('id','in',user_ids)]}}



class tl_weixin_data_wizard(osv.TransientModel):
    """
    获取用户数据的向导
    """
    _name = 'tl.weixin.data.wizard'
    _rec_name = 'app_id'

    # 获取选中的默认账号id
    @api.multi
    def _get_default_app_id(self):

        context = dict(self._context or {})
        app_id = context.get('active_model') == 'tl.weixin.app' and context.get('active_id') or []
        return app_id

    app_id = fields.Many2one('tl.weixin.app', required=True, default=_get_default_app_id,string=u'微信公众号', help=u'发送消息的公众号')
    company_id = fields.Many2one('res.company', u'公司', default=lambda self: self.env.user.company_id, help=u"所属公司")
    begin_date = fields.Date(u'开始日期')
    query_date = fields.Date(u'查询日期')
    end_date = fields.Date(u'结束日期')
    wizard_code = fields.Char(u'向导区分代码')

    @api.model
    def default_get(self, fields_list):
        res = super(tl_weixin_data_wizard, self).default_get(fields_list)
        context = self._context or {}
        if context.get('wizard_code', False):
            res.update({"wizard_code": context.get('wizard_code')})

        return res



    @api.multi
    def get_userdata(self):

        # str格式转化成datetime格式来判断end_time最大为昨天,以及两者只差少于7天
        time_list = []
        for x in [self.begin_date, self.end_date]:
            y, m, d = time.strptime(x, DEFAULT_SERVER_DATE_FORMAT)[0:3]
            time_list.append(datetime(y, m, d))
        begin_date = time_list[0]
        end_date = time_list[1]
        yesterday = (datetime.today() + timedelta(-1))

        if end_date < begin_date:
            raise ValidationError(u'结束日期不能小于开始日期')
        if end_date > yesterday and end_date.day != yesterday.day:
            raise ValidationError(u'结束日期最大为昨天!')
        if end_date - begin_date > timedelta(6):
            raise ValidationError(u'结束日期最多比开始日期多6天!')

        o = self.app_id
        client_obj = Client(self.pool, self._cr, o.id, o.appid, o.appsecret, o.access_token, o.token_expires_at)

        # 先获取用户增减数据
        json1 = client_obj.datacube_getuser_summary(self.begin_date, self.end_date)
        # json1 = {u'list': []}
        if "errcode" in json1 and json1["errcode"] != 0:
            raise ValidationError(_(json1["errmsg"]))
        else:

            # 再获取用户累计用户数据
            json2 = client_obj.datacube_getuser_cumulate(self.begin_date, self.end_date)
            # json2 = {u'list': [{u'user_source': 0, u'cumulate_user': 97, u'ref_date': u'2016-03-22'}, {u'user_source': 0, u'cumulate_user': 97, u'ref_date': u'2016-03-23'}]}
            if "errcode" in json2 and json2["errcode"] != 0:
                raise ValidationError(_(json2["errmsg"]))
            else:

                # 处理两次请求得到的数据,不能直接根据返回的json来循环ref_date,因为,当没有值时,json['list']为空,
                # 微信文档也没说明,几天中如果有一天没数据该如何处理, 所有这里是考虑了这种情况
                # 找出self.begin_date 和self.end_date之间的日期的字符串
                range_list = []
                while begin_date <= end_date:
                    range_list.append(str(begin_date.year) + '-' + str(str(begin_date.month).rjust(2,'0'))+ '-' +str(str(begin_date.day).rjust(2,'0')))
                    begin_date += timedelta(1)

                # vals_list = []
                for each_day in range_list:
                    # 判断tl.weixin.userdata.detail表上是否已经有这天的数据,如果有,则不再再本地生成
                    if self.env['tl.weixin.userdata'].search([('app_id', '=', self.app_id.id),('ref_date', '=', each_day)]):
                        continue

                    user_source = 0
                    cancel_user = 0
                    new_user = 0
                    cumulate_user = 0

                    # 遍历json1找到对应each_day的值
                    if json1['list']:
                        for each1 in json1['list']:
                            if each1['ref_date'] == each_day:
                                user_source = str(each1.get('user_source', 0))
                                cancel_user = each1.get('cancel_user', 0)
                                new_user = each1.get('new_user', 0)

                    # 遍历json2找到对应each_day的值
                    if json2['list']:
                        for each2 in json2['list']:

                            if str(each2['ref_date']) == each_day:
                                cumulate_user = each2.get('cumulate_user', 0)

                    vals = {
                        'ref_date': each_day,
                        'user_source': user_source or '',
                        'new_user': new_user,
                        'cancel_user': cancel_user,
                        'app_id': self.app_id.id,
                        'company_id': self.company_id.id or '',
                        'cumulate_user': cumulate_user,

                    }
                    self.env['tl.weixin.userdata'].create(vals)
        return


    @api.multi
    def get_articlesummary_data(self):

        y, m, d = time.strptime(self.query_date, DEFAULT_SERVER_DATE_FORMAT)[0:3]
        query_date = datetime(y, m , d)
        yesterday = (datetime.today() + timedelta(-1))
        if query_date > yesterday and query_date.day != yesterday.day:
            raise ValidationError(u'查询日期最大为昨天!')

        o = self.app_id
        client_obj = Client(self.pool, self._cr, o.id, o.appid, o.appsecret, o.access_token, o.token_expires_at)

        json = client_obj.datacube_getarticle_summary(self.query_date, self.query_date)
        if "errcode" in json and json["errcode"] != 0:
            raise ValidationError(_(json["errmsg"]))
        else:
            if not json.get('list', False):
                raise UserError(_(u'当天不存在有效数据'))
            else:

                # 判断是否已经存在查询日期这天的数据, 如果有, 则不在获取
                articledata = self.env['tl.weixin.articledata.summary'].search([('app_id', '=', self.app_id.id), ('ref_date', '=', self.query_date)])
                if articledata:
                    raise UserError(_(u'已存在查询日期的有效数据'))

                vals_lst = []
                for each_article in json['list']:
                    # 实际返回数据有user_source字段,API上没有说,也保存起来
                    # 处理msgid
                    msg_data_id = each_article.get('msgid','').split('_')[0]
                    index = each_article.get('msgid','').split('_')[1]
                    obj = self.env['tl.weixin.group.message'].search([('msg_data_id', '=', msg_data_id)])

                    if obj:
                        article_id = obj.material_id.article_ids[index].id
                    else:
                        article_id = ''

                    vals = {
                        "user_source": str(each_article.get('user_source', 5)),
                        "int_page_read_user": each_article.get('int_page_read_user',''),
                        "int_page_read_count": each_article.get('int_page_read_count',''),
                        "ori_page_read_user": each_article.get('ori_page_read_user',''),
                        "ori_page_read_count": each_article.get('ori_page_read_count',''),
                        "share_user": each_article.get('share_user',''),
                        "share_count": each_article.get('share_count',''),
                        "add_to_fav_user": each_article.get('add_to_fav_user',''),
                        "add_to_fav_count": each_article.get('add_to_fav_count',''),
                        'msgid': each_article.get('msgid',''),
                        'article_id': article_id or ''
                    }
                    vals_lst.append((0, 0, vals))

                self.env['tl.weixin.articledata.summary'].create({
                    'app_id': self.app_id.id,
                    "ref_date": query_date,
                    'detail_ids': vals_lst
                })

        return


    @api.multi
    def get_articletotal_data(self):
        # 经试验, 该接口的作用是, 如果某篇文章是1.1号发表的,  现在是2.1号, 那么查询日期选择1.1号,能得到,1.1号以后一共7天该文章的统计数据,
        # 如果选择查询日期为1.2号,那么查询不到有效内容(如果1.2号没有群发的话)

        y, m, d = time.strptime(self.query_date, DEFAULT_SERVER_DATE_FORMAT)[0:3]
        query_date = datetime(y, m , d)
        yesterday = (datetime.today() + timedelta(-1))
        if query_date > yesterday and query_date.day != yesterday.day:
            raise ValidationError(u'查询日期最大为昨天!')

        o = self.app_id
        client_obj = Client(self.pool, self._cr, o.id, o.appid, o.appsecret, o.access_token, o.token_expires_at)

        json = client_obj.datacube_getarticle_total(self.query_date, self.query_date)
        if "errcode" in json and json["errcode"] != 0:
            raise ValidationError(_(json["errmsg"]))
        else:
            if not json.get('list', False):
                raise UserError(_(u'当天不存在有效数据'))
            else:

                # 判断是否已经存在查询日期这天的数据, 如果有, 则不在获取
                articledata = self.env['tl.weixin.articledata.total'].search([('app_id', '=', self.app_id.id), ('ref_date', '=', self.query_date)])
                if articledata:
                    raise UserError(_(u'已存在查询日期的有效数据'))

                vals_lst = []
                for each_day in json['list'][0]['details']:

                    # 测试'stat_date' 能不能用字符串格式直接存比如u'2016-03-16'
                    vals = copy.deepcopy(each_day)
                    # 如果不能,报错的话,把格式处理下

                    vals_lst.append((0, 0, vals))

                # 处理msgid
                msg_data_id = json['list'][0]['msgid'].split('_')[0]
                index = json['list'][0]['msgid'].split('_')[1]
                obj = self.env['tl.weixin.group.message'].search([('msg_data_id', '=', msg_data_id)])

                if obj:
                    article_id = obj.material_id.article_ids[index].id
                else:
                    article_id = ''

                self.env['tl.weixin.articledata.total'].create({
                    'app_id': self.app_id.id,
                    "ref_date": query_date,
                    'title': json['list'][0]['title'],
                    'msgid': json['list'][0]['msgid'],
                    'user_source': str(json['list'][0]['user_source']),
                    'detail_ids': vals_lst,
                    'article_id': article_id or ''
                })

        return


    @api.multi
    def get_userread_data(self):
        # str格式转化成datetime格式来判断end_time最大为昨天,以及两者只差少于3天
        time_list = []
        for x in [self.begin_date, self.end_date]:
            y, m, d = time.strptime(x, DEFAULT_SERVER_DATE_FORMAT)[0:3]
            time_list.append(datetime(y, m, d))
        begin_date = time_list[0]
        end_date = time_list[1]
        yesterday = (datetime.today() + timedelta(-1))

        if end_date < begin_date:
            raise ValidationError(u'结束日期不能小于开始日期')
        if end_date > yesterday and end_date.day != yesterday.day:
            raise ValidationError(u'结束日期最大为昨天!')
        if end_date - begin_date > timedelta(2):
            raise ValidationError(u'结束日期最多比开始日期多2天!')

        o = self.app_id
        client_obj = Client(self.pool, self._cr, o.id, o.appid, o.appsecret, o.access_token, o.token_expires_at)

        # 先获取用户增减数据
        json = client_obj.datacube_getuser_read(self.begin_date, self.end_date)
        # json1 = {u'list': []}
        if "errcode" in json and json["errcode"] != 0:
            raise ValidationError(_(json["errmsg"]))
        else:

            range_list = []
            while begin_date <= end_date:
                range_list.append(str(begin_date.year) + '-' + str(str(begin_date.month).rjust(2,'0'))+ '-' +str(str(begin_date.day).rjust(2,'0')))
                begin_date += timedelta(1)

            for each_day in range_list:
                # 判断tl.weixin.articledata.userread表上是否已经有这天的数据,如果有,则不再再本地生成
                if self.env['tl.weixin.articledata.userread'].search([('app_id', '=', self.app_id.id),('ref_date', '=', each_day)]):
                    continue

                vals_list = []
                for each in json['list']:
                    if each['ref_date'] == each_day:
                        vals = {
                            'user_source':str(each['user_source']),
                            'int_page_read_user':each['int_page_read_user'],
                            'int_page_read_count':each['int_page_read_count'],
                            'ori_page_read_user':each['ori_page_read_user'],
                            'ori_page_read_count':each['ori_page_read_count'],
                            'share_user':each['share_user'],
                            'share_count':each['share_count'],
                            'add_to_fav_user':each['add_to_fav_user'],

                        }
                        vals_list.append((0, 0, vals))

                self.env['tl.weixin.articledata.userread'].create({
                    'app_id': self.app_id.id,
                    'ref_date': each_day,
                    'detail_ids': vals_list
                })
        return

    @api.multi
    def get_userreadhour_data(self):
        y, m, d = time.strptime(self.query_date, DEFAULT_SERVER_DATE_FORMAT)[0:3]
        query_date = datetime(y, m , d)
        yesterday = (datetime.today() + timedelta(-1))
        if query_date > yesterday and query_date.day != yesterday.day:
            raise ValidationError(u'查询日期最大为昨天!')

        o = self.app_id
        client_obj = Client(self.pool, self._cr, o.id, o.appid, o.appsecret, o.access_token, o.token_expires_at)

        json = client_obj.datacube_getuser_readhour(self.query_date, self.query_date)
        if "errcode" in json and json["errcode"] != 0:
            raise ValidationError(_(json["errmsg"]))
        else:
            print json

            
            # 判断tl.weixin.articledata.userreadhour表上是否已经有这天的数据,如果有,则不再再本地生成
            if self.env['tl.weixin.articledata.userreadhour'].search([('app_id', '=', self.app_id.id),('ref_date', '=', self.query_date)]):
                raise ValidationError(u'已存在查询日期的记录')

            # 这里的做法是,如果某个时间断没有记录,则没有在子表建记录
            vals_lst = []
            for each in json['list']:

                vals = {
                    'ref_hour': str(each.get('ref_hour')),
                    'user_source': str(each.get('user_source')),
                    'int_page_read_user': each.get('int_page_read_user'),
                    'int_page_read_count': each.get('int_page_read_count'),
                    'ori_page_read_user': each.get('ori_page_read_user'),
                    'ori_page_read_count': each.get('ori_page_read_count'),
                    'share_user': each.get('share_user'),
                    'share_count': each.get('share_count'),
                    'add_to_fav_user': each.get('add_to_fav_user'),
                    'add_to_fav_count': each.get('add_to_fav_count'),
                    'total_online_time': each.get('total_online_time'),
                }
                vals_lst.append((0, 0, vals))

            self.env['tl.weixin.articledata.userreadhour'].create({
                'app_id': self.app_id.id,
                'ref_date': self.query_date,
                'detail_ids': vals_lst
            })

        return



    @api.multi
    def get_usershare_data(self):

        # str格式转化成datetime格式来判断end_time最大为昨天,以及两者只差少于7天
        time_list = []
        for x in [self.begin_date, self.end_date]:
            y, m, d = time.strptime(x, DEFAULT_SERVER_DATE_FORMAT)[0:3]
            time_list.append(datetime(y, m, d))
        begin_date = time_list[0]
        end_date = time_list[1]
        yesterday = (datetime.today() + timedelta(-1))

        if end_date < begin_date:
            raise ValidationError(u'结束日期不能小于开始日期')
        if end_date > yesterday and end_date.day != yesterday.day:
            raise ValidationError(u'结束日期最大为昨天!')
        if end_date - begin_date > timedelta(6):
            raise ValidationError(u'结束日期最多比开始日期多6天!')

        o = self.app_id
        client_obj = Client(self.pool, self._cr, o.id, o.appid, o.appsecret, o.access_token, o.token_expires_at)

        # 先获取用户增减数据
        json = client_obj.datacube_getuser_share(self.begin_date, self.end_date)
        if "errcode" in json and json["errcode"] != 0:
            raise ValidationError(_(json["errmsg"]))
        else:
            # 处理两次请求得到的数据,不能直接根据返回的json来循环ref_date,因为,当没有值时,json['list']为空,
            # 微信文档也没说明,几天中如果有一天没数据该如何处理, 所有这里是考虑了这种情况
            # 找出self.begin_date 和self.end_date之间的日期的字符串
            range_list = []
            while begin_date <= end_date:
                range_list.append(str(begin_date.year) + '-' + str(str(begin_date.month).rjust(2,'0'))+ '-' +str(str(begin_date.day).rjust(2,'0')))
                begin_date += timedelta(1)

            for each_day in range_list:
                # 判断表上是否已经有这天的数据,如果有,则不再再本地生成
                if self.env['tl.weixin.articledata.usershare'].search([('app_id', '=', self.app_id.id),('ref_date', '=', each_day)]):
                    continue

                vals_list = []
                for each in json['list']:
                    if each['ref_date'] == each_day:
                        vals = {
                            'user_source': str(each['user_source']),
                            'share_count': each['share_count'],
                            'share_user': each['share_user'],
                            'share_scene': each['share_scene'],
                        }
                        
                        vals_list.append((0, 0, vals))

                self.env['tl.weixin.articledata.usershare'].create({
                    'app_id':self.app_id.id,
                    'ref_date': each_day,
                    'detail_ids':vals_list
                })

        return


    @api.multi
    def get_usersharehour_data(self):

        # str格式转化成datetime格式来判断end_time最大为昨天,以及两者只差少于7天
        y, m, d = time.strptime(self.query_date, DEFAULT_SERVER_DATE_FORMAT)[0:3]
        query_date = datetime(y, m , d)
        yesterday = (datetime.today() + timedelta(-1))
        if query_date > yesterday and query_date.day != yesterday.day:
            raise ValidationError(u'查询日期最大为昨天!')

        o = self.app_id
        client_obj = Client(self.pool, self._cr, o.id, o.appid, o.appsecret, o.access_token, o.token_expires_at)

        # 先获取用户增减数据
        json = client_obj.datacube_getuser_sharehour(self.query_date, self.query_date)
        if "errcode" in json and json["errcode"] != 0:
            raise ValidationError(_(json["errmsg"]))
        else:

            if self.env['tl.weixin.articledata.usersharehour'].search([('app_id', '=', self.app_id.id),('ref_date', '=', self.query_date)]):
                raise ValidationError(u'已存在查询日期的记录')

            vals_list = []
            for each in json['list']:
                vals = {
                    'user_source': str(each['user_source']),
                    'ref_hour': str(each['ref_hour']),
                    'share_scene': each['share_scene'],
                    'share_count': each['share_count'],
                    'share_user': each['share_user'],
                }
                vals_list.append((0, 0, vals))

            self.env['tl.weixin.articledata.usersharehour'].create({
                'app_id': self.app_id.id,
                'ref_date': self.query_date,
                'detail_ids': vals_list
            })

        return


    @api.multi
    def get_upstreammsg_data(self):

        # str格式转化成datetime格式来判断end_time最大为昨天,以及两者只差少于7天
        time_list = []
        for x in [self.begin_date, self.end_date]:
            y, m, d = time.strptime(x, DEFAULT_SERVER_DATE_FORMAT)[0:3]
            time_list.append(datetime(y, m, d))
        begin_date = time_list[0]
        end_date = time_list[1]
        yesterday = (datetime.today() + timedelta(-1))

        if end_date < begin_date:
            raise ValidationError(u'结束日期不能小于开始日期')
        if end_date > yesterday and end_date.day != yesterday.day:
            raise ValidationError(u'结束日期最大为昨天!')
        if end_date - begin_date > timedelta(6):
            raise ValidationError(u'结束日期最多比开始日期多6天!')

        o = self.app_id
        client_obj = Client(self.pool, self._cr, o.id, o.appid, o.appsecret, o.access_token, o.token_expires_at)
        json = client_obj.datacube_getupstreammsg(self.begin_date, self.end_date)
        json2 = client_obj.datacube_getupstreammsgdist(self.begin_date, self.end_date)

        if "errcode" in json and json["errcode"] != 0:
            raise ValidationError(_(json["errmsg"]))
        elif "errcode" in json2 and json2["errcode"] != 0:
            raise ValidationError(_(json2["errmsg"]))
        else:
            range_list = []
            while begin_date <= end_date:
                range_list.append(str(begin_date.year) + '-' + str(str(begin_date.month).rjust(2,'0'))+ '-' +str(str(begin_date.day).rjust(2,'0')))
                begin_date += timedelta(1)

            for each_day in range_list:
                # 判断表上是否已经有这天的数据,如果有,则不再再本地生成
                if self.env['tl.weixin.upstreammsg'].search([('app_id', '=', self.app_id.id),('ref_date', '=', each_day)]):
                    continue

                vals_list = []
                for each in json['list']:
                    if each['ref_date'] == each_day:
                        vals = {
                            'user_source': str(each['user_source']),
                            'msg_count': each['msg_count'],
                            'msg_type': each['msg_type'],
                            'msg_user': each['msg_user'],
                        }

                        vals_list.append((0, 0, vals))

                vals2_list = []
                for each2 in json2['list']:
                    if each2['ref_date'] == each_day:
                        vals2 = {
                            'user_source': str(each2['user_source']),
                            'msg_user': each2['msg_user'],
                            'count_interval': str(each2['count_interval']),
                        }

                        vals2_list.append((0, 0, vals2))


                self.env['tl.weixin.upstreammsg'].create({
                    'app_id':self.app_id.id,
                    'ref_date': each_day,
                    'detail_ids': vals_list,
                    'detail2_ids': vals2_list
                })
        return



    @api.multi
    def get_upstreammsghour_data(self):
        pass
        # TODO 思考数据结构怎么样合理
        # TODO 怎么样方式查询合理
        # str格式转化成datetime格式来判断end_time最大为昨天,以及两者只差少于7天
        y, m, d = time.strptime(self.query_date, DEFAULT_SERVER_DATE_FORMAT)[0:3]
        query_date = datetime(y, m , d)
        yesterday = (datetime.today() + timedelta(-1))
        if query_date > yesterday and query_date.day != yesterday.day:
            raise ValidationError(u'查询日期最大为昨天!')

        o = self.app_id
        client_obj = Client(self.pool, self._cr, o.id, o.appid, o.appsecret, o.access_token, o.token_expires_at)

        # 先获取用户增减数据
        json = client_obj.datacube_getupstreammsghour(self.query_date, self.query_date)
        if "errcode" in json and json["errcode"] != 0:
            raise ValidationError(_(json["errmsg"]))
        else:

            if self.env['tl.weixin.upstreammsghour'].search([('app_id', '=', self.app_id.id),('ref_date', '=', self.query_date)]):
                raise ValidationError(u'已存在查询日期的记录')

            vals_list = []
            for each in json['list']:
                vals = {
                    'user_source': str(each['user_source']),
                    'ref_hour': str(each['ref_hour']),
                    'msg_type': each['msg_type'],
                    'msg_user': each['msg_user'],
                    'msg_count': each['msg_count'],
                }
                vals_list.append((0, 0, vals))

            self.env['tl.weixin.upstreammsghour'].create({
                'app_id': self.app_id.id,
                'ref_date': self.query_date,
                'detail_ids': vals_list
            })



    @api.multi
    def get_upstreammsgweek_data(self):

        # str格式转化成datetime格式来判断end_time最大为昨天,以及两者只差少于7天
        time_list = []
        for x in [self.begin_date, self.end_date]:
            y, m, d = time.strptime(x, DEFAULT_SERVER_DATE_FORMAT)[0:3]
            time_list.append(datetime(y, m, d))
        begin_date = time_list[0]
        end_date = time_list[1]
        last_sunday = datetime.today() + timedelta((0-int(begin_date.strftime('%w'))))

        if end_date < begin_date:
            raise ValidationError(u'结束日期不能小于开始日期')
        # 结束日期最大为上周日
        if end_date > last_sunday and end_date.day != last_sunday.day:
            raise ValidationError(u'结束日期最大为上周日!')

        if end_date - begin_date > timedelta(29):
            raise ValidationError(u'结束日期最多比开始日期多29天!')

        o = self.app_id
        client_obj = Client(self.pool, self._cr, o.id, o.appid, o.appsecret, o.access_token, o.token_expires_at)
        json = client_obj.datacube_getupstreammsgweek(self.begin_date, self.end_date)
        json2 = client_obj.datacube_getupstreammsgdistweek(self.begin_date, self.end_date)

        if "errcode" in json and json["errcode"] != 0:
            raise ValidationError(_(json["errmsg"]))
        elif "errcode" in json2 and json2["errcode"] != 0:
            raise ValidationError(_(json2["errmsg"]))
        else:
            # range_list 应当返回日期范围里的星期一
            range_list = []
            while begin_date <= end_date:
                # 找出所选日期范围里的星期一
                # 经测试,如果选择的开始日期在一个星期中,那么这个星期的记录是不被返回的
                # 如果结束的那天在一个星期中间,那么这个星期的记录是被返回的
                if str(begin_date.strftime('%w')) == '1':
                    range_list.append(str(begin_date.year) + '-' + str(str(begin_date.month).rjust(2,'0'))+ '-' +str(str(begin_date.day).rjust(2,'0')))
                begin_date += timedelta(1)

            print range_list
            for each_day in range_list:
                # 判断表上是否已经有这天的数据,如果有,则不再再本地生成
                if self.env['tl.weixin.upstreammsgweek'].search([('app_id', '=', self.app_id.id),('ref_date', '=', each_day)]):
                    continue

                vals_list = []
                for each in json['list']:
                    if each['ref_date'] == each_day:
                        vals = {
                            'user_source': str(each['user_source']),
                            'msg_count': each['msg_count'],
                            'msg_type': each['msg_type'],
                            'msg_user': each['msg_user'],
                        }
                        vals_list.append((0, 0, vals))

                vals2_list = []
                for each2 in json2['list']:
                    if each2['ref_date'] == each_day:
                        vals2 = {
                            'user_source': str(each2['user_source']),
                            'msg_user': each2['msg_user'],
                            'count_interval': str(each2['count_interval']),
                        }
                        vals2_list.append((0, 0, vals2))

                self.env['tl.weixin.upstreammsgweek'].create({
                    'app_id':self.app_id.id,
                    'ref_date': each_day,
                    'detail_ids':vals_list,
                    'detail2_ids':vals2_list
                })
        return


    @api.multi
    def get_upstreammsgmonth_data(self):

        # str格式转化成datetime格式来判断end_time最大为昨天,以及两者只差少于7天
        time_list = []
        for x in [self.begin_date, self.end_date]:
            y, m, d = time.strptime(x, DEFAULT_SERVER_DATE_FORMAT)[0:3]
            time_list.append(datetime(y, m, d))
        begin_date = time_list[0]
        end_date = time_list[1]
        last_month_endday = datetime.today() + timedelta((0-int(datetime.today().day)))
        
        if end_date < begin_date:
            raise ValidationError(u'结束日期不能小于开始日期')
        # 结束日期最大为上月末
        if end_date > last_month_endday and end_date.day != last_month_endday.day:
            raise ValidationError(u'结束日期最大为上月末!')
        
        if end_date - begin_date > timedelta(29):
            raise ValidationError(u'结束日期最多比开始日期多29天!')
        
        o = self.app_id
        client_obj = Client(self.pool, self._cr, o.id, o.appid, o.appsecret, o.access_token, o.token_expires_at)
        json = client_obj.datacube_getupstreammsgmonth(self.begin_date, self.end_date)
        json2 = client_obj.datacube_getupstreammsgdistmonth(self.begin_date, self.end_date)
        
        if "errcode" in json and json["errcode"] != 0:
            raise ValidationError(_(json["errmsg"]))
        if "errcode" in json2 and json2["errcode"] != 0:
            raise ValidationError(_(json2["errmsg"]))
        else:
            # range_list 应当返回日期范围里的星期一
            range_list = []
            while begin_date <= end_date:
                # 找出所选日期范围里的1号
                if int(begin_date.day) == 1:
                    range_list.append(str(begin_date.year) + '-' + str(str(begin_date.month).rjust(2,'0'))+ '-' +str(str(begin_date.day).rjust(2,'0')))
                begin_date += timedelta(1)
        
            for each_day in range_list:
                # 判断表上是否已经有这天的数据,如果有,则不再再本地生成
                if self.env['tl.weixin.upstreammsgmonth'].search([('app_id', '=', self.app_id.id),('ref_date', '=', each_day)]):
                    continue
        
                vals_list = []
                for each in json['list']:
                    if each['ref_date'] == each_day:
                        vals = {
                            'user_source': str(each['user_source']),
                            'msg_count': each['msg_count'],
                            'msg_type': each['msg_type'],
                            'msg_user': each['msg_user'],
                        }
        
                        vals_list.append((0, 0, vals))
                
                vals2_list = []
                for each2 in json2['list']:
                    if each2['ref_date'] == each_day:
                        vals2 = {
                            'user_source': str(each2['user_source']),
                            'msg_user': each2['msg_user'],
                            'count_interval': str(each2['count_interval']),
                        }
        
                        vals2_list.append((0, 0, vals2))
                
        
                self.env['tl.weixin.upstreammsgmonth'].create({
                    'app_id':self.app_id.id,
                    'ref_date': each_day,
                    'detail_ids':vals_list,
                    'detail2_ids':vals2_list,
                })
        return


    @api.multi
    def get_interfacesummary_data(self):
        # str格式转化成datetime格式来判断end_time最大为昨天,以及两者只差少于7天
        time_list = []
        for x in [self.begin_date, self.end_date]:
            y, m, d = time.strptime(x, DEFAULT_SERVER_DATE_FORMAT)[0:3]
            time_list.append(datetime(y, m, d))
        begin_date = time_list[0]
        end_date = time_list[1]
        yesterday = (datetime.today() + timedelta(-1))

        if end_date < begin_date:
            raise ValidationError(u'结束日期不能小于开始日期')
        # 结束日期昨天
        if end_date > yesterday and end_date.day != yesterday.day:
            raise ValidationError(u'结束日期最大为昨天!')

        if end_date - begin_date > timedelta(29):
            raise ValidationError(u'结束日期最多比开始日期多29天!')

        o = self.app_id
        client_obj = Client(self.pool, self._cr, o.id, o.appid, o.appsecret, o.access_token, o.token_expires_at)
        json = client_obj.datacube_getinterfacesummary(self.begin_date, self.end_date)

        if "errcode" in json and json["errcode"] != 0:
            raise ValidationError(_(json["errmsg"]))

        range_list = []
        while begin_date <= end_date:
            # 找出所选日期范围里的每一天
            range_list.append(str(begin_date.year) + '-' + str(str(begin_date.month).rjust(2,'0'))+ '-' +str(str(begin_date.day).rjust(2,'0')))
            begin_date += timedelta(1)

        for each_day in range_list:
            json2 = client_obj.datacube_getinterfacesummaryhour(each_day, each_day)
            if "errcode" in json2 and json2["errcode"] != 0:
                raise ValidationError(_(json2["errmsg"]))

            if self.env['tl.weixin.interfacesummary'].search([('app_id', '=', self.app_id.id),('ref_date', '=', each_day)]):
                continue

            vals_list = []
            for each in json2['list']:
                if each['ref_date'] == each_day:
                    vals = {
                        'total_time_cost': each['total_time_cost'],
                        'max_time_cost': each['max_time_cost'],
                        'fail_count': each['fail_count'],
                        'ref_hour': str(each['ref_hour']),
                        'callback_count': each['callback_count'],
                    }
                    vals_list.append((0, 0, vals))

            self.env['tl.weixin.interfacesummary'].create({
                'app_id':self.app_id.id,
                'ref_date': each_day,
                'hour_ids': vals_list,
                'total_time_cost': each['total_time_cost'],
                'max_time_cost': each['max_time_cost'],
                'fail_count': each['fail_count'],
                'callback_count': each['callback_count'],
            })

        return





### FFFFF

class tl_weixin_userdata(models.Model):
    """
    用户分析数据
    """
    _name = 'tl.weixin.userdata'
    _rec_name = 'ref_date'
    _order = 'ref_date'

    app_id = fields.Many2one('tl.weixin.app', required=True, string=u'微信公众号', help=u'发送消息的公众号')
    company_id = fields.Many2one('res.company', u'公司', default=lambda self: self.env.user.company_id, help=u"所属公司")
    ref_date = fields.Date(u'数据日期')
    # TODO user source 不是指单一用户的吗, 对一个用户群是什么含义
    user_source = fields.Selection(
        [('0', u'其他合计'), ('1', u'公众号搜索'), ('17', u'名片分享'),
         ('30', u'扫描二维码'), ('43', u'图文页右上角菜单'), ('51', u'支付后关注（在支付完成页）'),
         ('57', u'图文页内公众号名称'), ('75', u'公众号文章广告'), ('78', u'表朋友圈广告'),], string=u'用户渠道',
        help=u"0代表其他合计 1代表公众号搜索 17代表名片分享 30代表扫描二维码 43代表图文页右上角菜单 51代表支付后关注（在支付完成页） 57代表图文页内公众号名称 75代表公众号文章广告 78代表朋友圈广告")
    new_user = fields.Integer(u'新增用户数', help=u'新增的用户数量')
    cancel_user = fields.Integer(u'减少用户数', help=u'取消关注的用户数量，新增数减去取消数即为净增用户数量')
    cumulate_user = fields.Integer(u'总用户数', help=u'总用户数量')







class tl_weixin_articledata_summary(models.Model):
    """
    图文群发每日数据
    """
    _name = 'tl.weixin.articledata.summary'
    _rec_name = 'ref_date'
    _order = 'ref_date'

    app_id = fields.Many2one('tl.weixin.app', required=True, string=u'微信公众号', help=u'发送消息的公众号')
    company_id = fields.Many2one('res.company', u'公司', default=lambda self: self.env.user.company_id, help=u"所属公司")
    ref_date = fields.Date(u'数据的日期')
    detail_ids = fields.One2many('tl.weixin.articledata.summary.detail','summary_id')


class tl_weixin_articledata_summary_detail(models.Model):
    """
    图文群发每日数据详细
    """
    _name = 'tl.weixin.articledata.summary.detail'

    _order = 'title'

    summary_id = fields.Many2one('tl.weixin.articledata.summary', cascade='ondelete')
    article_id = fields.Many2one('tl.weixin.articles')
    msgid = fields.Char(u'图文消息Id', help=u'图文消息Id_Article的Index')
    title = fields.Char(u'图文标题')
    user_source = fields.Selection(
        [('0', u'会话'), ('1', u'好友'), ('2', u'朋友圈'),
         ('3', u'腾讯微博'), ('4', u'历史消息'), ('5', u'其它'),], string=u'用户渠道',help=u'代表用户从哪里进入来阅读该图文')
    int_page_read_user = fields.Integer(u'图文页阅读人数', help=u'图文页（点击群发图文卡片进入的页面）的阅读人数')
    int_page_read_count = fields.Integer(u'图文页的阅读次数', help=u'图文页的阅读次数')
    ori_page_read_user = fields.Integer(u'原文页阅读人数', help=u'原文页（点击图文页“阅读原文”进入的页面）的阅读人数，无原文页时此处数据为0')
    ori_page_read_count = fields.Integer(u'原文页的阅读次数', help=u'原文页的阅读次数')
    share_user = fields.Integer(u'分享的人数', help=u'分享的人数')
    share_count = fields.Integer(u'分享的次数', help=u'分享的次数')
    add_to_fav_user = fields.Integer(u'收藏的人数', help=u'收藏的人数')
    add_to_fav_count = fields.Integer(u'收藏的次数', help=u'收藏的次数')









# 获取图文群发总数据
class tl_weixin_articledata_total(models.Model):
    """
    图文群发总数据
    """
    _name = 'tl.weixin.articledata.total'
    _rec_name = 'ref_date'
    _order = 'ref_date'

    app_id = fields.Many2one('tl.weixin.app', required=True, string=u'微信公众号', help=u'发送消息的公众号')
    company_id = fields.Many2one('res.company', u'公司', default=lambda self: self.env.user.company_id, help=u"所属公司")
    ref_date = fields.Date(u'数据的日期')
    title = fields.Char(u'图文标题')
    user_source = fields.Selection(
        [('0', u'会话'), ('1', u'好友'), ('2', u'朋友圈'),
         ('3', u'腾讯微博'), ('4', u'历史消息'), ('5', u'其它'),], string=u'用户渠道',help=u'代表用户从哪里进入来阅读该图文')
    msgid = fields.Char(u'图文消息Id', help=u'图文消息Id_Article的Index')
    article_id = fields.Many2one('tl.weixin.articles')
    detail_ids = fields.One2many('tl.weixin.articledata.total.detail','total_id')


class tl_weixin_articledata_total_detail(models.Model):
    """
    图文群发总数据详细
    """
    _name = 'tl.weixin.articledata.total.detail'

    _order = 'stat_date'

    total_id = fields.Many2one('tl.weixin.articledata.total', cascade='ondelete')

    # 未加中文string=...的值是接口返回的,但文档上没有说明的值
    stat_date = fields.Date(u'截止日期')
    int_page_read_user = fields.Integer(u'图文页阅读人数', help=u'图文页（点击群发图文卡片进入的页面）的阅读人数')
    int_page_read_count = fields.Integer(u'图文页的阅读次数', help=u'图文页的阅读次数')
    ori_page_read_user = fields.Integer(u'原文页阅读人数', help=u'原文页（点击图文页“阅读原文”进入的页面）的阅读人数，无原文页时此处数据为0')
    ori_page_read_count = fields.Integer(u'原文页的阅读次数', help=u'原文页的阅读次数')
    share_user = fields.Integer(u'分享的人数', help=u'分享的人数')
    share_count = fields.Integer(u'分享的次数', help=u'分享的次数')
    add_to_fav_user = fields.Integer(u'收藏的人数', help=u'收藏的人数')
    add_to_fav_count = fields.Integer(u'收藏的次数')
    feed_share_from_feed_user = fields.Integer(u'feed_share_from_feed_user')
    feed_share_from_session_user = fields.Integer(u'feed_share_from_session_user')
    int_page_from_friends_read_count = fields.Integer(u'int_page_from_friends_read_count')
    int_page_from_session_read_user = fields.Integer(u'int_page_from_session_read_user')
    int_page_from_feed_read_count = fields.Integer(u'int_page_from_feed_read_count')
    int_page_from_hist_msg_read_user = fields.Integer(u'int_page_from_hist_msg_read_user')
    int_page_from_friends_read_user = fields.Integer(u'int_page_from_friends_read_user')
    int_page_from_feed_read_user = fields.Integer(u'int_page_from_feed_read_user')
    feed_share_from_other_cnt = fields.Integer(u'feed_share_from_other_cnt')
    int_page_from_hist_msg_read_count = fields.Integer(u'int_page_from_hist_msg_read_count')
    int_page_from_other_read_count = fields.Integer(u'int_page_from_other_read_count')
    feed_share_from_other_user = fields.Integer(u'feed_share_from_other_user')
    int_page_from_other_read_user = fields.Integer(u'int_page_from_other_read_user')
    feed_share_from_session_cnt = fields.Integer(u'feed_share_from_session_cnt')
    target_user = fields.Integer(u'target_user')
    int_page_from_session_read_count = fields.Integer(u'int_page_from_session_read_count')






class tl_weixin_articledata_userread(models.Model):
    """
    获取图文统计数据
    """
    _name = 'tl.weixin.articledata.userread'
    _rec_name = 'ref_date'
    _order = 'ref_date'

    app_id = fields.Many2one('tl.weixin.app', required=True, string=u'微信公众号', help=u'发送消息的公众号')
    company_id = fields.Many2one('res.company', u'公司', default=lambda self: self.env.user.company_id, help=u"所属公司")
    ref_date = fields.Date(u'数据的日期')
    detail_ids = fields.One2many('tl.weixin.articledata.userread.detail', 'userread_id')


class tl_weixin_articledata_userread_detail(models.Model):
    """
    获取图文统计数据详细
    """
    _name = 'tl.weixin.articledata.userread.detail'



    userread_id = fields.Many2one('tl.weixin.articledata.userread', cascade='ondelete')
    user_source = fields.Selection(
        [('0', u'会话'), ('1', u'好友'), ('2', u'朋友圈'),
         ('3', u'腾讯微博'), ('4', u'历史消息'), ('5', u'其它'),], string=u'用户渠道',help=u'代表用户从哪里进入来阅读该图文')
    int_page_read_user = fields.Integer(u'图文页阅读人数', help=u'图文页（点击群发图文卡片进入的页面）的阅读人数')
    int_page_read_count = fields.Integer(u'图文页的阅读次数', help=u'图文页的阅读次数')
    ori_page_read_user = fields.Integer(u'原文页阅读人数', help=u'原文页（点击图文页“阅读原文”进入的页面）的阅读人数，无原文页时此处数据为0')
    ori_page_read_count = fields.Integer(u'原文页的阅读次数', help=u'原文页的阅读次数')
    share_user = fields.Integer(u'分享的人数', help=u'分享的人数')
    share_count = fields.Integer(u'分享的次数', help=u'分享的次数')
    add_to_fav_user = fields.Integer(u'收藏的人数', help=u'收藏的人数')
    add_to_fav_count = fields.Integer(u'收藏的次数', help=u'收藏的次数')



class tl_weixin_articledata_userreadhour(models.Model):
    """
    获取图文统计分时数据
    """
    _name = 'tl.weixin.articledata.userreadhour'
    _rec_name = 'ref_date'
    _order = 'ref_date'

    app_id = fields.Many2one('tl.weixin.app', required=True, string=u'微信公众号', help=u'发送消息的公众号')
    company_id = fields.Many2one('res.company', u'公司', default=lambda self: self.env.user.company_id, help=u"所属公司")
    ref_date = fields.Date(u'数据的日期')
    detail_ids = fields.One2many('tl.weixin.articledata.userreadhour.detail', 'userreadhour_id')


class tl_weixin_articledata_userreadhour_detail(models.Model):
    """
    获取图文统计分时数据详细
    """
    _name = 'tl.weixin.articledata.userreadhour.detail'

    userreadhour_id = fields.Many2one('tl.weixin.articledata.userreadhour', cascade='ondelete')
    ref_hour = fields.Selection(
        [('000', u'[000,100)'), ('100', u'[100,200)'), ('200', u'[200,300)'),
         ('300', u'[300,400)'), ('400', u'[400,500)'), ('500', u'[500,600)'),
        ('600', u'[600,700)'), ('700', u'[700,800)'), ('800', u'[800,900)'),
        ('900', u'[900,1000)'), ('1000', u'[1000,1100)'), ('1100', u'[1100,1200)'),
        ('1200', u'[1200,1300)'), ('1300', u'[1300,1400)'), ('1400', u'[1400,1500)'),
        ('1500', u'[1500,1600)'), ('1600', u'[1600,1700)'), ('1700', u'[1700,1800)'),
        ('1800', u'[1800,1900)'), ('1900', u'[1900,2000)'), ('2000', u'[2000,2100)'),
        ('2100', u'[2100,2200)'), ('2200', u'[2200,2300)'), ('2300', u'[2300,2400)'),],
        string=u'小时数据',help=u'`数据的小时')
    user_source = fields.Selection(
        [('0', u'会话'), ('1', u'好友'), ('2', u'朋友圈'),
         ('3', u'腾讯微博'), ('4', u'历史消息'), ('5', u'其它'),], string=u'用户渠道',help=u'代表用户从哪里进入来阅读该图文')
    int_page_read_user = fields.Integer(u'图文页阅读人数', help=u'图文页（点击群发图文卡片进入的页面）的阅读人数')
    int_page_read_count = fields.Integer(u'图文页的阅读次数', help=u'图文页的阅读次数')
    ori_page_read_user = fields.Integer(u'原文页阅读人数', help=u'原文页（点击图文页“阅读原文”进入的页面）的阅读人数，无原文页时此处数据为0')
    ori_page_read_count = fields.Integer(u'原文页的阅读次数', help=u'原文页的阅读次数')
    share_user = fields.Integer(u'分享的人数', help=u'分享的人数')
    share_count = fields.Integer(u'分享的次数', help=u'分享的次数')
    add_to_fav_user = fields.Integer(u'收藏的人数', help=u'收藏的人数')
    add_to_fav_count = fields.Integer(u'收藏的次数', help=u'收藏的次数')
    total_online_time = fields.Integer(u'total_online_time')



class tl_weixin_articledata_usershare(models.Model):
    """
    获取图文分享转发数据
    """
    _name = 'tl.weixin.articledata.usershare'
    _rec_name = 'ref_date'
    _order = 'ref_date'

    app_id = fields.Many2one('tl.weixin.app', required=True, string=u'微信公众号', help=u'发送消息的公众号')
    company_id = fields.Many2one('res.company', u'公司', default=lambda self: self.env.user.company_id, help=u"所属公司")
    ref_date = fields.Date(u'数据的日期')
    detail_ids = fields.One2many('tl.weixin.articledata.usershare.detail', 'usershare_id')


class tl_weixin_articledata_usershare_detail(models.Model):
    """
    获取图文分享转发数据详细
    """
    _name = 'tl.weixin.articledata.usershare.detail'

    usershare_id = fields.Many2one('tl.weixin.articledata.usershare', cascade='ondelete')
    user_source = fields.Selection([('0', u'会话'), ('1', u'好友'), ('2', u'朋友圈'),('3', u'腾讯微博'),('4', u'历史消息'), ('5', u'其它')],
                                   string=u'用户渠道',help=u'代表用户从哪里进入来阅读该图文')
    share_user = fields.Integer(u'分享的人数', help=u'分享的人数')
    share_count = fields.Integer(u'分享的次数', help=u'分享的次数')
    share_scene = fields.Selection(
        [(1, u'好友转发'), (2, u'朋友圈'), (3, u'腾讯微博'),(255, u'其他'),], string=u'分享的场景',help=u'分享的场景')



class tl_weixin_articledata_usersharehour(models.Model):
    """
    获取图文分享转发分时数据
    """
    _name = 'tl.weixin.articledata.usersharehour'
    _rec_name = 'ref_date'
    _order = 'ref_date'

    app_id = fields.Many2one('tl.weixin.app', required=True, string=u'微信公众号', help=u'发送消息的公众号')
    company_id = fields.Many2one('res.company', u'公司', default=lambda self: self.env.user.company_id, help=u"所属公司")
    ref_date = fields.Date(u'数据的日期')
    detail_ids = fields.One2many('tl.weixin.articledata.usersharehour.detail', 'usersharehour_id')


class tl_weixin_articledata_usersharehour_detail(models.Model):
    """
    获取图文分享转发分时数据详细
    """
    _name = 'tl.weixin.articledata.usersharehour.detail'

    usersharehour_id = fields.Many2one('tl.weixin.articledata.usersharehour', cascade='ondelete')
    user_source = fields.Selection([('0', u'会话'), ('1', u'好友'), ('2', u'朋友圈'),('3', u'腾讯微博'),('4', u'历史消息'), ('5', u'其它')],
                                   string=u'用户渠道',help=u'代表用户从哪里进入来阅读该图文')
    share_user = fields.Integer(u'分享的人数', help=u'分享的人数')
    share_count = fields.Integer(u'分享的次数', help=u'分享的次数')
    share_scene = fields.Selection(
        [(1, u'好友转发'), (2, u'朋友圈'), (3, u'腾讯微博'),(255, u'其他'),], string=u'分享的场景',help=u'分享的场景')
    ref_hour = fields.Selection(
        [('000', u'[000,100)'), ('100', u'[100,200)'), ('200', u'[200,300)'),
         ('300', u'[300,400)'), ('400', u'[400,500)'), ('500', u'[500,600)'),
        ('600', u'[600,700)'), ('700', u'[700,800)'), ('800', u'[800,900)'),
        ('900', u'[900,1000)'), ('1000', u'[1000,1100)'), ('1100', u'[1100,1200)'),
        ('1200', u'[1200,1300)'), ('1300', u'[1300,1400)'), ('1400', u'[1400,1500)'),
        ('1500', u'[1500,1600)'), ('1600', u'[1600,1700)'), ('1700', u'[1700,1800)'),
        ('1800', u'[1800,1900)'), ('1900', u'[1900,2000)'), ('2000', u'[2000,2100)'),
        ('2100', u'[2100,2200)'), ('2200', u'[2200,2300)'), ('2300', u'[2300,2400)'),],
        string=u'小时数据',help=u'数据的小时')
    


# ggg
class tl_weixin_upstreammsg(models.Model):
    """
    获取消息发送概况数据
    """
    _name = 'tl.weixin.upstreammsg'
    _rec_name = 'ref_date'
    _order = 'ref_date'

    app_id = fields.Many2one('tl.weixin.app', required=True, string=u'微信公众号', help=u'发送消息的公众号')
    company_id = fields.Many2one('res.company', u'公司', default=lambda self: self.env.user.company_id, help=u"所属公司")
    ref_date = fields.Date(u'数据的日期')
    detail_ids = fields.One2many('tl.weixin.upstreammsg.detail', 'upstreammsg_id', string=u'消息发送概况数据')
    detail2_ids = fields.One2many('tl.weixin.upstreammsg.detail2', 'upstreammsg_id', string=u'消息发送分布数据')


class tl_weixin_upstreammsg_detail(models.Model):
    """
    获取消息发送概况数据详细
    """
    _name = 'tl.weixin.upstreammsg.detail'

    upstreammsg_id = fields.Many2one('tl.weixin.upstreammsg', cascade='ondelete')
    user_source = fields.Selection([('0', u'会话'), ('1', u'好友'), ('2', u'朋友圈'),('3', u'腾讯微博'),('4', u'历史消息'), ('5', u'其它')],
                                   string=u'用户渠道',help=u'代表用户从哪里进入来阅读该图文')
    msg_type = fields.Selection([(1, u'文字'), (2, u'图片'), (3, u'语音'),(4, u'视频'),(6, u'第三方应用消息（链接消息）'),],
                                string=u'消息类型',help=u'消息类型')
    msg_user = fields.Integer(string=u'用户数', help=u'上行发送了（向公众号发送了）消息的用户数')
    msg_count = fields.Integer(string=u'消息总数', help=u'上行发送了消息的消息总数')


class tl_weixin_upstreammsg_detail2(models.Model):
    """
    获取消息发送分布数据详细
    """
    _name = 'tl.weixin.upstreammsg.detail2'

    upstreammsg_id = fields.Many2one('tl.weixin.upstreammsg', cascade='ondelete')
    user_source = fields.Selection([('0', u'会话'), ('1', u'好友'), ('2', u'朋友圈'),('3', u'腾讯微博'),('4', u'历史消息'), ('5', u'其它')],
                                   string=u'用户渠道',help=u'代表用户从哪里进入来阅读该图文')
    msg_user = fields.Integer(string=u'用户数', help=u'上行发送了（向公众号发送了）消息的用户数')
    count_interval = fields.Selection([('0', u'0'), ('1', u'1-5'), ('2', u'6-10'),('3', u'10次以上'),],
                                string=u'消息量分布区间',help=u'当日发送消息量分布的区间')










class tl_weixin_upstreammsghour(models.Model):
    """
    获取消息发送分时数据
    """
    _name = 'tl.weixin.upstreammsghour'
    _rec_name = 'ref_date'
    _order = 'ref_date'

    app_id = fields.Many2one('tl.weixin.app', required=True, string=u'微信公众号', help=u'发送消息的公众号')
    company_id = fields.Many2one('res.company', u'公司', default=lambda self: self.env.user.company_id, help=u"所属公司")
    ref_date = fields.Date(u'数据的日期')
    detail_ids = fields.One2many('tl.weixin.upstreammsghour.detail', 'upstreammsghour_id')


class tl_weixin_upstreammsghour_detail(models.Model):
    """
    获取消息发送分时数据详细
    """
    _name = 'tl.weixin.upstreammsghour.detail'

    upstreammsghour_id = fields.Many2one('tl.weixin.upstreammsghour', cascade='ondelete')
    user_source = fields.Selection([('0', u'会话'), ('1', u'好友'), ('2', u'朋友圈'),('3', u'腾讯微博'),('4', u'历史消息'), ('5', u'其它')],
                                   string=u'用户渠道',help=u'代表用户从哪里进入来阅读该图文')
    msg_type = fields.Selection([(1, u'文字'), (2, u'图片'), (3, u'语音'),(4, u'视频'),(6, u'第三方应用消息（链接消息）'),],
                                string=u'消息类型',help=u'消息类型')
    msg_user = fields.Integer(string=u'用户数', help=u'上行发送了（向公众号发送了）消息的用户数')
    msg_count = fields.Integer(string=u'消息总数', help=u'上行发送了消息的消息总数')
    ref_hour = fields.Selection(
        [('000', u'[000,100)'), ('100', u'[100,200)'), ('200', u'[200,300)'),
         ('300', u'[300,400)'), ('400', u'[400,500)'), ('500', u'[500,600)'),
        ('600', u'[600,700)'), ('700', u'[700,800)'), ('800', u'[800,900)'),
        ('900', u'[900,1000)'), ('1000', u'[1000,1100)'), ('1100', u'[1100,1200)'),
        ('1200', u'[1200,1300)'), ('1300', u'[1300,1400)'), ('1400', u'[1400,1500)'),
        ('1500', u'[1500,1600)'), ('1600', u'[1600,1700)'), ('1700', u'[1700,1800)'),
        ('1800', u'[1800,1900)'), ('1900', u'[1900,2000)'), ('2000', u'[2000,2100)'),
        ('2100', u'[2100,2200)'), ('2200', u'[2200,2300)'), ('2300', u'[2300,2400)'),],
        string=u'小时数据',help=u'数据的小时')



class tl_weixin_upstreammsgweek(models.Model):
    """
    获取消息发送周数据
    """
    _name = 'tl.weixin.upstreammsgweek'
    _rec_name = 'ref_date'
    _order = 'ref_date'

    @api.multi
    def _get_ref_date_end(self):
        for each in self:
            if each.ref_date:

                y, m, d = time.strptime(each.ref_date, DEFAULT_SERVER_DATE_FORMAT)[0:3]
                ref_date = datetime(y, m, d)
                each.ref_date_end = ref_date + timedelta(6)


    app_id = fields.Many2one('tl.weixin.app', required=True, string=u'微信公众号', help=u'发送消息的公众号')
    company_id = fields.Many2one('res.company', u'公司', default=lambda self: self.env.user.company_id, help=u"所属公司")
    ref_date = fields.Date(u'数据开始日期')
    ref_date_end = fields.Date(u'数据截止日期', compute=_get_ref_date_end)
    detail_ids = fields.One2many('tl.weixin.upstreammsgweek.detail', 'upstreammsgweek_id')
    detail2_ids = fields.One2many('tl.weixin.upstreammsgweek.detail2', 'upstreammsgweek_id')




class tl_weixin_upstreammsgweek_detail(models.Model):
    """
    获取消息发送周数据详细
    """
    _name = 'tl.weixin.upstreammsgweek.detail'

    upstreammsgweek_id = fields.Many2one('tl.weixin.upstreammsgweek', cascade='ondelete')
    user_source = fields.Selection([('0', u'会话'), ('1', u'好友'), ('2', u'朋友圈'),('3', u'腾讯微博'),('4', u'历史消息'), ('5', u'其它')],
                                   string=u'用户渠道',help=u'代表用户从哪里进入来阅读该图文')
    msg_type = fields.Selection([(1, u'文字'), (2, u'图片'), (3, u'语音'),(4, u'视频'),(6, u'第三方应用消息（链接消息）'),],
                                string=u'消息类型',help=u'消息类型')
    msg_user = fields.Integer(string=u'用户数', help=u'上行发送了（向公众号发送了）消息的用户数')
    msg_count = fields.Integer(string=u'消息总数', help=u'上行发送了消息的消息总数')


class tl_weixin_upstreammsgweek_detail2(models.Model):
    """
    获取消息发送周分布数据详细
    """
    _name = 'tl.weixin.upstreammsgweek.detail2'

    upstreammsgweek_id = fields.Many2one('tl.weixin.upstreammsgweek', cascade='ondelete')
    user_source = fields.Selection([('0', u'会话'), ('1', u'好友'), ('2', u'朋友圈'),('3', u'腾讯微博'),('4', u'历史消息'), ('5', u'其它')],
                                   string=u'用户渠道',help=u'代表用户从哪里进入来阅读该图文')
    msg_user = fields.Integer(string=u'用户数', help=u'上行发送了（向公众号发送了）消息的用户数')
    count_interval = fields.Selection([('0', u'0'), ('1', u'1-5'), ('2', u'6-10'),('3', u'10次以上'),],
                                string=u'消息量分布区间',help=u'当日发送消息量分布的区间')






class tl_weixin_upstreammsgmonth(models.Model):
    """
    获取消息发送月数据
    """
    _name = 'tl.weixin.upstreammsgmonth'
    _rec_name = 'ref_date'
    _order = 'ref_date'

    @api.multi
    def _get_ref_date_end(self):
        # 计算出月末那一天
        for each in self:
            if each.ref_date:
                y, m, d = time.strptime(self.ref_date, DEFAULT_SERVER_DATE_FORMAT)[0:3]
                ref_date = datetime(y, m, d)
                days_of_month = int(calendar.monthrange(ref_date.year, ref_date.month)[1])
                each.ref_date_end = ref_date + timedelta(days_of_month - 1)


    app_id = fields.Many2one('tl.weixin.app', required=True, string=u'微信公众号', help=u'发送消息的公众号')
    company_id = fields.Many2one('res.company', u'公司', default=lambda self: self.env.user.company_id, help=u"所属公司")
    ref_date = fields.Date(u'数据开始日期')
    ref_date_end = fields.Date(u'数据截止日期', compute=_get_ref_date_end)
    detail_ids = fields.One2many('tl.weixin.upstreammsgmonth.detail', 'upstreammsgmonth_id')
    detail2_ids = fields.One2many('tl.weixin.upstreammsgmonth.detail2', 'upstreammsgmonth_id')




class tl_weixin_upstreammsgmonth_detail(models.Model):
    """
    获取消息发送月数据详细
    """
    _name = 'tl.weixin.upstreammsgmonth.detail'

    upstreammsgmonth_id = fields.Many2one('tl.weixin.upstreammsgmonth', cascade='ondelete')

    user_source = fields.Selection([('0', u'会话'), ('1', u'好友'), ('2', u'朋友圈'),('3', u'腾讯微博'),('4', u'历史消息'), ('5', u'其它')],
                                   string=u'用户渠道',help=u'代表用户从哪里进入来阅读该图文')
    msg_type = fields.Selection([(1, u'文字'), (2, u'图片'), (3, u'语音'),(4, u'视频'),(6, u'第三方应用消息（链接消息）')],string=u'消息类型',help=u'消息类型')
    msg_user = fields.Integer(string=u'用户数', help=u'上行发送了（向公众号发送了）消息的用户数')
    msg_count = fields.Integer(string=u'消息总数', help=u'上行发送了消息的消息总数')


class tl_weixin_upstreammsgmonth_detail2(models.Model):
    """
    获取消息发送周月布数据详细
    """
    _name = 'tl.weixin.upstreammsgmonth.detail2'

    upstreammsgmonth_id = fields.Many2one('tl.weixin.upstreammsgmonth', cascade='ondelete')
    user_source = fields.Selection([('0', u'会话'), ('1', u'好友'), ('2', u'朋友圈'),('3', u'腾讯微博'),('4', u'历史消息'), ('5', u'其它')],
                                   string=u'用户渠道',help=u'代表用户从哪里进入来阅读该图文')
    msg_user = fields.Integer(string=u'用户数', help=u'上行发送了（向公众号发送了）消息的用户数')
    count_interval = fields.Selection([('0', u'0'), ('1', u'1-5'), ('2', u'6-10'),('3', u'10次以上'),],
                                string=u'消息量分布区间',help=u'当日发送消息量分布的区间')



## 接口分析数据

class tl_weixin_interfacesummary(models.Model):
    """
    接口分析数据
    """
    _name = 'tl.weixin.interfacesummary'
    _rec_name = 'ref_date'
    _order = 'ref_date'

    app_id = fields.Many2one('tl.weixin.app', required=True, string=u'微信公众号', help=u'发送消息的公众号')
    company_id = fields.Many2one('res.company', u'公司', default=lambda self: self.env.user.company_id, help=u"所属公司")
    ref_date = fields.Date(u'数据开始日期')
    hour_ids = fields.One2many('tl.weixin.interfacesummaryhour', 'day_id')
    callback_count = fields.Integer(string=u'回复用户次数', help=u'通过服务器配置地址获得消息后，被动回复用户消息的次数')
    fail_count = fields.Integer(string=u'失败次数', help=u'通过服务器配置地址获得消息后，被动回复用户消息失败的次数')
    total_time_cost = fields.Integer(string=u'总耗时', help=u'总耗时，除以callback_count即为平均耗时')
    max_time_cost = fields.Integer(string=u'最大耗时', help=u'最大耗时')



class tl_weixin_interfacesummaryhour(models.Model):
    """
    接口分析分时数据
    """
    _name = 'tl.weixin.interfacesummaryhour'

    day_id = fields.Many2one('tl.weixin.interfacesummary', cascade='ondelete')
    callback_count = fields.Integer(string=u'回复用户次数', help=u'通过服务器配置地址获得消息后，被动回复用户消息的次数')
    fail_count = fields.Integer(string=u'失败次数', help=u'通过服务器配置地址获得消息后，被动回复用户消息失败的次数')
    total_time_cost = fields.Integer(string=u'总耗时', help=u'总耗时，除以callback_count即为平均耗时')
    max_time_cost = fields.Integer(string=u'最大耗时', help=u'最大耗时')
    ref_hour = fields.Selection(
        [('000', u'[000,100)'), ('100', u'[100,200)'), ('200', u'[200,300)'),
         ('300', u'[300,400)'), ('400', u'[400,500)'), ('500', u'[500,600)'),
        ('600', u'[600,700)'), ('700', u'[700,800)'), ('800', u'[800,900)'),
        ('900', u'[900,1000)'), ('1000', u'[1000,1100)'), ('1100', u'[1100,1200)'),
        ('1200', u'[1200,1300)'), ('1300', u'[1300,1400)'), ('1400', u'[1400,1500)'),
        ('1500', u'[1500,1600)'), ('1600', u'[1600,1700)'), ('1700', u'[1700,1800)'),
        ('1800', u'[1800,1900)'), ('1900', u'[1900,2000)'), ('2000', u'[2000,2100)'),
        ('2100', u'[2100,2200)'), ('2200', u'[2200,2300)'), ('2300', u'[2300,2400)'),],
        string=u'小时数据',help=u'数据的小时')







### EEEEE