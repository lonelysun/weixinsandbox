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
from openerp import SUPERUSER_ID
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT

from openerp import _
from openerp.exceptions import UserError, ValidationError
from openerp import api, fields, models

try:
    import cStringIO as StringIO
except ImportError:
    import StringIO

_logger = logging.getLogger(__name__)


# 接口信息
class tl_weixin_app(models.Model):
    _name = 'tl.weixin.app'
    _description = "tl.weixin.app"

    # 获取默认公司
    def _default_company_id(self, cr, uid, context=None):
        if not context.get('company_id', False):
            company_id = self.pool.get('res.users').browse(cr, uid, uid, context).company_id.id
        else:
            company_id = context.get('company_id', False)
        return company_id

    name = fields.Char(u'公众号', required=True)
    access_token = fields.Text(u'Access Token')
    appid = fields.Char(u'AppID(应用ID)', required=True)
    appsecret = fields.Char(u'AppSecret(应用密钥)', required=True)
    date_token = fields.Datetime(u'Token生效时间', readonly="1")
    # token_expires_at = fields.Integer(u'Token失效时间', readonly="1")
    token_expires_at = fields.Datetime(u'Token失效时间', readonly="1")

    jsapi_ticket = fields.Text(u'JsApi Ticket', help=u"jsapi_ticket是公众号用于调用微信JS接口的临时票据。正常情况下，jsapi_ticket的有效期为7200秒.")
    jsapi_ticket_date = fields.Datetime(u'JsApi Ticket生效时间', readonly="1")
    # jsapi_ticket_expires_at = fields.Integer(u'JsApi Ticket失效时间', readonly="1")
    jsapi_ticket_expires_at = fields.Datetime(u'JsApi Ticket失效时间', readonly="1")
    company_id = fields.Many2one('res.company', u'公司', select=True)
    # page_ids = fields.One2many('tl.weixin.page', 'app_id', u'摇一摇页面', )
    # device_ids = fields.One2many('tl.device', 'app_id', u'设备', )
    # shop_id = fields.Many2one('tl.shop', u'商户')
    user_ids = fields.One2many('tl.weixin.users', 'app_id', u'关注者')
    # group_ids = fields.One2many('tl.device.group', 'app_id', u'设备分组')
    mch_id = fields.Char(u'微信支付商户号', help=u"微信支付分配的商户号")
    security_key = fields.Char(u'加密KEY', help=u"key设置路径：微信商户平台(pay.weixin.qq.com)-->账户设置-->API安全-->密钥设置")
    image = openerp.fields.Binary(u"微信公众二维码", attachment=True, help=u"建议尺寸：宽60像素，高60像素")
    primary_industry = fields.Many2one('tl.weixin.industry', string=u'主营行业', domain=[('code','>',0)], help=u'需要选择公众账号服务所处的2个行业，每月可更改1次所选行业')
    secondary_industry = fields.Many2one('tl.weixin.industry', string=u'副营行业', domain=[('code','>',0)], help=u'需要选择公众账号服务所处的2个行业，每月可更改1次所选行业')
    user_group_ids = fields.One2many('tl.weixin.users.groups', 'app_id', u'用户分组')
    account_name = fields.Char(u'微信号')


    _defaults = {
        'company_id': _default_company_id,
    }

    def grant_token(self, cr, uid, ids, context=None):
        """
        获取 Access Token
        """
        o = self.browse(cr, uid, ids[0], context)
        client_obj = Client(self.pool, cr, o.id, o.appid, o.appsecret, o.access_token, o.token_expires_at)
        json = client_obj.grant_token()
        if "errcode" in json:
            _logger.warn(u"获取Access Token失败，%s[%s]" % (json["errmsg"], json["errcode"]))
            return False
        else:
            stamp = int(json["expires_in"])
            parm = {
                'access_token': json["access_token"],
                'date_token': datetime.now(),
                # 'token_expires_at': int(time.time()) + json["expires_in"]
                'token_expires_at':datetime.now() + timedelta(seconds=stamp)
            }
            self.write(cr, uid, ids, parm)
            return json["access_token"]

    @api.multi
    def _sync_weixin_card(self, begin, status_list):

        client_obj = Client(self.pool, self._cr, self.id, self.appid, self.appsecret, self.access_token,
                            self.token_expires_at)
        json = client_obj.card_batchget(begin, status_list)
        if "errcode" in json and json["errcode"] != 0:
            raise UserError(_(json["errmsg"]))
        else:
            total_num = json.get('total_num', 0)
            if total_num > 0:
                card_id_list = json.get('card_id_list', [])
                new_card_ids = []
                for card_id in card_id_list:
                    # 验证是否已经存在
                    card = self.env['tl.wxcard'].search([('wxcard_id', '=', card_id)], limit=1)
                    if not card:
                        new_card_ids.append(card_id)
                self.env['tl.wxcard'].card_get_by_wxcard_ids(self.id, new_card_ids)

            return total_num, len(card_id_list)

    @api.multi
    def sync_weixin_card(self):
        status_list = []
        local_total_count = 0
        total_count, current_count = self._sync_weixin_card(0, status_list)

        local_total_count += current_count
        index = 0
        while local_total_count < total_count and index < 100:
            total_count, current_count = self._sync_weixin_card(local_total_count, status_list)
            local_total_count += current_count
            index += 1

        return True

    def grant_jsapi_ticket(self, cr, uid, id, o, context=None):
        """
        获取最新的JsApi Ticket
        """
        client_obj = Client(self.pool, cr, o.id, o.appid, o.appsecret, o.access_token, o.token_expires_at)
        json = client_obj.get_jsapi_ticket()
        if "errcode" in json and json["errcode"] != 0:
            raise UserError(_(json["errmsg"]))
        else:
            stamp = int(time.time()) + json["expires_in"]

            parm = {
                'jsapi_ticket': json["ticket"],
                'jsapi_ticket_date': datetime.now(),
                # 'jsapi_ticket_expires_at': int(time.time()) + json["expires_in"]
                'token_expires_at':datetime.now() + timedelta(seconds=stamp)
            }
            self.write(cr, uid, id, parm)
            return json["ticket"]

    def get_jsapi_ticket(self, cr, uid, openid, context=None):
        """
        获取JsApi Ticket，先从本地获取
        """
        records = self.pool.get('tl.weixin.users').search_read(cr, openerp.SUPERUSER_ID, [('openid', '=', openid)],
                                                               ['app_id'], context=context)
        if records:
            id = records[0].get('app_id')[0]
            o = self.browse(cr, uid, id, context)



            if (o.jsapi_ticket):
                timeArray = time.strptime(o.jsapi_ticket_expires_at, "%Y-%m-%d %H:%M:%S")
                time_stamp = int(time.mktime(timeArray))
                if time_stamp > 0:
                    now = time.time()
                    if time_stamp - now > 60:
                        return o.jsapi_ticket
                    else:
                        return self.grant_jsapi_ticket(cr, uid, id, o)
            else:
                return self.grant_jsapi_ticket(cr, uid, id, o)
        else:
            return False

    # 测试连接是否正常
    def test_weixin_app(self, cr, uid, ids, context=None):
        self.grant_token(cr, uid, ids, context=context)
        # self.sync_weixin_get_industry(cr, uid, ids, context=context)
        return True

    # 同步微信摇一摇入口画面
    def _sync_weixin_page(self, cr, uid, ids, begin, context=None):
        o = self.browse(cr, uid, ids[0], context)
        client_obj = Client(self.pool, cr, o.id, o.appid, o.appsecret, o.access_token, o.token_expires_at)
        json = client_obj.shakearound_page_search(begin)
        if "errcode" in json and json["errcode"] != 0:
            raise UserError(_(json["errmsg"]))
        else:
            val_pages = []
            data = json.get('data')
            total_count = data.get('total_count', 0)

            if total_count > 0:
                pages = data.get('pages', False)
                page_obj = self.pool.get('tl.weixin.page')
                material_obj = self.pool.get('tl.shakearound.material')

                for page in pages:

                    # 验证图标地址是否存在
                    material_ids = material_obj.search(cr, uid, [('pic_url', '=', page.get('icon_url', 0))],
                                                       context=context)
                    if not material_ids:

                        # 生成预览图片
                        image_bytes = urllib2.urlopen(page.get('icon_url', 0)).read()
                        data_stream = io.BytesIO(image_bytes)
                        image = Image.open(data_stream).convert("RGBA")
                        # output = io.BytesIO('img')
                        output = StringIO.StringIO()
                        image.save(output, 'PNG')
                        output.seek(0)
                        output_s = output.read()
                        image = base64.b64encode(output_s)
                        val_material = {
                            'name': u'%s图标' % (page.get('comment', False)),
                            'app_id': o.id,
                            'pic_url': page.get('icon_url', 0),
                            'type': 'icon',
                            'image': image,
                        }
                        material_id = material_obj.create(cr, uid, val_material, context)
                    else:
                        material_id = material_ids[0]

                    # 验证该画面是否已经存在
                    pages_ids = page_obj.search(cr, uid, [('page_id', '=', page.get('page_id', 0))], context=context)
                    if pages_ids:
                        val_pages.append((1, int(pages_ids[0]), {
                            'comment': page.get('comment', False),
                            'description': page.get('description', False),
                            'name': page.get('title', False),
                            'material_id': material_id,
                            'page_id': page.get('page_id', 0),
                            'page_url': page.get('page_url', False),
                            'auto': True,  # 该字段标志该数据是自动修改，不需要同步到服务器中
                        }))
                    else:
                        val_pages.append((0, 0, {
                            'comment': page.get('comment', False),
                            'description': page.get('description', False),
                            'name': page.get('title', False),
                            'material_id': material_id,
                            'page_id': page.get('page_id', 0),
                            'page_url': page.get('page_url', False),
                        }))
                self.write(cr, uid, o.id, {'page_ids': val_pages})
            return total_count, len(pages)

    # 同步微信摇一摇入口画面
    def sync_weixin_page(self, cr, uid, ids, context=None):
        """
        分页调用，每次获取50条数据，最大允许获取5000条记录
        """
        local_total_count = 0
        total_count, current_count = self._sync_weixin_page(cr, uid, ids, 0, context=None)

        print(total_count)
        print(current_count)
        local_total_count += current_count
        index = 0
        while local_total_count < total_count and index < 100:
            total_count, current_count = self._sync_weixin_page(cr, uid, ids, local_total_count, context=None)
            local_total_count += current_count
            index += 1

        return True

    # 同步设备分组列表
    def sync_device_group(self, cr, uid, ids, begin, context=None):
        o = self.browse(cr, uid, ids[0], context)
        client_obj = Client(self.pool, cr, o.id, o.appid, o.appsecret, o.access_token, o.token_expires_at)
        json = client_obj.device_group_getlist(0)
        if "errcode" in json and json["errcode"] != 0:
            raise UserError(_(json["errmsg"]))
        else:
            val_groups = []
            data = json.get('data')
            total_count = data.get('total_count', 0)

            if total_count > 0:
                groups = data.get('groups', False)
                group_obj = self.pool.get('tl.device.group')

                for group in groups:
                    # 验证设备分组是否已经存在
                    group_ids = group_obj.search(cr, uid, [('group_id', '=', group.get('group_id', 0))],
                                                 context=context)

                    if group_ids:
                        val_groups.append((1, int(group_ids[0]), {
                            'name': group.get('group_name', False),
                            'auto': True,  # 该字段标志该数据是自动修改，不需要同步到服务器中
                        }))
                    else:
                        val_groups.append((0, 0, {
                            'name': group.get('group_name', False),
                            'group_id': group.get('group_id', 0),

                        }))

                self.write(cr, uid, o.id, {'group_ids': val_groups})
            return True

    # 同步设备列表
    def _sync_weixin_devices(self, cr, uid, ids, begin, context=None):
        o = self.browse(cr, uid, ids[0], context)
        client_obj = Client(self.pool, cr, o.id, o.appid, o.appsecret, o.access_token, o.token_expires_at)
        json = client_obj.devices_search(begin)
        if "errcode" in json and json["errcode"] != 0:
            raise UserError(_(json["errmsg"]))
        else:
            val_pages = []
            data = json.get('data')
            total_count = data.get('total_count', 0)

            if total_count > 0:
                devices = data.get('devices', False)
                beacon_obj = self.pool.get('tl.device')

                for device in devices:
                    # 验证该画面是否已经存在
                    device_ids = beacon_obj.search(cr, uid, [('device_id', '=', device.get('device_id', 0))],
                                                   context=context)
                    if isinstance(device.get('last_active_time', False), (int, long, float)):
                        last_active_time = datetime.fromtimestamp(device.get('last_active_time', False))
                    else:
                        last_active_time = False
                    if device_ids:
                        val_pages.append((1, int(device_ids[0]), {
                            'comment': device.get('comment', False),
                            'device_id': device.get('device_id', 0),
                            'major': device.get('major', False),
                            'minor': device.get('minor', False),
                            'status': device.get('status', 0),
                            'last_active_time': last_active_time,
                            'uuid': device.get('uuid', False),
                            'auto': True,  # 该字段标志该数据是自动修改，不需要同步到服务器中
                        }))
                    else:
                        val_pages.append((0, 0, {
                            'comment': device.get('comment', False),
                            'device_id': device.get('device_id', 0),
                            'major': device.get('major', False),
                            'minor': device.get('minor', False),
                            'status': device.get('status', 0),
                            'last_active_time': last_active_time,
                            'uuid': device.get('uuid', False),
                        }))

                self.write(cr, uid, o.id, {'device_ids': val_pages})
            return total_count, len(devices)

    # 同步微信摇一摇入口画面
    def sync_weixin_devices(self, cr, uid, ids, context=None):
        """
        分页调用，每次获取50条数据，最大允许获取5000条记录
        """
        local_total_count = 0
        total_count, current_count = self._sync_weixin_devices(cr, uid, ids, 0, context=None)
        local_total_count += current_count
        index = 0
        while local_total_count < total_count and index < 100:
            total_count, current_count = self._sync_weixin_devices(cr, uid, ids, local_total_count, context=None)
            local_total_count += current_count
            index += 1

        return True

    # 获取帐号的关注者列表
    def sync_followers(self, cr, uid, ids, context=None):
        """
        公众号可通过本接口来获取帐号的关注者列表，
        关注者列表由一串OpenID（加密后的微信号，每个用户对每个公众号的OpenID是唯一的）组成。
        一次拉取调用最多拉取10000个关注者的OpenID，可以通过多次拉取的方式来满足需求。
        """

        user_obj = self.pool.get('tl.weixin.users')
        o = self.browse(cr, uid, ids[0], context)
        client_obj = Client(self.pool, cr, o.id, o.appid, o.appsecret, o.access_token, o.token_expires_at)
        json = client_obj.get_followers()
        if "errcode" in json and json["errcode"] != 0:
            raise UserError(_(json["errmsg"]))
        else:

            data = json.get('data')
            if not data:
                raise ValidationError(_(u'没有关注者'))

            total_count = json.get('total', 0)  # 关注该公众账号的总用户数
            count = json.get('count', 0)  # 拉取的OPENID个数，最大值为10000
            next_openid = data.get('next_openid', False)  # 拉取列表的最后一个用户的OPENID
            if count > 0:
                openids = data.get('openid', False)
                val_users = []

                group_obj = self.pool.get('tl.weixin.users.groups')

                for openid in openids:
                    # 验证该画面是否已经存在
                    user_ids = user_obj.search(cr, uid, [('openid', '=', openid)], context=context)

                    o = client_obj.get_user_info(openid)
                    if "errcode" in o and o["errcode"] != 0:
                        continue

                    if isinstance(o.get('subscribe_time', False), (int, long, float)):
                        subscribe_time = datetime.fromtimestamp(o.get('subscribe_time', False))
                    else:
                        subscribe_time = False

                    groupid = o.get('groupid', 'NoGroupId')
                    # print groupid
                    if groupid != 'NoGroupId':
                        ids = group_obj.search(cr, uid, [('groupid', '=', groupid)], limit=1, context=context)

                        if ids:
                            group_id = group_obj.browse(cr, uid, ids[0]).id
                        else:
                            group_id = False
                    else:
                        group_id = False

                    if not user_ids:

                        val_users.append((0, 0, {
                            'subscribe': o.get('subscribe', False),
                            'openid': o.get('openid', False),
                            'name': o.get('nickname', False),
                            'sex': o.get('sex', False),
                            'city': o.get('city', False),
                            'country': o.get('country', False),
                            'province': o.get('province', False),
                            'language': o.get('language', False),
                            'headimgurl': o.get('headimgurl', False),
                            'subscribe_time': subscribe_time,
                            'unionid': o.get('unionid', False),
                            'remark': o.get('remark', False),
                            # 'groupid': o.get('groupid', False),
                            'group_id': group_id,

                        }))
                    else:
                        vals = {
                            'subscribe': o.get('subscribe', False),
                            'openid': o.get('openid', False),
                            'name': o.get('nickname', False),
                            'sex': o.get('sex', False),
                            'city': o.get('city', False),
                            'country': o.get('country', False),
                            'province': o.get('province', False),
                            'language': o.get('language', False),
                            'headimgurl': o.get('headimgurl', False),
                            'subscribe_time': subscribe_time,
                            'unionid': o.get('unionid', False),
                            'remark': o.get('remark', False),
                            # 'groupid': o.get('groupid', False),
                            'group_id': group_id,
                            'auto': True
                        }

                        user_obj.write(cr, uid, int(user_ids[0]), vals, context=context)

                self.write(cr, uid, o.id, {'user_ids': val_users})
            return True

    # 同步门店列表
    def _sync_weixin_poi(self, cr, uid, ids, begin, context=None):

        image_obj = self.pool.get('tl.weixin.image')
        business_obj = self.pool.get('tl.business')
        state_obj = self.pool.get('res.country.state')
        city_obj = self.pool.get('res.country.state.area')
        district_obj = self.pool.get('res.country.state.area.subdivide')

        index = 0
        o = self.browse(cr, uid, ids[0], context)
        client_obj = Client(self.pool, cr, o.id, o.appid, o.appsecret, o.access_token, o.token_expires_at)
        json = client_obj.poi_getpoilist(begin)
        if "errcode" in json and json["errcode"] != 0:
            raise UserError(_(json["errmsg"]))
        else:
            business_list = json.get('business_list')
            total_count = json.get('total_count', 0)
            poi_obj = self.pool.get('tl.weixin.poi')
            for item in business_list:
                index = index + 1
                data = item.get('base_info', False)
                if data:
                    sid = data.get('sid', False)
                    poi_id = data.get('poi_id', False)
                    # 状态
                    available_state = data.get('available_state', 1)
                    if available_state == 1:
                        state = 'draft'
                    elif available_state == 2:
                        state = 'unapproved'
                    elif available_state == 3:
                        state = 'succ'
                    else:
                        state = 'fail'

                    domain = []
                    if sid:
                        domain = domain + [('sid', '=', sid)]
                    if poi_id:
                        domain = domain + [('poi_id', '=', poi_id)]
                    if len(domain) > 1:
                        domain = ['|'] + domain

                    # 图片
                    photo_list = data.get('photo_list', False)
                    photo_list_ids = []
                    if photo_list:
                        for photo in photo_list:
                            photo_url = photo.get('photo_url')
                            # 查看图片是否存在
                            image_ids = image_obj.search(cr, uid, [('url', '=', photo_url)], context=context)
                            if not image_ids:
                                # 生成预览图片
                                image_bytes = urllib2.urlopen(photo_url).read()
                                data_stream = io.BytesIO(image_bytes)
                                image = Image.open(data_stream).convert("RGBA")
                                output = StringIO.StringIO()
                                image.save(output, 'PNG')
                                output.seek(0)
                                output_s = output.read()
                                image = base64.b64encode(output_s)
                                v_image = {
                                    'url': photo_url,
                                    'image': image,
                                    'app_id': o.id,
                                    'name': data.get('business_name', False)
                                }
                                new_image_id = image_obj.create(cr, uid, v_image, context=context)

                                photo_list_ids.append(new_image_id)
                            else:
                                photo_list_ids.append(image_ids[0])

                    # 分类
                    business_id = False
                    sub_business_id = False
                    categories = data.get('categories', [])[0],
                    if categories:
                        categories = categories[0]
                        business_id, sub_business_id = categories.split(',')
                        business_id = business_obj.search(cr, uid, [('name', '=', business_id)], context=context)
                        sub_business_id = business_obj.search(cr, uid, [('name', '=', sub_business_id)],
                                                              context=context)

                    # 省市县
                    province_ids = state_obj.search(cr, uid, [('name', '=', data.get('province', False))],
                                                    context=context)
                    city_ids = city_obj.search(cr, uid, [('name', '=', data.get('city', False))], context=context)
                    district_ids = district_obj.search(cr, uid, [('name', '=', data.get('district', False))],
                                                       context=context)

                    device_ids = poi_obj.search(cr, uid, domain, context=context)

                    update_status = str(data.get('update_status'))

                    if device_ids:
                        val_update = {
                            "sid": data.get('sid', False),
                            "app_id": o.id,
                            'business_id': business_id and business_id[0] or False,
                            'sub_business_id': sub_business_id and sub_business_id[0] or False,
                            "name": data.get('business_name', False),
                            "branch_name": data.get('branch_name', False),
                            "state_id": province_ids and province_ids[0] or False,
                            "city_id": city_ids and city_ids[0] or False,
                            "district_id": district_ids and district_ids[0] or False,
                            "address": data.get('address', False),
                            "telephone": data.get('telephone', False),
                            "offset_type": data.get('offset_type', False),
                            "longitude": data.get('longitude', False),
                            "latitude": data.get('latitude', False),
                            "image_ids": [[6, 0, list(set(photo_list_ids))]],
                            "recommend": data.get('recommend', False),
                            "special": data.get('special', False),
                            "introduction": data.get('introduction', False),
                            "open_time": data.get('open_time', False),
                            "avg_price": data.get('avg_price', False),
                            'state': state,
                            'auto': True,
                            'poi_id': data.get('poi_id', False),
                            'update_status': update_status,
                        }
                        poi_obj.write(cr, uid, device_ids, val_update, context=context)
                    else:

                        vals = {
                            "sid": data.get('sid', False),
                            "app_id": o.id,
                            'business_id': business_id and business_id[0] or False,
                            'sub_business_id': sub_business_id and sub_business_id[0] or False,
                            "name": data.get('business_name', False),
                            "branch_name": data.get('branch_name', False),
                            "state_id": province_ids and province_ids[0] or False,
                            "city_id": city_ids and city_ids[0] or False,
                            "district_id": district_ids and district_ids[0] or False,
                            "address": data.get('address', False),
                            "telephone": data.get('telephone', False),
                            "offset_type": data.get('offset_type', False),
                            "longitude": data.get('longitude', False),
                            "latitude": data.get('latitude', False),
                            "image_ids": [[6, 0, list(set(photo_list_ids))]],
                            "recommend": data.get('recommend', False),
                            "special": data.get('special', False),
                            "introduction": data.get('introduction', False),
                            "open_time": data.get('open_time', False),
                            "avg_price": data.get('avg_price', False),
                            'state': state,
                            'poi_id': data.get('poi_id', False),
                            'update_status': update_status,
                        }
                        poi_obj.create(cr, uid, vals, context=context)
            return total_count, index

    # 同步门店
    def sync_weixin_poi(self, cr, uid, ids, context=None):
        """
        返回数据条数，最大允许50，默认为20
        """
        local_total_count = 0
        total_count, current_count = self._sync_weixin_poi(cr, uid, ids, 0, context=None)
        local_total_count += current_count
        index = 0
        while local_total_count < total_count and index < 100:
            total_count, current_count = self._sync_weixin_poi(cr, uid, ids, local_total_count, context=None)
            local_total_count += current_count
            index += 1

        return True

    # 同步模板
    @api.multi
    def sync_weixin_template(self):
        client_obj = Client(self.pool, self._cr, self.id, self.appid, self.appsecret, self.access_token,
                            self.token_expires_at)
        json = client_obj.get_all_private_template()

        if "errcode" in json and json["errcode"] != 0:
            raise UserError(_(json["errmsg"]))
        else:
            data = json.get('template_list', False)

            if not data:
                raise ValidationError(_(u'没有模板'))
            else:

                for each_template in data:
                    template_id = each_template.get('template_id', False)

                    if template_id:

                        each_template['app_id'] = self.id
                        each_template['company_id'] = self.company_id.id

                        domain = [('template_id', '=', template_id)]
                        template = self.env['tl.weixin.template'].search(domain, limit=1)

                        if template:
                            template.write(each_template)
                        else:

                            self.env['tl.weixin.template'].create(each_template)
                    else:
                        raise ValidationError(_(u'返回数据的格式错误'))
        return

    # 同步分组
    @api.multi
    def sync_weixin_users_groups(self):
        client_obj = Client(self.pool, self._cr, self.id, self.appid, self.appsecret, self.access_token,
                            self.token_expires_at)
        json = client_obj.get_groups()

        if "errcode" in json and json["errcode"] != 0:
            raise UserError(_(json["errmsg"]))
        else:
            groups_list = json.get("groups", False)
            if not groups_list:
                raise ValidationError(_(u'没有分组'))
            else:
                for each_group in groups_list:
                    domain = [('groupid', '=', int(each_group['id'])), ('app_id', '=', self.id)]

                    group = self.env['tl.weixin.users.groups'].search(domain, limit=1)


                    if group:
                        group.write({
                            "name": each_group['name'],
                            "groupid": each_group['id'],
                            "users_count": each_group['count'],
                            "auto": True
                        })
                    else:
                        self.env['tl.weixin.users.groups'].create({
                            "name": each_group['name'],
                            "groupid": each_group['id'],
                            "users_count": each_group['count'],
                            "app_id": self.id,
                            "auto": True
                        })
        return


    # 同步客服
    @api.multi
    def sync_weixin_kfaccount(self):
        client_obj = Client(self.pool, self._cr, self.id, self.appid, self.appsecret, self.access_token, self.token_expires_at)
        json = client_obj.getkflist()

        if "errcode" in json and json["errcode"] != 0:
            raise UserError(_(json["errmsg"]))
        else:
            kf_list = json.get("kf_list", False)
            if not kf_list:
                raise ValidationError(_(u'没有客服'))
            else:
                for each_account in kf_list:
                    domain = [('kf_id', '=', int(each_account['kf_id'])), ('app_id', '=', self.id)]

                    kfaccount = self.env['tl.weixin.kfaccount'].search(domain, limit=1)


                    if kfaccount:
                        kfaccount.write({
                            "kf_account": each_account['kf_account'],
                            "kf_nick": each_account['kf_nick'],
                            "kf_id": each_account['kf_id'],
                            "kf_headimgurl": each_account['kf_headimgurl'],
                            "auto": True
                        })
                    else:
                        self.env['tl.weixin.kfaccount'].create({
                            "kf_account": each_account['kf_account'],
                            "kf_nick": each_account['kf_nick'],
                            "kf_id": each_account['kf_id'],
                            "kf_headimgurl": each_account['kf_headimgurl'],
                            "app_id":self.id,
                            "auto": True
                        })
        return



    # 同步自定义菜单
    # 同步的策略是:先删除此公众号本地的菜单, 然后拉取服务器上的菜单
    @api.multi
    def sync_weixin_menu(self):
        client_obj = Client(self.pool, self._cr, self.id, self.appid, self.appsecret, self.access_token, self.token_expires_at)
        json = client_obj.get_menu()

        if "errcode" in json and json["errcode"] != 0:
            raise UserError(_(json["errmsg"]))
        else:

            menu = json.get("menu", False)
            if not menu:
                raise UserError(_(u'不存在有效的菜单'))
            else:

                # 判断是否该app_id已经存在menu,如果已存在,则删除所有该app_id的所有menu
                menu_set = self.env['tl.weixin.menu'].search([('app_id', '=', self.id)])
                if menu_set:
                    menu_set.unlink()


                button_lst = []
                for each_button in menu['button']:

                    sub_button = each_button.get('sub_button', False)
                    sub_button_lst = []
                    if sub_button:
                        # 存在二级菜单

                        for each_sub in sub_button:
                            # 根据服务器返回的key值查询本地的key值,如果查不到则存空
                            if each_sub.get('key', False):
                                key = self.env['tl.weixin.eventkey'].search([('value','=', each_sub.get('key'))])
                                if key:
                                    key_id = key.id
                                else:
                                    key_id = ''
                            else:
                                key_id = ''

                            sub_button_vals = {
                                'name': each_sub.get('name', ''),
                                'type': each_sub.get('type', ''),
                                'url': each_sub.get('url', ''),
                                'key': key_id,
                                'media_id': each_sub.get('media_id', ''),

                            }
                            sub_button_lst.append((0, 0, sub_button_vals))

                    # 根据服务器返回的key值查询本地的key值,如果查不到则存空
                    if each_button.get('key', False):
                        key = self.env['tl.weixin.eventkey'].search([('value','=', each_button.get('key'))])
                        if key:
                            key_id = key.id
                        else:
                            key_id = ''
                    else:
                        key_id = ''
                    button_vals = {
                        'name': each_button.get('name', ''),
                        'type': each_button.get('type', ''),
                        'url': each_button.get('url', ''),
                        'key': key_id,
                        'media_id': each_button.get('media_id', ''),
                        'child_ids': sub_button_lst,

                    }
                    button_lst.append((0, 0, button_vals))

                vals = {
                    'app_id': self.id,
                    'button_ids': button_lst,
                    'menuid': menu.get('menuid', ''),
                    'auto': True
                }

                self.env['tl.weixin.menu'].create(vals)


                # 判断是否存在个性化菜单
                conditionalmenu = json.get("conditionalmenu", False)
                if conditionalmenu:
                    # 这是一个个性化菜单
                    for each_conditional in conditionalmenu:

                        button_lst = []
                        for each_button in each_conditional['button']:

                            sub_button = each_button.get('sub_button', False)
                            sub_button_lst = []
                            if sub_button:
                                # 存在二级菜单

                                for each_sub in sub_button:
                                    # 根据服务器返回的key值查询本地的key值,如果查不到则设为空
                                    if sub_button.get('key', False):
                                        key = self.env['tl.weixin.eventkey'].search([('value','=', each_sub.get('key'))])
                                        if key:
                                            key_id = key.id
                                        else:
                                            key_id = ''
                                    else:
                                        key_id = ''

                                    sub_button_vals = {
                                        'name': each_sub.get('name', ''),
                                        'type': each_sub.get('type', ''),
                                        'url': each_sub.get('url', ''),
                                        'key': key_id,
                                        'media_id': each_sub.get('media_id', ''),
                                        'is_sub': True
                                    }
                                    sub_button_lst.append((0, 0, sub_button_vals))

                            if each_button.get('key', False):
                                key = self.env['tl.weixin.eventkey'].search([('value','=', each_button.get('key'))])
                                if key:
                                    key_id = key.id
                                else:
                                    key_id = ''
                            else:
                                key_id = ''
                            button_vals = {
                                'name': each_button.get('name', ''),
                                'type': each_button.get('type', ''),
                                'url': each_button.get('url', ''),
                                'key': key_id,
                                'media_id': each_button.get('media_id', ''),
                                'is_sub': False,
                                'child_ids': sub_button_lst,
                            }
                            button_lst.append((0, 0, button_vals))

                        # 解析matchrule
                        #API文档有问题, 说"matchrule共六个字段", 但实际有7个
                        matchrule = each_conditional['matchrule']

                        if matchrule.get('group_id', False):
                            # 查询表得到对应的group_id
                            group = self.env['tl.weixin.users.groups'].search([('groupid','=',int(matchrule.get('group_id')))])
                            if group:
                                group_id = group.id
                            else:
                                group_id = ''
                                
                        else:
                            group_id = ''

                        if matchrule.get('country', False):
                            country = self.env['tl.weixin.country'].search([('name','=',matchrule.get('country'))])
                            if country:
                                country_id = country.id
                            else:
                                country_id = ''
                        else:
                            country_id = ''

                        if matchrule.get('province', False):
                            province = self.env['tl.weixin.province'].search([('name','=',matchrule.get('province'))])
                            if province:
                                province_id = province.id
                            else:
                                province_id = ''
                        else:
                            province_id = ''

                        if matchrule.get('city', False):
                            # 查询表得到对应的city_id
                            city = self.env['tl.weixin.city'].search([('name','=',matchrule.get('city'))])
                            if city:
                                city_id = city.id
                            else:
                                city_id = ''
                        else:
                            city_id = ''

                        vals = {
                            'app_id': self.id,
                            'button_ids': button_lst,
                            'menuid': each_conditional.get('menuid', ''),

                            'is_conditional': True,
                            'group_id': group_id,
                            'sex': matchrule.get('sex', ''),
                            'country_id': country_id,
                            'province_id': province_id,
                            'city_id': city_id,
                            'client_platform_type': matchrule.get('client_platform_type', ''),
                            'language': matchrule.get('language', ''),
                            'auto': True

                        }

                        self.env['tl.weixin.menu'].create(vals)

        return

    # 删除自定义菜单
    @api.multi
    def sync_weixin_menu_delete(self):
        client_obj = Client(self.pool, self._cr, self.id, self.appid, self.appsecret, self.access_token, self.token_expires_at)
        json = client_obj.delete_menu()

        if "errcode" in json and json["errcode"] != 0:
            raise UserError(_(json["errmsg"]))
        else:
            menu_set = self.env['tl.weixin.menu'].search([('app_id', '=', self.id)])
            if menu_set:
                menu_set.unlink()

        return

    @api.multi
    def write(self, vals):
        auto = vals.has_key('auto')
        if auto:
            vals.pop('auto')

        if (vals.has_key('primary_industry') or vals.has_key('secondary_industry')) and not auto:

            primary_industry = vals.get('primary_industry', self.primary_industry)
            secondary_industry = vals.get('secondary_industry', self.secondary_industry)

            client_obj = Client(self.pool, self._cr, self.id, self.appid, self.appsecret, self.access_token,
                                self.token_expires_at)
            json = client_obj.api_set_industry(str(primary_industry), str(secondary_industry))

            if "errcode" in json and json["errcode"] != 0:
                raise UserError(_(json["errmsg"]))

        return super(tl_weixin_app, self).write(vals)

    @api.multi
    def sync_weixin_get_industry(self):

        """
        获取行业信息
        """
        client_obj = Client(self.pool, self._cr, self.id, self.appid, self.appsecret, self.access_token,
                            self.token_expires_at)
        json = client_obj.get_industry()
        if "errcode" in json:
            _logger.warn(u"获取行业信息，%s[%s]" % (json["errmsg"], json["errcode"]))
            return False
        else:
            primary_industry = json.get('primary_industry', False)
            secondary_industry = json.get('secondary_industry', False)

            if primary_industry and secondary_industry:
                domain1 = [('name', '=', primary_industry['second_class'])]
                id1 = self.env['tl.weixin.industry'].search(domain1).id
                domain2 = [('name', '=', secondary_industry['second_class'])]
                id2 = self.env['tl.weixin.industry'].search(domain2).id
                vals = {
                    'primary_industry': id1,
                    'secondary_industry': id2,
                    'auto': True,  # 该字段标志该数据是自动修改，不需要同步到服务器中
                }
                self.write(vals)

            else:
                raise UserError(_('得到的数据格式错误'))

        return


class tl_weixin_users(models.Model):
    """
        公众平台用户
    """
    _name = 'tl.weixin.users'
    _description = u"公众平台用户"
    _rec_name = 'name'

    # 获取默认公司
    def _default_company_id(self, cr, uid, context=None):
        if not context.get('company_id', False):
            company_id = self.pool.get('res.users').browse(cr, uid, uid, context).company_id.id
        else:
            company_id = context.get('company_id', False)
        return company_id

    name = fields.Char(u'用户的昵称', size=225, required=True, help=u"用户的昵称")
    subscribe = fields.Boolean(u'是否订阅', help=u"用户是否订阅该公众号标识，值为0时，代表此用户没有关注该公众号，拉取不到其余信息。")
    realname = fields.Char(u'姓名', size=225, help=u"姓名")
    mail = fields.Char(u'邮箱', size=225, help=u"邮箱")
    phone = fields.Char(u'联系电话', size=225, help=u"联系电话")
    openid = fields.Char(u'用户公众号', required=True, help=u"用户的标识，对当前公众号唯一")
    sex = fields.Selection([(0, u'未知'), (1, u'男'), (2, u'女'), ], u'性别', help=u"用户的性别，值为1时是男性，值为2时是女性，值为0时是未知")
    city = fields.Char(u'市', size=225, help=u"用户所在城市")
    province = fields.Char(u'省份', size=225, help=u"用户所在省份")
    country = fields.Char(u'国家', size=225, help=u"用户所在国家")
    language = fields.Char(u'语言', size=225, help=u"用户的语言，简体中文为zh_CN")
    headimgurl = fields.Char(u'头像', size=512, help=u"用户头像，最后一个数值代表正方形头像大小（有0、46、64、96、132数值可选")
    image = fields.Binary(u'头像')
    unionid = fields.Char(u'Unionid', size=225, help=u"只有在用户将公众号绑定到微信开放平台帐号后，才会出现该字段。详见：获取用户个人信息（UnionID机制）")
    subscribe_time = fields.Datetime(u'关注时间', help=u"用户关注时间，为时间戳。如果用户曾多次关注，则取最后关注时间")
    app_id = fields.Many2one('tl.weixin.app', u'微信公众号', required=True)
    remark = fields.Char(u'备注')
    page_access_token = fields.Text(u'Page Access Token')
    refresh_token = fields.Text(u'Refresh Token')
    company_id = fields.Many2one('res.company', u'公司', select=True)
    # shop_id = fields.Many2one('tl.shop', u'商户')
    # groupid = fields.Integer(u'组')
    group_id = fields.Many2one('tl.weixin.users.groups', string=u'用户所在分组')
    # wxcard_ids = fields.One2many('tl.wxcard.line', 'users_id', u'卡券', )

    _defaults = {
        'company_id': _default_company_id,
    }

    @api.multi
    def write(self, vals):
        auto = vals.has_key('auto')

        if auto:
            vals.pop('auto')

        if vals.get('group_id', False) and not auto:
            group_obj = self.env['tl.weixin.users.groups'].browse(vals.get('group_id'))
            to_groupid = int(group_obj.groupid)

            o = self.app_id
            client_obj = Client(self.pool, self._cr, o.id, o.appid, o.appsecret, o.access_token, o.token_expires_at)
            json = client_obj.batch_move_user_group(self.openid, to_groupid)

            if "errcode" in json and json["errcode"] != 0:
                raise UserError(_(json["errmsg"]))

        return super(tl_weixin_users, self).write(vals)

    # 根据openid获取关注者信息
    def create_or_update_user_by_openid(self, cr, uid, account_id, open_id, context=None):
        appconnect = self.pool.get('tl.weixin.app').browse(cr, uid, account_id, context)
        client_obj = Client(self.pool, cr, appconnect.id, appconnect.appid, appconnect.appsecret,
                            appconnect.access_token, appconnect.token_expires_at)
        o = client_obj.get_user_info(open_id)
        if "errcode" in o and o["errcode"] != 0:
            raise UserError(_(o["errmsg"]))
        else:
            _logger.info(o)
            ids = self.search(cr, SUPERUSER_ID, [('openid', '=', open_id), ('app_id', '=', account_id)])
            if isinstance(o.get('subscribe_time', False), (int, long, float)):
                subscribe_time = datetime.fromtimestamp(o.get('subscribe_time', False))
            else:
                subscribe_time = False
            if len(ids) == 0:
                # 第一次关注
                parm = {
                    'subscribe': o.get('subscribe', False),
                    'openid': o.get('openid', False),
                    'name': o.get('nickname', False),
                    'sex': o.get('sex', False),
                    'city': o.get('city', False),
                    'country': o.get('country', False),
                    'province': o.get('province', False),
                    'language': o.get('language', False),
                    'headimgurl': o.get('headimgurl', False),
                    'subscribe_time': subscribe_time,
                    'unionid': o.get('unionid', False),
                    'remark': o.get('remark', False),
                    'group_id': o.get('group_id', False),
                    'app_id': appconnect.id or False
                }
                self.create(cr, uid, parm, context)
            # 以前关注过或正在关注
            else:
                parm = {
                    'subscribe': o.get('subscribe', False),
                    'openid': o.get('openid', False),
                    'name': o.get('nickname', False),
                    'sex': o.get('sex', False),
                    'city': o.get('city', False),
                    'country': o.get('country', False),
                    'province': o.get('province', False),
                    'language': o.get('language', False),
                    'headimgurl': o.get('headimgurl', False),
                    'subscribe_time': subscribe_time,
                    'unionid': o.get('unionid', False),
                    'remark': o.get('remark', False),
                    'group_id': o.get('group_id', False),
                    'auto': True
                }
                self.write(cr, uid, ids[0], parm, context)
        return ids


class tl_weixin_poi(models.Model):
    """
        微信门店
    """
    _name = 'tl.weixin.poi'
    _description = u"微信门店"

    # 获取默认公司
    def _default_company_id(self, cr, uid, context=None):
        if not context.get('company_id', False):
            company_id = self.pool.get('res.users').browse(cr, uid, uid, context).company_id.id
        else:
            company_id = context.get('company_id', False)
        return company_id

    def _default_country(self, cr, uid, context=None):

        res = self.pool.get('res.country').search(cr, uid, [('code', '=', 'CN')], limit=1, context=context)
        country_id = res and res[0] or False
        return country_id

    def _address_display(self, cr, uid, ids, name, args, context=None):
        res = {}
        for poi in self.browse(cr, uid, ids, context=context):
            address_format = "%(province)s%(city)s%(district)s%(address)s"
            args = {
                'province': poi.country_id.name or '',
                'city': poi.state_id.name or '',
                'district': poi.city_id.name or '',
                'address': poi.district_id.name or '',
            }
            res[poi.id] = address_format % args
        return res

    @api.multi
    @api.depends('country_id', 'state_id', 'city_id', 'district_id')
    def _address_display(self):
        for poi in self:
            address_format = "%(province)s%(city)s%(district)s%(address)s"
            args = {
                'province': poi.country_id.name or '',
                'city': poi.state_id.name or '',
                'district': poi.city_id.name or '',
                'address': poi.district_id.name or '',
            }
            poi.contact_address = address_format % args

    name = fields.Char(u'门店名称', size=225, required=True, help=u"门店名称（仅为商户名，如：国美、麦当劳，不应包含地区、地址、分店名等信息，错误示例：北京国美）")
    poi_id = fields.Char(u'微信的门店ID', help=u"微信的门店ID，微信内门店唯一标示ID", readonly="1")
    branch_name = fields.Char(u'分店名称', size=225, help=u"分店名称（不应包含地区信息，不应与门店名有重复，错误示例：北京王府井店）")
    app_id = fields.Many2one('tl.weixin.app', u'微信公众号', required=True)
    country_id = fields.Many2one('res.country', u'国家', ondelete='restrict')
    state_id = fields.Many2one("res.country.state", u'省', ondelete='restrict')

    city_id = fields.Many2one('res.country.state.area', u'市')
    district_id = fields.Many2one('res.country.state.area.subdivide', u'县', select=True, track_visibility='onchange')

    address = fields.Char(u'街道地址', required=True, help=u"门店所在的详细街道地址（不要填写省市信息）")
    contact_address = fields.Char(string=u'详细地址', compute='_address_display')
    longitude = fields.Char(u'经度', help=u"门店所在地理位置的经度")
    latitude = fields.Char(u'纬度', help=u"门店所在地理位置的纬度（经纬度均为火星坐标，最好选用腾讯地图标记的坐标）")
    categories = fields.Char(u'门店类型', help=u"门店的类型（不同级分类用“,”隔开，如：美食，川菜，火锅。详细分类参见附件：微信门店类目表）")
    # business_id = fields.Many2one('tl.business', u'门店类型', required=True, select=True)
    # sub_business_id = fields.Many2one('tl.business', u'子类型', select=True, track_visibility='onchange')
    telephone = fields.Char(u'电话', help=u"门店的电话（纯数字，区号、分机号均由“-”隔开）")
    offset_type = fields.Selection([(1, u'火星坐标')], u'坐标类型', help=u"坐标类型，1 为火星坐标（目前只能选1）")
    special = fields.Char(u'特色服务', help=u"特色服务，如免费wifi，免费停车，送货上门等商户能提供的特色功能或服务")
    open_time = fields.Char(u'营业时间', help=u"营业时间，24 小时制表示，用“-”连接，如 8:00-20:00")
    avg_price = fields.Integer(u'人均价格', help=u"人均价格，大于0 的整数")
    introduction = fields.Text(u'商户简介', help=u"商户简介，主要介绍商户信息等")
    recommend = fields.Char(u'推荐品', help=u"推荐品，餐厅可为推荐菜；酒店为推荐套房；景点为推荐游玩景点等，针对自己行业的推荐内容")
    sid = fields.Char(u'内部唯一编号', help=u"商户自己的id，用于后续审核通过收到poi_id 的通知时，做对应关系。请商户自己保证唯一识别性")
    company_id = fields.Many2one('res.company', u'公司', select=True)
    state = fields.Selection([('draft', u'草稿'), ('unapproved', u'待审核'), ('succ', u'已审核'), ('fail', u'无效')], u'状态',
                             help=u"将标记门店相应审核状态，只有审核通过状态，才能进行更新，更新字段仅限扩展字段（表1 中前11 个字段）；")
    # shop_id = fields.Many2one('tl.shop', u'商户')
    image_ids = fields.Many2many('tl.weixin.image', 'tl_poi_image_rel', 'poi_id', 'image_id', u'图片列表', help=u"""图片列表，url 形式，可以有多张图片，
        尺寸为640*340px。必须为上一接口生成的url。图片内容不允许与门店不相关，不允许为二维码、员工合照（或模特肖像）、
        营业执照、无门店正门的街景、地图截图、公交地铁站牌、菜单截图等""")
    update_status = fields.Selection([('1', u'正在更新中，更新内容不会同步到微信'), ('0', u'可以再次更新，更新内容会同步到微信')], u'是否正在更新中',
                                     readonly="1",
                                     help=u"扩展字段是否正在更新中。1 表示扩展字段正在更新中，尚未生效，不允许再次更新； 0 表示扩展字段没有在更新中或更新已生效，可以再次更新")

    _defaults = {
        'company_id': _default_company_id,
        'state': 'draft',
        'offset_type': 1,
        'country_id': _default_country,
        'update_status': "0",
    }

    def create(self, cr, uid, vals, context=None):

        if not vals.get('sid', False):
            t = long(time.time())
            vals['sid'] = t

        poi_id = super(tl_weixin_poi, self).create(cr, uid, vals, context=context)
        poi = self.browse(cr, uid, poi_id, context)

        if not poi.latitude or not poi.longitude:
            tencent_map_key = openerp.tools.config['tencent_map_key']
            url = 'http://apis.map.qq.com/ws/geocoder/v1/?address=%s&key=%s' % (
                poi.contact_address.encode("utf8"), tencent_map_key)
            f = urllib2.urlopen(url)
            apps_charts = json.loads(f.read())
            charts = dict(apps_charts)
            status = charts.get('status', 0)
            if status > 0:
                raise UserError(_(charts.get('message', u'获取经纬度信息失败')))
            else:
                result = charts.get('result')
                location = result.get('location')
                if location:
                    lat = location.get('lat')
                    lng = location.get('lng')
                    t_vals = {
                        'latitude': lat,
                        'longitude': lng,
                    }
                    self.write(cr, uid, poi_id, t_vals, context)

        return poi_id

    def write(self, cr, uid, ids, vals, context=None):
        """
        编辑摇一摇出来的页面信息，包括在摇一摇页面出现的主标题、副标题、图片和点击进去的超链接。
        """
        auto = vals.has_key('auto')
        if auto:
            vals.pop('auto')

        result = super(tl_weixin_poi, self).write(cr, uid, ids, vals, context=context)
        poi = self.browse(cr, uid, ids, context)
        if not auto and poi and poi.poi_id and poi.update_status == '0':
            o = poi.app_id;
            client_obj = Client(self.pool, cr, o.id, o.appid, o.appsecret, o.access_token, o.token_expires_at)

            photo_list = []
            for image in poi.image_ids:
                v = {'photo_url': image.url}
                photo_list.append(v)

            v_update = {
                "poi_id": poi.poi_id,
                "telephone": poi.telephone,
                "photo_list": photo_list,
                "recommend": poi.recommend or '',
                "special": poi.special or '',
                "introduction": poi.introduction or '',
                "open_time": poi.open_time or '',
                "avg_price": poi.avg_price or 0,
            }
            json = client_obj.poi_updatepoi(v_update)
            if "errcode" in json and json["errcode"] != 0:
                raise UserError(_(json["errmsg"]))

        return result

    def unlink(self, cr, uid, ids, context=None):
        """
        商户可以通过该接口，删除已经成功创建的门店。请商户慎重调用该接口，门店信息被删除后，可能会影响其他与门店相关的业务使用，如卡券等。
        同样，该门店信息也不会在微信的商户详情页显示，不会再推荐入附近功能。
        """
        for poi in self.browse(cr, uid, ids, context=context):
            o = poi.app_id;
            client_obj = Client(self.pool, cr, o.id, o.appid, o.appsecret, o.access_token, o.token_expires_at)
            json = client_obj.poi_delpoi(poi.poi_id)
            if "errcode" in json and json["errcode"] != 0:
                raise UserError(_(json["errmsg"]))

        return super(tl_weixin_poi, self).unlink(cr, uid, ids, context=context)

    def sync_poi_status(self, cr, uid, ids, context=None):
        """
        查询门店信息
        """
        poi = self.browse(cr, uid, ids[0], context)

        if poi.poi_id and poi.app_id:

            o = poi.app_id
            client_obj = Client(self.pool, cr, o.id, o.appid, o.appsecret, o.access_token, o.token_expires_at)
            json = client_obj.poi_getpoi(poi.poi_id)
            if "errcode" in json and json["errcode"] != 0:
                raise UserError(_(json["errmsg"]))
            else:
                image_obj = self.pool.get('tl.weixin.image')
                business_obj = self.pool.get('tl.business')
                state_obj = self.pool.get('res.country.state')
                city_obj = self.pool.get('res.country.state.area')
                district_obj = self.pool.get('res.country.state.area.subdivide')
                poi_obj = self.pool.get('tl.weixin.poi')

                business = json.get('business')
                data = business.get('base_info', False)

                if data:
                    sid = data.get('sid', False)
                    poi_id = data.get('poi_id', False)
                    # 状态
                    available_state = data.get('available_state', 1)
                    if available_state == 1:
                        state = 'draft'
                    elif available_state == 2:
                        state = 'unapproved'
                    elif available_state == 3:
                        state = 'succ'
                    else:
                        state = 'fail'

                    # 图片
                    photo_list = data.get('photo_list', False)
                    photo_list_ids = []
                    if photo_list:
                        for photo in photo_list:
                            photo_url = photo.get('photo_url')
                            # 查看图片是否存在
                            image_ids = image_obj.search(cr, uid, [('url', '=', photo_url)], context=context)
                            if not image_ids:
                                # 生成预览图片
                                image_bytes = urllib2.urlopen(photo_url).read()
                                data_stream = io.BytesIO(image_bytes)
                                image = Image.open(data_stream).convert("RGBA")
                                output = StringIO.StringIO()
                                image.save(output, 'PNG')
                                output.seek(0)
                                output_s = output.read()
                                image = base64.b64encode(output_s)
                                v_image = {
                                    'url': photo_url,
                                    'image': image,
                                    'app_id': o.id,
                                    'name': data.get('business_name', False)
                                }
                                new_image_id = image_obj.create(cr, uid, v_image, context=context)

                                photo_list_ids.append(new_image_id)
                            else:
                                photo_list_ids.append(image_ids[0])

                    # 分类
                    business_id = False
                    sub_business_id = False
                    categories = data.get('categories', [])[0],
                    if categories:
                        categories = categories[0]
                        business_id, sub_business_id = categories.split(',')
                        business_id = business_obj.search(cr, uid, [('name', '=', business_id)], context=context)
                        sub_business_id = business_obj.search(cr, uid, [('name', '=', sub_business_id)],
                                                              context=context)

                    # 省市县
                    province_ids = state_obj.search(cr, uid, [('name', '=', data.get('province', False))],
                                                    context=context)
                    city_ids = city_obj.search(cr, uid, [('name', '=', data.get('city', False))], context=context)
                    district_ids = district_obj.search(cr, uid, [('name', '=', data.get('district', False))],
                                                       context=context)
                    update_status = str(data.get('update_status'))

                    val_update = {
                        "sid": data.get('sid', False),
                        "app_id": o.id,
                        'business_id': business_id and business_id[0] or False,
                        'sub_business_id': sub_business_id and sub_business_id[0] or False,
                        "name": data.get('business_name', False),
                        "branch_name": data.get('branch_name', False),
                        "state_id": province_ids and province_ids[0] or False,
                        "city_id": city_ids and city_ids[0] or False,
                        "district_id": district_ids and district_ids[0] or False,
                        "address": data.get('address', False),
                        "telephone": data.get('telephone', False),
                        "offset_type": data.get('offset_type', False),
                        "longitude": data.get('longitude', False),
                        "latitude": data.get('latitude', False),
                        "image_ids": [[6, 0, list(set(photo_list_ids))]],
                        "recommend": data.get('recommend', False),
                        "special": data.get('special', False),
                        "introduction": data.get('introduction', False),
                        "open_time": data.get('open_time', False),
                        "avg_price": data.get('avg_price', False),
                        'state': state,
                        'auto': True,
                        'poi_id': data.get('poi_id', False),
                        'update_status': update_status,
                    }
                    poi_obj.write(cr, uid, poi.id, val_update, context=context)

            return True

    def draft_to_unapproved(self, cr, uid, ids, context=None):

        poi = self.browse(cr, uid, ids, context)
        if poi.sub_business_id:
            categories = '%s,%s' % (poi.business_id.name, poi.sub_business_id.name)
        else:
            categories = '%s' % (poi.business_id.name)
        photo_list = []
        for image in poi.image_ids:
            v = {'photo_url': image.url}
            photo_list.append(v)

        vals = {
            "sid": poi.sid,
            "business_name": poi.name,
            "branch_name": poi.branch_name,
            "province": poi.state_id.name or '',
            "city": poi.city_id.name or '',
            "district": poi.district_id.name or '',
            "address": poi.address,
            "telephone": poi.telephone,
            "categories": categories,
            "offset_type": poi.offset_type,
            "longitude": poi.longitude,
            "latitude": poi.latitude,
            "photo_list": photo_list,
            "recommend": poi.recommend or '',
            "special": poi.special or '',
            "introduction": poi.introduction or '',
            "open_time": poi.open_time or '',
            "avg_price": poi.avg_price or 0,
        }

        app_obj = self.pool.get('tl.weixin.app')
        o = app_obj.browse(cr, uid, poi.app_id.id, context)
        client_obj = Client(self.pool, cr, o.id, o.appid, o.appsecret, o.access_token, o.token_expires_at)
        json = client_obj.poi_addpoi(vals)

        if "errcode" in json and json["errcode"] != 0:
            raise UserError(_(json["errmsg"]))
        else:
            state = 'unapproved'
            self.write(cr, uid, ids, {'state': state}, context=context)
        return True


class tl_weixin_image(models.Model):
    """
        微信门店图片
    """
    _name = 'tl.weixin.image'
    _description = u"微信门店图片"

    # 获取默认公司
    def _default_company_id(self, cr, uid, context=None):
        if not context.get('company_id', False):
            company_id = self.pool.get('res.users').browse(cr, uid, uid, context).company_id.id
        else:
            company_id = context.get('company_id', False)
        return company_id

    name = fields.Char(u'名称', size=225, required=True)
    company_id = fields.Many2one('res.company', u'公司', select=True)
    app_id = fields.Many2one('tl.weixin.app', u'微信公众号', required=True)
    url = fields.Text(u'图片地址', help=u"图片地址")
    image = openerp.fields.Binary("图片", attachment=True, required=True,
                                  help=u"上传的图片限制文件大小限制1MB，支持JPG 格式。")

    _defaults = {
        'company_id': _default_company_id,
    }

    def create(self, cr, uid, vals, context=None):

        if not vals.get('url', False):
            app_obj = self.pool.get('tl.weixin.app')
            o = app_obj.browse(cr, uid, vals.get('app_id', False), context)
            client_obj = Client(self.pool, cr, o.id, o.appid, o.appsecret, o.access_token, o.token_expires_at)

            src = vals.get('image', False)
            image_stream = StringIO.StringIO(src.decode('base64'))
            image = Image.open(image_stream)

            if image.size[0] > 640 or image.size[1] > 340:
                raise UserError(_(u'错误', u'图片大小建议640px*340px 。'))

            file_format = image.format
            if file_format not in ('PNG', 'JPEG', 'JPG'):
                raise UserError(_(u'图片格式限定 JPG,JPEG,PNG。'))

            output = StringIO.StringIO()
            image.save(output, file_format)
            output.seek(0)
            output_s = output.read()

            # 临时文件名
            file_name = '%s.%s' % ('temp', file_format)
            json = client_obj.media_uploadimg(output_s, file_name)
            image_stream.close()
            output.close()

            if "errcode" in json and json["errcode"] != 0:
                raise UserError(_(json["errmsg"]))
            else:
                vals['url'] = json['url']
        return super(tl_weixin_image, self).create(cr, uid, vals, context=context)


# 微信素材管理
class tl_weixin_material(models.Model):
    _name = "tl.weixin.material"
    _description = u'微信素材管理'

    # 获取默认公司
    def _default_company_id(self, cr, uid, context=None):
        if not context.get('company_id', False):
            company_id = self.pool.get('res.users').browse(cr, uid, uid, context).company_id.id
        else:
            company_id = context.get('company_id', False)
        return company_id

    app_id = fields.Many2one('tl.weixin.app', u'公众号', required=True, ondelete="cascade")
    name = fields.Char(u'标题', size=255, help=u"图文消息的标题", required=True)
    url = fields.Text(u'URL', help=u"图文页的URL，或者，当获取的列表是图片素材列表时，该字段是图片的URL")
    update_time = fields.Datetime(u'更新时间', help=u'这篇图文消息素材的最后更新时间', readonly="1")
    file_name = fields.Char(u'文件名称', size=512, help=u"文件名称")
    type = fields.Selection(
        [('image', u'图片'), ('video', u'视频'), ('voice', u'语音 '), ('thumb', u'缩略图'), ('news', u'图文')], u'素材类型',
        required=True, help=u"素材的类型，图片（image）、视频（video）、语音 （voice）、图文（news）")
    company_id = fields.Many2one('res.company', u'公司', select=True)
    # shop_id = fields.Many2one('tl.shop', u'商户')
    media_id = fields.Char(u'素材编号', readonly="1")
    article_ids = fields.One2many('tl.weixin.articles', 'material_id', u'图文素材', )
    introduction = fields.Text(u'描述', help=u"素材的描述信息")
    annex = openerp.fields.Binary(u"附件", attachment=True,
                                  help=u"上传图文消息内的图片获取URL 请注意，本接口所上传的图片不占用公众号的素材库中图片数量的5000个的限制。图片仅支持jpg/png格式，大小必须在1MB以下")

    _defaults = {
        'company_id': _default_company_id,
        'type': 'image'
    }

    def create(self, cr, uid, vals, context=None):

        material_id = super(tl_weixin_material, self).create(cr, uid, vals, context=context)
        material = self.browse(cr, uid, material_id, context)

        # 将数据提交到微信
        app_obj = self.pool.get('tl.weixin.app')
        o = app_obj.browse(cr, uid, int(material.app_id.id), context)
        if o and not material.media_id:
            if material.type in ('video', 'voice'):
                raise UserError(_(u'暂不支持上传视频和音频,正在完善中'))

            client_obj = Client(self.pool, cr, o.id, o.appid, o.appsecret, o.access_token, o.token_expires_at)

            if material.type == 'news':
                # 图文消息
                articles = []
                for article in material.article_ids:
                    article_vals = {
                        'thumb_media_id': article.thumb_media_id.media_id,
                        'title': article.name,
                        'author': article.author,
                        'digest': article.digest,
                        'show_cover_pic': article.show_cover_pic and 1 or 0,
                        'content': article.content,
                        'content_source_url': article.content_source_url,
                    }
                    articles.append(article_vals)
                json = client_obj.material_add_news(articles)
                if "errcode" in json and json["errcode"] != 0:
                    raise UserError(_(json["errmsg"]))
                else:
                    vals['media_id'] = json['media_id']
                    update_vals = {
                        'media_id': json['media_id'],
                    }
                    self.write(cr, uid, material_id, update_vals, context)
            else:
                # 视频，音频，图片
                src = material.annex
                file_stream = StringIO.StringIO(src.decode('base64'))
                file_name = material.file_name
                json = client_obj.material_add_material(material.type, file_stream, file_name, material.name,
                                                        material.introduction)
                if "errcode" in json and json["errcode"] != 0:
                    raise UserError(_(json["errmsg"]))
                else:
                    update_vals = {
                        'media_id': json['media_id'],
                        'url': json['url'],
                    }
                    self.write(cr, uid, material_id, update_vals, context)
        return material_id


# 图文素材
# TODO 增加上传内容中图片的接口, 因为content中可能需要图片
class tl_weixin_articles(models.Model):
    _name = "tl.weixin.articles"
    _description = u'图文素材'

    material_id = fields.Many2one('tl.weixin.material', u'素材编号', select=True)
    name = fields.Char(u'标题', size=255, help=u"图文消息的标题", required=True)
    thumb_media_id = fields.Many2one('tl.weixin.material', u'封面图片素材编号', help=u'图文消息的封面图片素材id（必须是永久mediaID）',
                                     select=True, required=True)
    show_cover_pic = fields.Boolean(u'是否显示封面', required=True, help=u'是否显示封面，0为false，即不显示，1为true，即显示')
    author = fields.Char(u'作者', size=255, help=u"作者", required=True, )
    digest = fields.Char(u'摘要', help=u"图文消息的摘要，仅有单图文消息才有摘要，多图文此处为空", required=True, )

    content = fields.Text(u'内容', help=u"图文消息的具体内容，支持HTML标签，必须少于2万字符，小于1M，且此处会去除JS", required=True, )
    content_source_url = fields.Char(u'原文地址', help=u"图文消息的原文地址，即点击“阅读原文”后的URL", required=True, )

    _defaults = {

        'show_cover_pic': True
    }


# 消息事件历史
class tl_weixin_msg_history(models.Model):
    _name = "tl.weixin.msg.history"
    _description = u'消息事件历史'

    to_user_name = fields.Char(u'开发者微信号', size=255, help=u"开发者微信号", required=True)
    from_user_name = fields.Char(u'发送方帐号', size=255, help=u"发送方帐号（一个OpenID）", required=True)
    create_time = fields.Integer(u'消息创建时间', size=255, help=u"消息创建时间 （整型）", required=True)
    msg_type = fields.Selection([('text', u'文本消息'),
                                 ('image', u'图片消息'),
                                 ('voice', u'语音消息'),
                                 ('video', u'视频消息'),
                                 ('shortvideo', u'小视频消息'),
                                 ('location', u'地理位置消息'),
                                 ('link', u'链接消息'),
                                 ('subscribe', u'关注事件'),
                                 ('unsubscribe', u'取消关注事件'),
                                 ('SCAN', u'扫描带参数二维码事件'),
                                 ('LOCATION', u'上报地理位置事件'),
                                 ('CLICK', u'点击菜单拉取消息时的事件推送'),
                                 ('VIEW', u'点击菜单跳转链接时的事件推送'),
                                 ],
                                u'消息类型', help=u"消息类型", required=True, )
    msg_id = fields.Char(u'消息id', size=128, help=u"消息id，64位整型")
    content = fields.Text(u'文本消息内容', help=u"文本消息内容")
    pic_url = fields.Text(u'图片链接', help=u"图片链接")
    media_id = fields.Text(u'消息媒体id', help=u"消息媒体id，可以调用多媒体文件下载接口拉取数据。")
    format = fields.Char(u'语音格式', size=255, help=u"语音格式，如amr，speex等", )
    thumb_media_id = fields.Text(u'缩略图的媒体id', help=u"缩略图的媒体id，可以调用多媒体文件下载接口拉取数据。")

    location_x = fields.Char(u'地理位置维度', size=255, help=u"地理位置维度", )
    location_y = fields.Char(u'地理位置经度', size=255, help=u"地理位置经度", )
    precision = fields.Char(u'地理位置精度',size=255,help=u'地理位置精度')
    scale = fields.Char(u'地图缩放大小', size=255, help=u"地图缩放大小", )
    label = fields.Char(u'地理位置信息', help=u"地理位置信息", )
    title = fields.Char(u'消息标题', help=u"消息标题", )
    description = fields.Text(u'消息描述', size=255, help=u"消息描述", )
    url = fields.Char(u'消息链接', help=u"消息链接", )

    event_key = fields.Char(u'事件KEY值', help=u"事件KEY值，qrscene_为前缀，后面为二维码的参数值", )
    ticket = fields.Char(u'二维码的ticket', help=u"二维码的ticket，可用来换取二维码图片", )
    app_id = fields.Many2one('tl.weixin.app', u'公众号', select=True)
    user_id = fields.Many2one('tl.weixin.users', u'关注者', select=True, )

    msg_event_id = fields.Char(u'事件id',size=255 ,help=u"事件id，由FromUserName+CreateTime组成")
    xml_content = fields.Text(u'XML数据包原始内容',help=u"微信服务器POST的XML数据包")


