# -*- coding: utf-8 -*-
##############################################################################
#  COMPANY: BONN
#  AUTHOR: KIWI
#  EMAIL: arborous@gmail.com
#  VERSION : 1.0   NEW  2015/12/12
#  UPDATE : NONE
#  Copyright (C) 2011-2016 www.mychinavip.com All Rights Reserved
##############################################################################

import requests
from lxml import etree
from requests.compat import json as _json
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp import SUPERUSER_ID
import utils
import logging
import time
from HTMLParser import HTMLParser
import urllib2
import hashlib
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)
import os

BASE_DIR = os.path.dirname(os.path.dirname(__file__))


class ClientException(Exception):
    pass


wx_errcode = {
    '-1': u'系统繁忙，请稍候再试',
    '0': u'请求成功',
    '5': u'摇周边ticket过期,检查是不是从微信摇一摇进入',
    '11002': u'摇一摇ticket不存在,检查是不是从微信摇一摇进入',
    '11003': u'无效的摇一摇ticket,检查是不是从微信摇一摇进入',
    '11004': u'获取商户appid失败,检查是不是从微信摇一摇进入',
    '11005': u'摇周边频率检查失败,检查是不是从微信摇一摇进入',
    '11009': u'系统异常,请重试',
    '11010': u'随机字符串长度过长,对自定义页面时调jsapi参数校验出错，请检查',
    '11011': u'LotteryID解析失败,对自定义页面时调jsapi参数校验出错，请检查',
    '11012': u'签名校验失败,对自定义页面时调jsapi参数校验出错，请检查',
    '11013': u'openid无效,对自定义页面时调jsapi参数校验出错，请检查',
    '11014': u'pass_ticket无效,检查是不是从微信摇一摇进入',
    '12013': u'绑定用户和红包失败,抽到红包ticket后，微信支付返回的错误',
    '12014': u'微信支付查询红包ticket失败,抽到红包ticket后，微信支付返回的错误',
    '12015': u'抽奖操作频率过高,请重试',
    '12019': u'page_id无效',
    '40001': u'获取access_token时AppSecret错误，或者access_token无效。请认真比对AppSecret的正确性，或查看是否正在为恰当的公众号调用接口',
    '40002': u'不合法的凭证类型',
    '40003': u'不合法的OpenID，请开发者确认OpenID（该用户）是否已关注公众号，或是否是其他公众号的OpenID',
    '40004': u'不合法的媒体文件类型',
    '40005': u'不合法的文件类型',
    '40006': u'不合法的文件大小',
    '40007': u'不合法的媒体文件id',
    '40008': u'不合法的消息类型',
    '40009': u'不合法的图片文件大小',
    '40010': u'不合法的语音文件大小',
    '40011': u'不合法的视频文件大小',
    '40012': u'不合法的缩略图文件大小',
    '40013': u'不合法的AppID，请检查AppID的正确性，避免异常字符，注意大小写',
    '40014': u'不合法的access_token，请认真比对access_token的有效性（如是否过期），或查看是否正在为恰当的公众号调用接口',
    '40015': u'不合法的菜单类型',
    '40016': u'不合法的按钮个数',
    '40017': u'不合法的按钮个数',
    '40018': u'不合法的按钮名字长度',
    '40019': u'不合法的按钮KEY长度',
    '40020': u'不合法的按钮URL长度',
    '40021': u'不合法的菜单版本号',
    '40022': u'不合法的子菜单级数',
    '40023': u'不合法的子菜单按钮个数',
    '40024': u'不合法的子菜单按钮类型',
    '40025': u'不合法的子菜单按钮名字长度',
    '40026': u'不合法的子菜单按钮KEY长度',
    '40027': u'不合法的子菜单按钮URL长度',
    '40028': u'不合法的自定义菜单使用用户',
    '40029': u'不合法的oauth_code',
    '40030': u'不合法的refresh_token',
    '40031': u'不合法的openid列表',
    '40032': u'不合法的openid列表长度',
    '40033': u'不合法的请求字符，不能包含\ uxxxx格式的字符',
    '40035': u'不合法的参数',
    '40038': u'不合法的请求格式',
    '40039': u'不合法的URL长度',
    '40050': u'不合法的分组id',
    '40051': u'分组名字不合法',
    '40053': u'不合法的actioninfo，请开发者确认参数正确。',
    '40056': u'不合法的Code码',
    '40071': u'不合法的卡券类型',
    '40072': u'不合法的编码方式',
    '40073': u'卡券编号不合法',
    '40078': u'不合法的卡券状态',
    '40079': u'不合法的时间',
    '40080': u'不合法的CardExt',
    '40094': u'参数不正确，请检查json 字段',
    '40099': u'卡券已被核销',
    '40100': u'不合法的时间区间',
    '40116': u'不合法的Code码',
    '40117': u'分组名字不合法',
    '40118': u'media_id大小不合法',
    '40119': u'button类型错误',
    '40120': u'button类型错误',
    '40121': u'不合法的media_id类型',
    '40122': u'不合法的库存数量',
    '40124': u'会员卡设置查过限制的 custom_field字段',
    '40127': u'卡券被用户删除或转赠中',
    '40132': u'微信号不合法',
    '41001': u'缺少access_token参数',
    '41002': u'缺少appid参数',
    '41003': u'缺少refresh_token参数',
    '41004': u'缺少secret参数',
    '41005': u'缺少多媒体文件数据',
    '41006': u'缺少media_id参数',
    '41007': u'缺少子菜单数据',
    '41008': u'缺少oauth code',
    '41009': u'缺少openid',
    '41011': u'缺少必填字段',
    '41012': u'缺少cardid参数',
    '42001': u'access_token超时，请检查access_token的有效期，请参考基础支持-获取access_token中，对access_token的详细机制说明',
    '42002': u'refresh_token超时',
    '42003': u'oauth_code超时',
    '43001': u'需要GET请求',
    '43002': u'需要POST请求',
    '43003': u'需要HTTPS请求',
    '43004': u'需要接收者关注',
    '43005': u'需要好友关系',
    '43008': u'商户没有开通微信支付权限或者没有在商户后台申请微信买单功能',
    '43009': u'自定义SN权限，请前往公众平台申请',
    '43010': u'无储值权限，请前往公众平台申请',
    '43017': u'需要门店',
    '44001': u'多媒体文件为空',
    '44002': u'POST的数据包为空',
    '44003': u'图文消息内容为空',
    '44004': u'文本消息内容为空',
    '45001': u'多媒体文件大小超过限制',
    '45002': u'消息内容超过限制',
    '45003': u'标题字段超过限制',
    '45004': u'描述字段超过限制',
    '45005': u'链接字段超过限制',
    '45006': u'图片链接字段超过限制',
    '45007': u'语音播放时间超过限制',
    '45008': u'图文消息超过限制',
    '45009': u'接口调用超过限制',
    '45010': u'创建菜单个数超过限制',
    '45015': u'回复时间超过限制',
    '45016': u'系统分组，不允许修改',
    '45017': u'分组名字过长',
    '45018': u'分组数量超过上限',
    '45021': u'字段超过长度限制，请参考相应接口的字段说明',
    '45030': u'该cardid无接口权限',
    '45033': u'用户领取次数超过限制get_limit',
    '46001': u'不存在媒体数据',
    '46002': u'不存在的菜单版本',
    '46003': u'不存在的菜单数据',
    '46004': u'不存在的用户',
    '47001': u'解析JSON/XML内容错误',
    '48001': u'api功能未授权，请确认公众号已获得该接口，可以在公众平台官网-开发者中心页中查看接口权限',
    '50001': u'用户未授权该api',
    '50002': u'用户受限，可能是违规后接口被封禁',
    '61451': u'参数错误(invalid parameter)',
    '61452': u'无效客服账号(invalid kf_account)',
    '61453': u'客服帐号已存在(kf_account exsited)',
    '61454': u'客服帐号名长度超过限制(仅允许10个英文字符，不包括@及@后的公众号的微信号)(invalid kf_acount length)',
    '61455': u'客服帐号名包含非法字符(仅允许英文+数字)(illegal character in kf_account)',
    '61456': u'客服帐号个数超过限制(10个客服账号)(kf_account count exceeded)',
    '61457': u'无效头像文件类型(invalid file type)',
    '61450': u'系统错误(system error)',
    '61500': u'日期格式错误',
    '61501': u'日期范围错误',

    '65104': u'门店的类型不合法，必须严格按照附表的分类填写',
    '65105': u'图片url 不合法，必须使用接口1 的图片上传接口所获取的url',
    '65106': u'门店状态必须未审核通过',
    '65107': u'门店信息暂时不允许修改，微信正在审核上次修改的内容',
    '65109': u'门店名为空',
    '65110': u'门店所在详细街道地址为空',
    '65111': u'门店的电话为空',
    '65112': u'门店所在的城市为空',
    '65113': u'门店所在的省份为空',
    '65114': u'图片列表为空',
    '65115': u'poi_id 不正确',
    '9001001': u'POST数据参数不合法',
    '9001002': u'远端服务不可用',
    '9001003': u'Ticket不合法',
    '9001004': u'获取摇周边用户信息失败',
    '9001005': u'获取商户信息失败',
    '9001006': u'获取OpenID失败',
    '9001007': u'上传文件缺失',
    '9001008': u'上传素材的文件类型不合法',
    '9001009': u'上传素材的文件尺寸不合法',
    '9001010': u'上传失败',
    '9001020': u'帐号不合法',
    '9001021': u'已有设备激活率低于50%，不能新增设备',
    '9001022': u'设备申请数不合法，必须为大于0的数字',
    '9001023': u'已存在审核中的设备ID申请',
    '9001024': u'一次查询设备ID数量不能超过50',
    '9001025': u'设备ID不合法',
    '9001026': u'页面ID不合法',
    '9001027': u'页面参数不合法',
    '9001028': u'一次删除页面ID数量不能超过10',
    '9001029': u'页面已应用在设备中，请先解除应用关系再删除',
    '9001030': u'一次查询页面ID数量不能超过50',
    '9001031': u'时间区间不合法',
    '9001032': u'保存设备与页面的绑定关系参数错误',
    '9001033': u'商户ID不合法',
    '9001034': u'设备备注信息过长',
    '9001035': u'设备申请参数不合法',
    '9001036': u'查询起始值begin不合法',

}


def check_error(json):
    """
    检测微信公众平台返回值中是否包含错误的返回码。
    """
    if "errcode" in json and json["errcode"] != 0:

        errmsg = str(json["errmsg"])
        if wx_errcode.has_key(str(json["errcode"])):
            errmsg = wx_errcode[str(json["errcode"])]
        _logger.warn(u"{}: {}".format(json["errcode"], errmsg))
        return {"errcode": json["errcode"], "errmsg": errmsg}
    return json


class MLStripper(HTMLParser):
    def __init__(self):
        self.reset()
        self.fed = []

    def handle_data(self, d):
        self.fed.append(d)

    def get_data(self):
        return ''.join(self.fed)


class Client(object):
    """
    微信 API 操作类
    通过这个类可以方便的通过微信 API 进行一系列操作，比如主动发送消息、创建自定义菜单等
    """

    def __init__(self, pool, cr, public_account_id, appid, appsecret, token=None, token_expires_at=None):
        self.pool = pool
        self.cr = cr
        self.public_account_id = public_account_id
        self.appid = appid
        self.appsecret = appsecret
        self._token = token
        self.token_expires_at = token_expires_at

    def request(self, method, url, **kwargs):
        if "params" not in kwargs:
            kwargs["params"] = {"access_token": self.token}
        if isinstance(kwargs.get("data", ""), dict):
            body = _json.dumps(kwargs["data"], ensure_ascii=False)
            body = body.encode('utf8')
            kwargs["data"] = body
        r = requests.request(
            method=method,
            url=url,
            **kwargs
        )
        r.raise_for_status()
        json = r.json()

        _logger.info(u"调用方法：%s,地址：%s,参数：%s。返回结果:%s", method, url, kwargs, json)

        if '40001' == json.get('errcode', False):
            # 强制刷新TOKEN
            self.token(True)

        return check_error(json)

    def get(self, url, **kwargs):
        return self.request(
            method="get",
            url=url,
            **kwargs
        )

    def post(self, url, **kwargs):
        return self.request(
            method="post",
            url=url,
            **kwargs
        )

    def grant_token(self):
        """
        获取 Access Token 。
        详情请参考 http://mp.weixin.qq.com/wiki/index.php?title=通用接口文档
        :return: 返回的 JSON 数据包
        """
        return self.get(
            url="https://api.weixin.qq.com/cgi-bin/token",
            params={
                "grant_type": "client_credential",
                "appid": self.appid,
                "secret": self.appsecret
            }
        )

    def get_openid_by_code(self, code):
        """
        获取 openid
        详情请参考 http://mp.weixin.qq.com/wiki/17/c0f37d5704f0b64713d5d2c37b468d75.html
        :return: 返回的 JSON 数据包
        """
        return self.get(
            url="https://api.weixin.qq.com/sns/oauth2/access_token",
            params={
                "grant_type": "authorization_code",
                "appid": self.appid,
                "secret": self.appsecret,
                "code": code
            }
        )

    @property
    def token(self, refresh=False):
        """
        被动更新TOKEN,发现TOKEN失效后重新设置TOKEN值
        :return:
        """
        # if self.token_expires_at > 0 and not refresh:
        #     now = time.time()
        #     if self.token_expires_at - now > 60:
        #         return self._token


        if self.token_expires_at and not refresh:
            now = time.time()
            timeArray = time.strptime(self.token_expires_at, DEFAULT_SERVER_DATETIME_FORMAT)
            time_stamp = int(time.mktime(timeArray))
            if time_stamp - now > 60:
                return self._token


        json = self.grant_token()
        self._token = json["access_token"]


        # self.token_expires_at = int(time.time()) + json["expires_in"]
        self.token_expires_at = datetime.now() + timedelta(seconds=int(json["expires_in"]))

        parm = {
            'access_token': self._token,
            'token_expires_at': self.token_expires_at,
            'date_token': time.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
        }
        obj = self.pool.get('tl.weixin.app')
        obj.write(self.cr, SUPERUSER_ID, self.public_account_id, parm)
        return self._token

    def strip_tags(self, html):
        """
        清除html标签
        """

        s = MLStripper()
        s.feed(html)
        return s.get_data()

    def create_menu(self, menu_data):
        """
        创建自定义菜单 ::
        详情请参考 http://mp.weixin.qq.com/wiki/index.php?title=自定义菜单创建接口
        :param menu_data: Python 字典
        :return: 返回的 JSON 数据包
        """
        return self.post(
            url="https://api.weixin.qq.com/cgi-bin/menu/create",
            data=menu_data
        )

    def create_conditional_menu(self, menu_data):
        """
        创建自定义菜单 ::
        https://api.weixin.qq.com/cgi-bin/menu/addconditional?access_token=ACCESS_TOKEN
        :param menu_data: Python 字典
        :return: 返回的 JSON 数据包
        """
        return self.post(
            url="https://api.weixin.qq.com/cgi-bin/menu/addconditional",
            data=menu_data
        )


    def get_menu(self):
        """
        查询自定义菜单。
        详情请参考 http://mp.weixin.qq.com/wiki/index.php?title=自定义菜单查询接口
        :return: 返回的 JSON 数据包
        """
        return self.get("https://api.weixin.qq.com/cgi-bin/menu/get")

    def delete_menu(self):
        """
        删除自定义菜单。
        详情请参考 http://mp.weixin.qq.com/wiki/index.php?title=自定义菜单删除接口
        :return: 返回的 JSON 数据包
        """
        return self.get("https://api.weixin.qq.com/cgi-bin/menu/delete")

    def delete_conditional_menu(self, menuid):
        """
        删除自定义个性化菜单。
        详情请参考 https://api.weixin.qq.com/cgi-bin/menu/delconditional?access_token=ACCESS_TOKEN
        :return: 返回的 JSON 数据包
        """
        return self.post(
            url="https://api.weixin.qq.com/cgi-bin/menu/delconditional",
            data = {
                "menuid": menuid
            }
        )

    def try_match_menu(self, openid):
        """
        测试个性化菜单匹配结果
        详情请参考 https://api.weixin.qq.com/cgi-bin/menu/trymatch?access_token=ACCESS_TOKEN
        :return: 返回的 JSON 数据包
        """
        return self.post(
            url="https://api.weixin.qq.com/cgi-bin/menu/trymatch",
            data = {
                "user_id": openid
            }
        )

    def upload_media(self, media_type, media_file):
        """
        上传多媒体文件。
        详情请参考 http://mp.weixin.qq.com/wiki/index.php?title=上传下载多媒体文件
        :param media_type: 媒体文件类型，分别有图片（image）、语音（voice）、视频（video）和缩略图（thumb）
        :param media_file:要上传的文件，一个 File-object
        :return: 返回的 JSON 数据包
        """

        return self.post(
            url="http://file.api.weixin.qq.com/cgi-bin/media/upload",
            params={
                "access_token": self.token,
                "type": media_type
            },
            files={
                "media": media_file
            }
        )

    def shorturl(self, action, long_url):
        """
        将一条长链接转成短链接。
        主要使用场景： 开发者用于生成二维码的原链接（商品、支付二维码等）太长导致扫码速度和成功率下降，将原长链接通过此接口转成短链接再生成二维码将大大提升扫码速度和成功率。
        详情请参考https://api.weixin.qq.com/cgi-bin/shorturl?access_token=ACCESS_TOKEN
        :param action: 此处填long2short，代表长链接转短链接
        :param long_url:需要转换的长链接，支持http://、https://、weixin://wxpay 格式的url
        :return: 返回的 JSON 数据包
        """

        return self.post(
            url="https://api.weixin.qq.com/cgi-bin/shorturl",
            params={
                "access_token": self.token,
            },
            data={
                "action": action,
                "long_url": long_url
            }
        )

    def download_media(self, media_id):
        """
        下载多媒体文件。
        详情请参考 http://mp.weixin.qq.com/wiki/index.php?title=上传下载多媒体文件
        :param media_id: 媒体文件 ID
        :return: requests 的 Response 实例
        """
        return requests.get(
            "http://file.api.weixin.qq.com/cgi-bin/media/get",
            params={
                "access_token": self.token,
                "media_id": media_id
            }
        )

    def create_group(self, name):
        """
        创建分组
        详情请参考 http://mp.weixin.qq.com/wiki/index.php?title=分组管理接口

        :param name: 分组名字（30个字符以内）
        :return: 返回的 JSON 数据包

        """
        # name = to_text(name)
        return self.post(
            url="https://api.weixin.qq.com/cgi-bin/groups/create",
            params={
                "access_token": self.token,
            },
            data={"group": {"name": name}}
        )

    def get_groups(self):
        """
        查询所有分组
        详情请参考 http://mp.weixin.qq.com/wiki/index.php?title=分组管理接口

        :return: 返回的 JSON 数据包
        """
        return self.get(
            url="https://api.weixin.qq.com/cgi-bin/groups/get",
            params={
                "access_token": self.token,
            })

    def get_group_by_id(self, openid):
        """
        查询用户所在分组
        详情请参考 http://mp.weixin.qq.com/wiki/index.php?title=分组管理接口

        :param openid: 用户的OpenID
        :return: 返回的 JSON 数据包
        """
        return self.post(
            url="https://api.weixin.qq.com/cgi-bin/groups/getid",
            params={
                "access_token": self.token,
            },
            data={"openid": openid}
        )

    def update_group(self, group_id, name):
        """
        修改分组名
        详情请参考 http://mp.weixin.qq.com/wiki/index.php?title=分组管理接口

        :param group_id: 分组id，由微信分配
        :param name: 分组名字（30个字符以内）
        :return: 返回的 JSON 数据包
        """
        return self.post(
            url="https://api.weixin.qq.com/cgi-bin/groups/update",
            params={
                "access_token": self.token,
            },
            data={"group": {
                "id": int(group_id),
                "name": utils.to_text(name)
            }}
        )

    def move_user(self, user_id, group_id):
        """
        移动用户分组
        详情请参考 http://mp.weixin.qq.com/wiki/index.php?title=分组管理接口

        :param user_id: 用户 ID 。 就是你收到的 `Message` 的 source
        :param group_id: 分组 ID
        :return: 返回的 JSON 数据包
        """
        return self.post(
            url="https://api.weixin.qq.com/cgi-bin/groups/members/update",
            params={
                "access_token": self.token,
            },
            data={
                "openid": user_id,
                "to_groupid": group_id
            }
        )

    def batch_move_user_group(self, user_id_list, group_id):
        """
        批量移动用户分组
        详情请参考 http://mp.weixin.qq.com/wiki/index.php?title=分组管理接口

        :param user_id_list: 用户唯一标识符openid的列表（size不能超过50）
        :param group_id: 分组 ID
        :return: 返回的 JSON 数据包
        """
        return self.post(
            url="https://api.weixin.qq.com/cgi-bin/groups/members/batchupdate",
            params={
                "access_token": self.token,
            },
            data={
                "openid_list": user_id_list,
                "to_groupid": group_id
            }
        )

    def delete_user_group(self, group_id):
        """
        删除分组
        注意本接口是删除一个用户分组，删除分组后，所有该分组内的用户自动进入默认分组。
        详情请参考 http://mp.weixin.qq.com/wiki/index.php?title=分组管理接口

        :param group_id: 分组 ID
        :return: 返回的 JSON 数据包
        """
        return self.post(
            url="https://api.weixin.qq.com/cgi-bin/groups/delete",
            params={
                "access_token": self.token,
            },
            data={
                "group": {"id": int(group_id)}
            }
        )

    def get_user_info(self, openid, lang="zh_CN"):
        """
        获取用户基本信息
        详情请参考 http://mp.weixin.qq.com/wiki/index.php?title=获取用户基本信息

        :param user_id: 用户 ID 。 就是你收到的 `Message` 的 source
        :param lang: 返回国家地区语言版本，zh_CN 简体，zh_TW 繁体，en 英语
        :return: 返回的 JSON 数据包
        """
        return self.get(
            url="https://api.weixin.qq.com/cgi-bin/user/info",
            params={
                "access_token": self.token,
                "openid": openid,
                "lang": lang
            }
        )

    def get_jsapi_ticket(self):
        """
        获取jsapi_ticket
        jsapi_ticket是公众号用于调用微信JS接口的临时票据。
        正常情况下，jsapi_ticket的有效期为7200秒，通过access_token来获取。

        :return: 返回的 JSON 数据包
        """
        return self.get(
            url="https://api.weixin.qq.com/cgi-bin/ticket/getticket",
            params={
                "access_token": self.token,
                "type": "jsapi"
            }
        )

    def get_followers(self, first_user_id=None):
        """
        获取关注者列表
        详情请参考 http://mp.weixin.qq.com/wiki/index.php?title=获取关注者列表

        :param first_user_id: 可选。第一个拉取的OPENID，不填默认从头开始拉取
        :return: 返回的 JSON 数据包
        """
        params = {
            "access_token": self.token
        }
        if first_user_id:
            params["next_openid"] = first_user_id
        return self.get("https://api.weixin.qq.com/cgi-bin/user/get", params=params)

    def update_remark(self, openid, remark):
        """
        用户设置备注名
        详情请参考 https://api.weixin.qq.com/cgi-bin/user/info/updateremark?access_token=ACCESS_TOKEN

        :param openid: 用户id
        :param remark: 修改的名称
        """
        return self.post(
            url="https://api.weixin.qq.com/cgi-bin/user/info/updateremark",
            data={
                "openid": openid,
                "remark": remark
            }
        )

    def send_text_message(self, user_id, content, kf_account):
        """
        发送文本消息
        详情请参考 http://mp.weixin.qq.com/wiki/index.php?title=发送客服消息

        :param user_id: 用户 ID 。 就是你收到的 `Message` 的 source
        :param content: 消息正文
        :return: 返回的 JSON 数据包
        """

        content = self.strip_tags(content)

        if kf_account:
            return  self.post(
                url="https://api.weixin.qq.com/cgi-bin/message/custom/send",
                data={
                    "touser": user_id,
                    "msgtype": "text",
                    "text": {"content": content},
                    "customservice": {"kf_account": kf_account}
                }
            )
        else:
            return self.post(
                url="https://api.weixin.qq.com/cgi-bin/message/custom/send",
                data={
                    "touser": user_id,
                    "msgtype": "text",
                    "text": {"content": content}
                }
            )

    def send_image_message(self, user_id, media_id, kf_account):
        """
        发送图片消息
        详情请参考 http://mp.weixin.qq.com/wiki/index.php?title=发送客服消息

        :param user_id: 用户 ID 。 就是你收到的 `Message` 的 source
        :param media_id: 图片的媒体ID。 可以通过 :func:`upload_media` 上传。
        :return: 返回的 JSON 数据包
        """
        if kf_account:
            return  self.post(
                url="https://api.weixin.qq.com/cgi-bin/message/custom/send",
                data={
                    "touser": user_id,
                    "msgtype": "image",
                    "image": {"media_id": media_id},
                    "customservice": {"kf_account": kf_account}
                }
            )
        else:
            return self.post(
                url="https://api.weixin.qq.com/cgi-bin/message/custom/send",
                data={
                    "touser": user_id,
                    "msgtype": "image",
                    "image": {"media_id": media_id}
                }
            )

    def send_voice_message(self, user_id, media_id, kf_account):
        """
        发送语音消息
        详情请参考 http://mp.weixin.qq.com/wiki/index.php?title=发送客服消息

        :param user_id: 用户 ID 。 就是你收到的 `Message` 的 source
        :param media_id: 发送的语音的媒体ID。 可以通过 :func:`upload_media` 上传。
        :return: 返回的 JSON 数据包
        """
        if kf_account:
            return  self.post(
                url="https://api.weixin.qq.com/cgi-bin/message/custom/send",
                data={
                    "touser": user_id,
                    "msgtype": "voice",
                    "voice": {"media_id": media_id},
                    "customservice": {"kf_account": kf_account}
                }
            )
        else:
            return self.post(
                url="https://api.weixin.qq.com/cgi-bin/message/custom/send",
                data={
                    "touser": user_id,
                    "msgtype": "voice",
                    "voice": {"media_id": media_id}
                }
            )

    def send_video_message(self, user_id, media_id,
                           title=None, description=None):
        """
        发送视频消息
        详情请参考 http://mp.weixin.qq.com/wiki/index.php?title=发送客服消息

        :param user_id: 用户 ID 。 就是你收到的 `Message` 的 source
        :param media_id: 发送的视频的媒体ID。 可以通过 :func:`upload_media` 上传。
        :param title: 视频消息的标题
        :param description: 视频消息的描述
        :return: 返回的 JSON 数据包
        """
        video_data = {
            "media_id": media_id,
        }
        if title:
            video_data["title"] = title
        if description:
            video_data["description"] = description

        return self.post(
            url="https://api.weixin.qq.com/cgi-bin/message/custom/send",
            data={
                "touser": user_id,
                "msgtype": "video",
                "video": video_data
            }
        )

    def send_music_message(self, user_id, url, hq_url, thumb_media_id,
                           title=None, description=None):
        """
        发送音乐消息
        详情请参考 http://mp.weixin.qq.com/wiki/index.php?title=发送客服消息

        :param user_id: 用户 ID 。 就是你收到的 `Message` 的 source
        :param url: 音乐链接
        :param hq_url: 高品质音乐链接，wifi环境优先使用该链接播放音乐
        :param thumb_media_id: 缩略图的媒体ID。 可以通过 :func:`upload_media` 上传。
        :param title: 音乐标题
        :param description: 音乐描述
        :return: 返回的 JSON 数据包
        """
        music_data = {
            "musicurl": url,
            "hqmusicurl": hq_url,
            "thumb_media_id": thumb_media_id
        }
        if title:
            music_data["title"] = title
        if description:
            music_data["description"] = description

        return self.post(
            url="https://api.weixin.qq.com/cgi-bin/message/custom/send",
            data={
                "touser": user_id,
                "msgtype": "music",
                "music": music_data
            }
        )

    def send_article_message(self, user_id, articles):
        """
        发送图文消息
        详情请参考 http://mp.weixin.qq.com/wiki/index.php?title=发送客服消息

        :param user_id: 用户 ID 。 就是你收到的 `Message` 的 source
        :param articles: 一个包含至多10个 :class:`Article` 实例的数组
        :return: 返回的 JSON 数据包
        """
        articles_data = []
        for article in articles:
            articles_data.append({
                "title": article.title,
                "description": article.description,
                "url": article.url,
                "picurl": article.img
            })
        return self.post(
            url="https://api.weixin.qq.com/cgi-bin/message/custom/send",
            data={
                "touser": user_id,
                "msgtype": "news",
                "news": {
                    "articles": articles_data
                }
            }
        )


    def send_mpnews_message(self, user_id, media_id, kf_account):
        """
        发送语音消息
        详情请参考 http://mp.weixin.qq.com/wiki/index.php?title=发送客服消息

        :param user_id: 用户 ID 。 就是你收到的 `Message` 的 source
        :param media_id: 发送的语音的媒体ID。 可以通过 :func:`upload_media` 上传。
        :return: 返回的 JSON 数据包
        """
        if kf_account:
            return  self.post(
                url="https://api.weixin.qq.com/cgi-bin/message/custom/send",
                data={
                    "touser": user_id,
                    "msgtype": "mpnews",
                    "mpnews": {"media_id": media_id},
                    "customservice": {"kf_account": kf_account}
                }
            )
        else:
            return self.post(
                url="https://api.weixin.qq.com/cgi-bin/message/custom/send",
                data={
                    "touser": user_id,
                    "msgtype": "mpnews",
                    "mpnews": {"media_id": media_id}
                }
            )


    def create_qrcode(self, **data):
        """
        创建二维码
        详情请参考 http://mp.weixin.qq.com/wiki/index.php?title=生成带参数的二维码

        :param data: 你要发送的参数 dict
        :return: 返回的 JSON 数据包
        """
        return self.post(
            url="https://api.weixin.qq.com/cgi-bin/qrcode/create",
            data=data
        )

    def show_qrcode(self, ticket):
        """
        通过ticket换取二维码
        详情请参考 http://mp.weixin.qq.com/wiki/index.php?title=生成带参数的二维码

        :param ticket: 二维码 ticket 。可以通过 :func:`create_qrcode` 获取到
        :return: 返回的 Request 对象
        """
        return requests.get(
            url="https://mp.weixin.qq.com/cgi-bin/showqrcode",
            params={
                "ticket": ticket
            }
        )

    def send_preview(self, touser, msgtype, content):
        """
        预览接口

        :param user_id: 用户 ID 。 就是你收到的 `Message` 的 source
        :param content: 消息正文
        :return: 返回的 JSON 数据包
        """

        # 文本
        if msgtype == 'text':
            return self.post(
                url="https://api.weixin.qq.com/cgi-bin/message/mass/preview",
                data={
                    "touser": touser,
                    "text": {
                        "content": content
                    },
                    "msgtype": msgtype
                }
            )
        # 图文消息
        if msgtype == 'mpnews':
            return self.post(
                url="https://api.weixin.qq.com/cgi-bin/message/mass/preview",
                data={
                    "touser": touser,
                    "mpnews": {
                        "media_id": content
                    },
                    "msgtype": msgtype
                }
            )
        # 语音
        if msgtype == 'voice':
            return self.post(
                url="https://api.weixin.qq.com/cgi-bin/message/mass/preview",
                data={
                    "touser": touser,
                    "voice": {
                        "media_id": content
                    },
                    "msgtype": "voice"
                }
            )

        # 图片
        if msgtype == 'image':
            return self.post(
                url="https://api.weixin.qq.com/cgi-bin/message/mass/preview",
                data={
                    "touser": touser,
                    "image": {
                        "media_id": content
                    },
                    "msgtype": msgtype
                }
            )
        # 视频
        if msgtype == 'video':
            return self.post(
                url="https://api.weixin.qq.com/cgi-bin/message/mass/preview",
                data={
                    "touser": touser,
                    "mpvideo": {
                        "media_id": content,
                    },
                    "msgtype": msgtype
                }
            )

    def send_mass_group(self, is_to_all, group_id, msgtype, content):
        """
        组群发

        :param user_id: 用户 ID 。 就是你收到的 `Message` 的 source
        :param content: 消息正文
        :return: 返回的 JSON 数据包
        """
        url_https = "https://api.weixin.qq.com/cgi-bin/message/mass/sendall"

        # 文本
        if msgtype == 'text':
            return self.post(
                url=url_https,
                data={
                    "filter": {
                        "is_to_all": is_to_all,
                        "group_id": group_id
                    },
                    "text": {
                        "content": content
                    },
                    "msgtype": "text"
                }
            )
        # 图文消息
        if msgtype == 'mpnews':
            return self.post(
                url=url_https,
                data={
                    "filter": {
                        "is_to_all": is_to_all,
                        "group_id": group_id
                    },
                    "mpnews": {
                        "media_id": content
                    },
                    "msgtype": "mpnews"
                }
            )
        # 语音
        if msgtype == 'voice':
            return self.post(
                url=url_https,
                data={
                    "filter": {
                        "is_to_all": is_to_all,
                        "group_id": group_id
                    },
                    "voice": {
                        "media_id": content
                    },
                    "msgtype": "voice"
                }
            )

        # 图片
        if msgtype == 'image':
            return self.post(
                url=url_https,
                data={
                    "filter": {
                        "is_to_all": is_to_all,
                        "group_id": group_id
                    },
                    "image": {
                        "media_id": content
                    },
                    "msgtype": "image"
                }

            )
        # 视频
        if msgtype == 'video':
            return self.post(
                url=url_https,
                data={
                    "filter": {
                        "is_to_all": is_to_all,
                        "group_id": group_id
                    },
                    "mpvideo": {
                        "media_id": content,
                    },
                    "msgtype": "mpvideo"
                }

            )
        # TODO 增加卡券
        # if

    def send_mass_openid(self, msgtype, touser, content):
        """
        列表群发

        :param user_id: 用户 ID 。 就是你收到的 `Message` 的 source
        :param content: 消息正文
        :return: 返回的 JSON 数据包
        """
        url_https = "https://api.weixin.qq.com/cgi-bin/message/mass/send"

        # 文本
        if msgtype == 'text':
            return self.post(
                url=url_https,
                data={
                    "touser": touser,
                    "msgtype": "text",
                    "text": {"content": content}
                }
            )
        # 图文消息
        if msgtype == 'mpnews':
            return self.post(
                url=url_https,
                data={
                    "touser": touser,
                    "mpnews": {
                        "media_id": content
                    },
                    "msgtype": "mpnews"
                }
            )
        # 语音：
        if msgtype == 'voice':
            return self.post(
                url=url_https,
                data={
                    "touser": touser,
                    "voice": {
                        "media_id": content
                    },
                    "msgtype": "voice"
                }

            )
        # 图片：
        if msgtype == 'image':
            return self.post(
                url=url_https,
                data={
                    "touser": touser,
                    "image": {
                        "media_id": content
                    },
                    "msgtype": "image"
                }

            )

        # 视频：
        if msgtype == 'video':
            return self.post(
                url=url_https,
                data={
                    "touser": touser,
                    "video": {
                        "media_id": content,
                        "title": "TITLE",
                        "description": "DESCRIPTION"
                    },
                    "msgtype": "video"
                }

            )
        # TODO 增加卡券

    def send_preview_del_msg_id(self, msg_id):
        """
        删除群发
        :param msg_id: 消息msg_id
        :return: 返回的 JSON 数据包
        """
        return self.post(
            url="https://api.weixin.qq.com/cgi-bin/message/mass/delete",
            data={
                "msg_id": msg_id
            }
        )

    def send_mass_get(self, msg_id):
        """
        查询群发消息发送状态
        :param msg_id: 消息msg_id
        :return: 返回的 JSON 数据包
        """
        return self.post(
            url="https://api.weixin.qq.com/cgi-bin/message/mass/get",
            data={
                "msg_id": msg_id
            }
        )

    ############## 设备管理 Start ##############

    def devices_search(self, begin=0):
        """
        查询已有的设备ID、UUID、Major、Minor、激活状态、备注信息、关联商户、关联页面等信息。
        可指定设备ID或完整的UUID、Major、Minor查询，
        也可批量拉取设备信息列表。查询所返回的设备列表按设备ID正序排序。
        详情请参考 https://api.weixin.qq.com/shakearound/device/search
        :return: 返回的 JSON 数据包
        """
        return self.post(
            url="https://api.weixin.qq.com/shakearound/device/search",
            data={
                'type': 2,
                'begin': begin,
                "count": 50,
            }
        )

    def devices_applyid(self, quantity, apply_reason, comment, poi_id=0):
        """
        接口说明 申请配置设备所需的UUID、Major、Minor。申请成功后返回批次ID，
        可用返回的批次ID通过“查询设备ID申请状态”接口查询目前申请的审核状态。
        若单次申请的设备ID数量小于500个，系统会进行快速审核；若单次申请的设备ID数量大于等 500个 ，会在三个工作日内完成审核。
        如果已审核通过，可用返回的批次ID通过“查询设备列表”接口拉取本次申请的设备ID。 通过接口申请的设备ID，
        需先配置页面，若未配置页面，则摇不出页面信息。
        一个公众账号最多可申请200000个设备ID，如需申请的设备ID数超过最大限额，请邮件至zhoubian@tencent.com，
        详情请参考 https://api.weixin.qq.com/shakearound/device/applyid?access_token=ACCESS_TOKEN
        :return: 返回的 JSON 数据包
        """
        return self.post(
            url="https://api.weixin.qq.com/shakearound/device/applyid",
            data={
                'quantity': quantity,
                'apply_reason': apply_reason,
                "comment": comment,
                "poi_id": poi_id,
            }
        )

    def devices_applystatus(self, apply_id):
        """
        接口说明 查询设备ID申请的审核状态。若单次申请的设备ID数量小于等于500个，
        系统会进行快速审核；若单次申请的设备ID数量大于500个，则在三个工作日内完成审核。，
        详情请参考 https://api.weixin.qq.com/shakearound/device/applystatus?access_token=ACCESS_TOKEN
        :return: 返回的 JSON 数据包
        """
        return self.post(
            url="https://api.weixin.qq.com/shakearound/device/applystatus",
            data={
                "apply_id": apply_id,
            }
        )

    def devices_update(self, device_id, uuid, major, minor, comment):
        """
        接口说明 编辑设备的备注信息。可用设备ID或完整的UUID、Major、Minor指定设备，二者选其一。
        详情请参考 https://api.weixin.qq.com/shakearound/device/update?access_token=ACCESS_TOKEN
        :return: 返回的 JSON 数据包
        """
        return self.post(
            url="https://api.weixin.qq.com/shakearound/device/update",
            data={
                'device_identifier':
                    {
                        "device_id": device_id,
                        "uuid": uuid,
                        "major": major,
                        "minor": minor,
                    },
                'comment': comment
            }
        )

    def relation_devices_page(self, device_id, uuid, major, minor):
        """
        接口说明 查询设备与页面的关联关系。提供两种查询方式，
        可指定页面ID分页查询该页面所关联的所有的设备信息；
        也可根据设备ID或完整的UUID、Major、Minor查询该设备所关联的所有页面信息。
        详情请参考 https://api.weixin.qq.com/shakearound/relation/search?access_token=ACCESS_TOKEN
        :return: 返回的 JSON 数据包
        """
        return self.post(
            url="https://api.weixin.qq.com/shakearound/relation/search",
            data={
                "type": 1,
                'device_identifier':
                    {
                        "device_id": device_id,
                        "uuid": uuid,
                        "major": major,
                        "minor": minor,
                    },
            }
        )

    def bindpage_devices_page(self, device_id, uuid, major, minor, page_ids):
        """
        接口说明 配置设备与页面的关联关系，
        接口说明 配置设备与页面的关联关系。配置时传入该设备需要关联的页面的id列表（该设备原有的关联关系将被直接清除）；页面的id列表允许为空，当页面的id列表为空时则会清除该设备的所有关联关系。配置完成后，在此设备的信号范围内，即可摇出关联的页面信息。
        在申请设备ID后，可直接使用接口直接配置页面。
        若设备配置多个页面，则随机出现页面信息。一个设备最多可配置30个关联页面。
        详情请参考 https://api.weixin.qq.com/shakearound/device/bindpage?access_token=ACCESS_TOKEN
        :return: 返回的 JSON 数据包
        """
        return self.post(
            url="https://api.weixin.qq.com/shakearound/device/bindpage",
            data={
                "page_ids": page_ids,
                'device_identifier':
                    {
                        "device_id": device_id,
                        "uuid": uuid,
                        "major": major,
                        "minor": minor,
                    },
            }
        )

    def getshakeinfo(self, ticket, need_poi=0):
        """
        获取摇周边的设备及用户信息
        获取设备信息，包括UUID、major、minor，以及距离、openID等信息。
        摇周边业务的ticket，可在摇到的URL中得到，ticket生效时间为30分钟，每一次摇都会重新生成新的ticket
        详情请参考https://api.weixin.qq.com/shakearound/user/getshakeinfo?access_token=ACCESS_TOKEN
        :return: 返回的 JSON 数据包
        """
        return self.post(
            url="https://api.weixin.qq.com/shakearound/user/getshakeinfo",
            data={
                'ticket': ticket,
                'need_poi': need_poi
            }
        )

    ############## 设备管理 End ##############




    ############## 页面管理 Start ##############

    def shakearound_page_search(self, begin=0):
        """
        获取 摇一摇入口画面 ，每次只能查询50条
        详情请参考 https://api.weixin.qq.com/shakearound/page/search?access_token=
        :return: 返回的 JSON 数据包
        """
        return self.post(
            url="https://api.weixin.qq.com/shakearound/page/search",
            data={
                'type': 2,
                'begin': begin,
                "count": 50,
            }
        )

    def shakearound_page_add(self, title, page_url, description, icon_url, comment):
        """
        新增摇一摇出来的页面信息，包括在摇一摇页面出现的主标题、副标题、图片和点击进去的超链接。
        详情请参考 http://mp.weixin.qq.com/wiki/15/7a21268ed234b4e648d86e3b91118907.html
        :return: 返回的 JSON 数据包
        """
        return self.post(
            url="https://api.weixin.qq.com/shakearound/page/add",
            data={
                "title": title,
                'page_url': page_url,
                "description": description,
                "icon_url": icon_url,
                "comment": comment,
            }
        )

    def shakearound_page_update(self, page_id, title, page_url, description, icon_url, comment):
        """
        编辑摇一摇出来的页面信息，包括在摇一摇页面出现的主标题、副标题、图片和点击进去的超链接。
        详情请参考 http://mp.weixin.qq.com/wiki/15/7a21268ed234b4e648d86e3b91118907.html
        :return: 返回的 JSON 数据包
        """
        return self.post(
            url="https://api.weixin.qq.com/shakearound/page/update",
            data={
                'page_id': page_id,
                "title": title,
                'page_url': page_url,
                "description": description,
                "icon_url": icon_url,
                "comment": comment,
            }
        )

    def shakearound_page_delete(self, page_id):
        """
        删除已有的页面，包括在摇一摇页面出现的主标题、副标题、图片和点击进去的超链接。只有页面与设备没有关联关系时，才可被删除。
        详情请参考https://api.weixin.qq.com/shakearound/page/delete?access_token=ACCESS_TOKEN
        :return: 返回的 JSON 数据包
        """
        return self.post(
            url="https://api.weixin.qq.com/shakearound/page/delete",
            data={
                'page_id': page_id
            }
        )

    def material_add(self, media_file, type):
        """
        上传图片素材
        详情请参考 http://mp.weixin.qq.com/wiki/11/63e6c02a529c33a58672337f32d1c01b.html
        :return: 返回的 JSON 数据包
        """
        return self.post(
            url="https://api.weixin.qq.com/shakearound/material/add",
            params={
                "access_token": self.token,
                "type": type
            },
            files={
                "media": media_file
            }
        )

    ############## 页面管理 End ##############





    ############## 设备分组管理 End ##############


    def device_group_add(self, group_name):
        """
        新建设备分组，每个帐号下最多只有1000个分组。
        分组名称，不超过100汉字或200个英文字母
        详情请参考https://api.weixin.qq.com/shakearound/device/group/add?access_token=ACCESS_TOKEN
        :return: 返回的 JSON 数据包
        """
        return self.post(
            url="https://api.weixin.qq.com/shakearound/device/group/add",
            data={
                'group_name': group_name
            }
        )

    def device_group_update(self, group_id, group_name):
        """
        编辑设备分组信息，目前只能修改分组名。
        分组名称，不超过100汉字或200个英文字母
        详情请参考https://api.weixin.qq.com/shakearound/device/group/update?access_token=ACCESS_TOKEN
        :return: 返回的 JSON 数据包
        """
        return self.post(
            url="https://api.weixin.qq.com/shakearound/device/group/update",
            data={
                'group_id': group_id,
                'group_name': group_name
            }
        )

    def device_group_delete(self, group_id):
        """
        删除设备分组，若分组中还存在设备，则不能删除成功。需把设备移除以后，才能删除。
        详情请参考https://api.weixin.qq.com/shakearound/device/group/delete?access_token=ACCESS_TOKEN
        :return: 返回的 JSON 数据包
        """
        return self.post(
            url="https://api.weixin.qq.com/shakearound/device/group/delete",
            data={
                'group_id': group_id
            }
        )

    def device_group_getlist(self, begin):
        """
        查询账号下所有的分组。
        待查询的分组数量，不能超过1000个
        详情请参考https://api.weixin.qq.com/shakearound/device/group/getlist?    access_token=ACCESS_TOKEN
        :return: 返回的 JSON 数据包
        """
        return self.post(
            url="https://api.weixin.qq.com/shakearound/device/group/getlist",
            data={
                'begin': begin,
                'count': 1000,
            }
        )

    def device_group_getdetail(self, group_id, begin):
        """
        查询分组详情，包括分组名，分组id，分组里的设备列表。
        详情请参考https://api.weixin.qq.com/shakearound/device/group/getlist?    access_token=ACCESS_TOKEN
        :return: 返回的 JSON 数据包
        """
        return self.post(
            url="https://api.weixin.qq.com/shakearound/device/group/getdetail",
            data={
                'group_id': group_id,
                'begin': begin,
                'count': 1000,
            }
        )

    def device_group_adddevice(self, group_id, device_identifiers):
        """
        添加设备到分组
        添加设备到分组，每个分组能够持有的设备上限为10000，并且每次添加操作的添加上限为1000。
        只有在摇周边申请的设备才能添加到分组。
        详情请参考https://api.weixin.qq.com/shakearound/device/group/adddevice?access_token=ACCESS_TOKEN
        :return: 返回的 JSON 数据包
        """
        return self.post(
            url="https://api.weixin.qq.com/shakearound/device/group/adddevice",
            data={
                "group_id": group_id,
                'device_identifiers': device_identifiers,
            }
        )

    def device_group_deletedevice(self, group_id, device_identifiers):

        """
        从分组中移除设备
        从分组中移除设备，每次删除操作的上限为1000。
        详情请参考https://api.weixin.qq.com/shakearound/device/group/deletedevice?access_token=ACCESS_TOKEN
        :return: 返回的 JSON 数据包
        """
        return self.post(
            url="https://api.weixin.qq.com/shakearound/device/group/deletedevice",
            data={
                "group_id": group_id,
                'device_identifiers': device_identifiers,
            }
        )

    ############## 设备分组管理 End ##############


    ############## 门店管理 Start ##############


    def media_uploadimg(self, media_file, file_name):

        """
        1.上传门店图片
        接口说明
        用POI 接口新建门店时所使用的图片url 必须为微信域名的url，因此需要先用上传图片接口上传图片并获取url，再创建门店。
        上传的图片限制文件大小限制1MB，支持JPG 格式。
        详情请参考https://api.weixin.qq.com/cgi-bin/media/uploadimg?access_token=ACCESS_TOKEN
        :return: 返回的 JSON 数据包
        """
        return self.post(
            url="https://api.weixin.qq.com/cgi-bin/media/uploadimg",
            params={
                "access_token": self.token,
                "type": 'image'
            },

            files={
                'Filedata': (file_name, media_file, 'application/octet-stream'),
            }
        )

    def poi_addpoi(self, vals):

        """
        创建门店接口是为商户提供创建自己门店数据的接口，门店数据字段越完整，商户页面展示越丰富，越能够吸引更多用户，并提高曝光度。
        成功创建后，会生成poi_id，但该id不一定为最终id。门店信息会经过审核，
        审核通过后方可获取最终poi_id，该id为门店的唯一id，
        强烈建议自行存储审核通过后的最终poi_id，并为后续调用使用
        详情请参考http://api.weixin.qq.com/cgi-bin/poi/addpoi?access_token=TOKEN
        :return: 返回的 JSON 数据包
        """
        return self.post(
            url="http://api.weixin.qq.com/cgi-bin/poi/addpoi",
            data={
                "business": {
                    "base_info": {
                        "sid": vals.get('sid', ''),
                        "business_name": vals.get('business_name', ''),
                        "branch_name": vals.get('branch_name', ''),
                        "province": vals.get('province', ''),
                        "city": vals.get('city', ''),
                        "district": vals.get('district', ''),
                        "address": vals.get('address', ''),
                        "telephone": vals.get('telephone', ''),
                        "categories": vals.get('categories', ''),
                        "offset_type": vals.get('offset_type', ''),
                        "longitude": vals.get('longitude', 0),
                        "latitude": vals.get('latitude', 0),
                        "photo_list": vals.get('photo_list', []),
                        "recommend": vals.get('recommend', ''),
                        "special": vals.get('special', ''),
                        "introduction": vals.get('introduction', ''),
                        "open_time": vals.get('open_time', ''),
                        "avg_price": vals.get('avg_price', 0),
                    }
                }
            }
        )

    def poi_getpoilist(self, begin):
        """
        查询门店列表
        商户可以通过该接口，批量查询自己名下的门店list，并获取已审核通过的poi_id（所有状态均会返回poi_id，但该poi_id不一定为最终id）、
        商户自身sid 用于对应、商户名、分店名、地址字段。
        详情请参考https://api.weixin.qq.com/cgi-bin/poi/getpoilist?access_token=TOKEN
        :return: 返回的 JSON 数据包
        """
        return self.post(
            url="https://api.weixin.qq.com/cgi-bin/poi/getpoilist",
            data={
                'begin': begin,
                'limit': 20,
            }
        )

    def poi_updatepoi(self, vals):
        """
        商户可以通过该接口，修改门店的服务信息，
        包括：图片列表、营业时间、推荐、特色服务、简介、人均价格、电话7 个字段（名称、坐标、地址等不可修改）
        修改后需要人工审核。
        详情请参考https://api.weixin.qq.com/cgi-bin/poi/updatepoi?access_token=TOKEN
        :return: 返回的 JSON 数据包
        """
        return self.post(
            url="http://api.weixin.qq.com/cgi-bin/poi/updatepoi",
            data={
                "business": {
                    "base_info": {
                        "poi_id": vals.get('poi_id', ''),
                        "telephone": vals.get('telephone', ''),
                        "photo_list": vals.get('photo_list', []),
                        "recommend": vals.get('recommend', ''),
                        "special": vals.get('special', ''),
                        "introduction": vals.get('introduction', ''),
                        "open_time": vals.get('open_time', ''),
                        "avg_price": vals.get('avg_price', 0),
                    }
                }
            }
        )

    def poi_getpoi(self, poi_id):
        """
        创建门店后获取poi_id 后，商户可以利用poi_id，查询具体某条门店的信息。
        若在查询时，update_status 字段为1，表明在5 个工作日内曾用update 接口修改过门店扩展字段，
        该扩展字段为最新的修改字段，尚未经过审核采纳，因此不是最终结果。最终结果会在5 个工作日内，
        最终确认是否采纳，并前端生效（但该扩展字段的采纳过程不影响门店的可用性，即available_state仍为审核通过状态）
        注：扩展字段为公共编辑信息（大家都可修改），修改将会审核，并决定是否对修改建议进行采纳，
        但不会影响该门店的生效可用状态。
        详情请参考 http://api.weixin.qq.com/cgi-bin/poi/getpoi?access_token=TOKEN
        :return: 返回的 JSON 数据包
        """
        return self.post(
            url="https://api.weixin.qq.com/cgi-bin/poi/getpoi",
            data={
                "poi_id": poi_id,
            }
        )

    def poi_delpoi(self, poi_id):
        """
        商户可以通过该接口，删除已经成功创建的门店。请商户慎重调用该接口，
        门店信息被删除后，
        可能会影响其他与门店相关的业务使用，如卡券等。
        同样，该门店信息也不会在微信的商户详情页显示，不会再推荐入附近功能
        详情请参考https://api.weixin.qq.com/cgi-bin/poi/delpoi?access_token=TOKEN
        :return: 返回的 JSON 数据包
        """
        return self.post(
            url="https://api.weixin.qq.com/cgi-bin/poi/delpoi",
            data={
                'poi_id': poi_id
            }
        )

    ############## 门店管理 End ##############



    ############## 素材管理 Start ##############

    def material_add_news(self, articles):

        """
        新增永久图文素材
        1、新增的永久素材也可以在公众平台官网素材管理模块中看到
        2、永久素材的数量是有上限的，请谨慎新增。图文消息素材和图片素材的上限为5000，其他类型为1000
        3、素材的格式大小等要求与公众平台官网一致。具体是，图片大小不超过2M，支持bmp/png/jpeg/jpg/gif格式，语音大小不超过5M，长度不超过60秒，支持mp3/wma/wav/amr格式
        4、调用该接口需https协议
        详情请参考https://api.weixin.qq.com/cgi-bin/material/add_news?access_token=ACCESS_TOKEN
        :return: 返回的 JSON 数据包
        """
        return self.post(
            url="https://api.weixin.qq.com/cgi-bin/material/add_news",
            data={
                "articles": articles
            }
        )

    def material_add_material(self, type, media_file, file_name, title, introduction):

        """
        新增其他类型永久素材
        通过POST表单来调用接口，表单id为media，包含需要上传的素材内容，有filename、filelength、content-type等信息。
        请注意：图片素材将进入公众平台官网素材管理模块中的默认分组
        媒体文件类型，分别有图片（image）、语音（voice）、视频（video）和缩略图（thumb）
        详情请参考https://api.weixin.qq.com/cgi-bin/material/add_material?access_token=ACCESS_TOKEN
        :return: 返回的 JSON 数据包
        """
        return self.post(
            url="https://api.weixin.qq.com/cgi-bin/material/add_material",
            params={
                "access_token": self.token,
                "description": {
                    "title": title,
                    "introduction": introduction,
                },
                'type': type,
            },
            files={
                'media': (file_name, media_file, 'application/octet-stream'),
            }
        )

    def material_get_material(self, media_id):
        """
        在新增了永久素材后，开发者可以根据media_id来获取永久素材，需要时也可保存到本地。
        1、获取永久素材也可以获取公众号在公众平台官网素材管理模块中新建的图文消息、图片、语音、视频等素材（但需要先通过获取素材列表来获知素材的media_id）
        2、临时素材无法通过本接口获取
        3、调用该接口需https协议
        详情请参考https://api.weixin.qq.com/cgi-bin/material/get_material?access_token=ACCESS_TOKEN
        :return: 返回的 JSON 数据包
        """
        return self.post(
            url="https://api.weixin.qq.com/cgi-bin/material/get_material",
            data={
                'media_id': media_id
            }
        )

    def material_update_news(self, media_id, index, articles):
        """
        在新增了永久素材后，开发者可以根据media_id来获取永久素材，需要时也可保存到本地。
        1、也可以在公众平台官网素材管理模块中保存的图文消息（永久图文素材）
        2、调用该接口需https协议
        详情请参考https://api.weixin.qq.com/cgi-bin/material/update_news?access_token=ACCESS_TOKEN
        :return: 返回的 JSON 数据包
        """
        return self.post(
            url="https://api.weixin.qq.com/cgi-bin/material/update_news",
            data={
                'media_id': media_id,
                "index": index,
                "articles": articles
            }
        )

    def material_batchget_material(self, type, offset):
        """
        获取素材列表
        1、获取永久素材的列表，也会包含公众号在公众平台官网素材管理模块中新建的图文消息、语音、视频等素材（但需要先通过获取素材列表来获知素材的media_id）
        2、临时素材无法通过本接口获取
        3、调用该接口需https协议
        详情请参考https://api.weixin.qq.com/cgi-bin/material/batchget_material?access_token=ACCESS_TOKEN
        :return: 返回的 JSON 数据包
        """
        return self.post(
            url="https://api.weixin.qq.com/cgi-bin/material/batchget_material",
            data={
                'type': type,
                "offset": offset,
                "count": 20
            }
        )

    ############## 素材管理 End ##############

    ############## 红包管理 Start ##############

    def mmpaymkttransfers_sendredpack(self, post_data, security_key):
        """
        用于企业向微信用户个人发现金红包
        1、目前支持向指定微信用户的openid发放指定金额红包。
        详情请参考https://api.weixin.qq.com/cgi-bin/material/batchget_material?access_token=ACCESS_TOKEN
        :return: 返回的 JSON 数据包
        """
        post_data, params_str = utils.params_filter(post_data)
        sign_data = params_str + '&key=' + str(security_key)

        sign = hashlib.md5(sign_data).hexdigest().upper()
        post_data['sign'] = sign
        data_xml = "<xml>" + utils.json2xml(post_data) + "</xml>"

        apiclient_cert = os.path.join(BASE_DIR, "tools/apiclient_cert.pem")
        apiclient_key = os.path.join(BASE_DIR, "tools/apiclient_key.pem")
        rootca = os.path.join(BASE_DIR, "tools/rootca.pem")

        r = requests.request(
            method='post',
            url='https://api.mch.weixin.qq.com/mmpaymkttransfers/sendredpack',
            data=data_xml,
            cert=(apiclient_cert, apiclient_key, rootca)
        )
        result = r.content

        return_xml = etree.fromstring(result)
        return_code = return_xml.find('return_code').text
        return_msg = return_xml.find('return_msg').text
        response = {}

        response['return_code'] = return_code
        response['return_msg'] = return_msg
        if return_code == 'SUCCESS':
            result_code = return_xml.find('result_code').text
            response['result_code'] = result_code
            if result_code == 'SUCCESS':
                response['send_listid'] = return_xml.find('send_listid').text
                response['send_time'] = return_xml.find('send_time').text
                response['total_amount'] = return_xml.find('total_amount').text
                response['re_openid'] = return_xml.find('re_openid').text
                response['mch_billno'] = return_xml.find('mch_billno').text
                response['mch_id'] = return_xml.find('mch_id').text
                response['wxappid'] = return_xml.find('wxappid').text
            else:
                response['err_code_des'] = return_xml.find('err_code_des').text
                response['err_code'] = return_xml.find('err_code').text
        return response

    def mmpaymkttransfers_sendgroupredpack(self, post_data, security_key):
        """
        用于企业向微信用户个人发裂变红包
        1、目前支持向指定微信用户的openid发放指定金额裂变红包。
        详情请参考https://api.mch.weixin.qq.com/mmpaymkttransfers/sendgroupredpack
        :return: 返回的 JSON 数据包
        """
        post_data, params_str = utils.params_filter(post_data)
        sign_data = params_str + '&key=' + str(security_key)

        print(sign_data)
        sign = hashlib.md5(sign_data).hexdigest().upper()
        post_data['sign'] = sign
        data_xml = "<xml>" + utils.json2xml(post_data) + "</xml>"

        print(data_xml)
        apiclient_cert = os.path.join(BASE_DIR, "tools/apiclient_cert.pem")
        apiclient_key = os.path.join(BASE_DIR, "tools/apiclient_key.pem")
        rootca = os.path.join(BASE_DIR, "tools/rootca.pem")

        r = requests.request(
            method='post',
            url='https://api.mch.weixin.qq.com/mmpaymkttransfers/sendgroupredpack',
            data=data_xml,
            cert=(apiclient_cert, apiclient_key, rootca)
        )
        result = r.content

        return_xml = etree.fromstring(result)
        return_code = return_xml.find('return_code').text
        return_msg = return_xml.find('return_msg').text
        response = {}

        response['return_code'] = return_code
        response['return_msg'] = return_msg
        if return_code == 'SUCCESS':
            result_code = return_xml.find('result_code').text
            response['result_code'] = result_code
            if result_code == 'SUCCESS':
                response['send_listid'] = return_xml.find('send_listid').text
                response['send_time'] = return_xml.find('send_time').text
                response['total_amount'] = return_xml.find('total_amount').text
                response['re_openid'] = return_xml.find('re_openid').text
                response['mch_billno'] = return_xml.find('mch_billno').text
                response['mch_id'] = return_xml.find('mch_id').text
                response['wxappid'] = return_xml.find('wxappid').text
            else:
                response['err_code_des'] = return_xml.find('err_code_des').text
                response['err_code'] = return_xml.find('err_code').text
        return response

    def mmpaymkttransfers_hbpreorder(self, post_data, security_key):
        """
        红包预下单接口
        设置单个红包的金额，类型等，生成红包信息。预下单完成后，需要在72小时内调用jsapi完成抽红包的操作。（红包过期失效后，资金会退回到商户财付通帐号。）
        详情请参考https://api.mch.weixin.qq.com/mmpaymkttransfers/hbpreorder
        :return: 返回的 JSON 数据包
        """
        post_data, params_str = utils.params_filter(post_data)
        sign_data = params_str + '&key=' + str(security_key)

        print(sign_data)
        sign = hashlib.md5(sign_data).hexdigest().upper()
        post_data['sign'] = sign
        data_xml = "<xml>" + utils.json2xml(post_data) + "</xml>"

        apiclient_cert = os.path.join(BASE_DIR, "tools/apiclient_cert.pem")
        apiclient_key = os.path.join(BASE_DIR, "tools/apiclient_key.pem")
        rootca = os.path.join(BASE_DIR, "tools/rootca.pem")

        r = requests.request(
            method='post',
            url='https://api.mch.weixin.qq.com/mmpaymkttransfers/hbpreorder',
            data=data_xml,
            cert=(apiclient_cert, apiclient_key, rootca)
        )
        result = r.content
        print(result)
        return_xml = etree.fromstring(result)
        return_code = return_xml.find('return_code').text
        return_msg = return_xml.find('return_msg').text
        response = {}

        response['return_code'] = return_code
        response['return_msg'] = return_msg
        if return_code == 'SUCCESS':
            result_code = return_xml.find('result_code').text
            response['result_code'] = result_code
            if result_code == 'SUCCESS':
                if return_xml.find('send_listid') != None:
                    response['send_listid'] = return_xml.find('send_listid').text
                else:
                    response['send_listid'] = ''
                if return_xml.find('re_openid') != None:
                    response['re_openid'] = return_xml.find('re_openid').text
                else:
                    response['re_openid'] = ''
                response['send_time'] = return_xml.find('send_time').text
                response['total_amount'] = return_xml.find('total_amount').text
                response['mch_billno'] = return_xml.find('mch_billno').text
                response['mch_id'] = return_xml.find('mch_id').text
                response['wxappid'] = return_xml.find('wxappid').text
                # 摇一摇红包
                if return_xml.find('sp_ticket') != None:
                    response['sp_ticket'] = return_xml.find('sp_ticket').text
                else:
                    response['sp_ticket'] = ''
                if return_xml.find('detail_id') != None:
                    response['detail_id'] = return_xml.find('detail_id').text
                else:
                    response['detail_id'] = ''
            else:
                response['err_code_des'] = return_xml.find('err_code_des').text
                response['err_code'] = return_xml.find('err_code').text
        return response

    def lottery_addlotteryinfo(self, data, use_template, logo_url):
        """
        创建红包活动
        创建红包活动，设置红包活动有效期，红包活动开关等基本信息，返回活动id
        详情请参考 https://api.weixin.qq.com/shakearound/lottery/addlotteryinfo?access_token=ACCESSTOKEN&use_template=1&logo_url=LOGO_URL
        :return: 返回的 JSON 数据包
        """
        return self.post(
            url="https://api.weixin.qq.com/shakearound/lottery/addlotteryinfo?access_token",
            params={
                "access_token": self.token,
                "use_template": use_template,
                "logo_url": logo_url
            },
            data=data
        )

    def lottery_setprizebucket(self, data):
        """
        录入红包信息
        接口说明
        在调用"创建红包活动"接口之后，调用此接口录入红包信息。
        注意，此接口每次调用，都会向某个活动新增一批红包信息，如果红包数少于100个，请通过一次调用添加所有红包信息。
        如果红包数大于100，可以多次调用接口添加。
        请注意确保多次录入的红包ticket总的数目不大于创建该红包活动时设置的total值。
        详情请参考 https://api.weixin.qq.com/shakearound/lottery/setprizebucket?access_token=ACCESSTOKEN
        :return: 返回的 JSON 数据包
        """
        return self.post(
            url="https://api.weixin.qq.com/shakearound/lottery/setprizebucket",
            params={
                "access_token": self.token,
            },
            data=data
        )

    def lottery_setprizebucket(self, lottery_id, onoff):
        """
        设置红包活动抽奖开关
        接口说明
        开发者实时控制红包活动抽奖的开启和关闭。注意活动抽奖开关只在红包活动有效期之内才能生效，如果不能确定红包活动有效期，请尽量将红包活动有效期的范围设置大。
        详情请参考 https://api.weixin.qq.com/shakearound/lottery/setlotteryswitch?access_token=ACCESSTOKEN&lottery_id=LOTTERYID&onoff=1
        :return: 返回的 JSON 数据包
        """
        return self.post(
            url="https://api.weixin.qq.com/shakearound/lottery/setlotteryswitch",
            params={
                "access_token": self.token,
                "lottery_id": lottery_id,
                "onoff": onoff,
            }
        )

    ############## 红包管理 End ##############




    ############## 卡券管理 Start ##############

    def card_create(self, data):
        """
        录入红包信息
        接口说明
        创建卡券接口是微信卡券的基础接口，用于创建一类新的卡券，获取card_id，
        创建成功并通过审核后，商家可以通过文档提供的其他接口将卡券下发给用户，每次成功领取，库存数量相应扣除。
        开发者须知
        1.需自定义Code码的商家必须在创建卡券时候，设定use_custom_code为true，
        且在调用投放卡券接口时填入指定的Code码。指定OpenID同理。特别注意：在公众平台创建的卡券均为非自定义Code类型。
        2.can_share字段指领取卡券原生页面是否可分享，建议指定Code码、
        指定OpenID等强限制条件的卡券填写false。
        3.特别注意：编码方式仅支持使用UTF-8，否则会报错。
        4.创建成功后该卡券会自动提交审核，审核结果将通过事件通知商户。
        开发者可调用设置白名单接口设置用户白名单，领取未通过审核的卡券，测试整个卡券的使用流程。
        详情请参考 https://api.weixin.qq.com/card/create?access_token=ACCESS_TOKEN
        :return: 返回的 JSON 数据包
        """
        return self.post(
            url="https://api.weixin.qq.com/card/create",
            params={
                "access_token": self.token,
            },
            data={
                'card': data
            }
        )

    def card_get(self, card_id):
        """
        查看卡券详情
        接口说明
        调用该接口可查询卡券字段详情及卡券所处状态。建议开发者调用卡券更新信息接口后调用该接口验证是否更新成功。
        开发者注意事项
        1.对于部分有特殊权限的商家，查询卡券详情得到的返回可能含特殊接口的字段。
        2.由于卡券字段会持续更新，实际返回字段包含但不限于文档中的字段，建议开发者开发时对于不理解的字段不做处理，以免出错。
        详情请参考 https://api.weixin.qq.com/card/get?access_token=TOKEN
        :return: 返回的 JSON 数据包
        """
        return self.post(
            url="https://api.weixin.qq.com/card/get",
            params={
                "access_token": self.token,
            },
            data={
                'card_id': card_id
            }
        )

    def card_batchget(self, offset, status_list):
        """
        批量查询卡券列表
        详情请参考 https://api.weixin.qq.com/card/batchget?access_token=TOKEN
        :return: 返回的 JSON 数据包
        """
        return self.post(
            url="https://api.weixin.qq.com/card/batchget",
            params={
                "access_token": self.token,
            },
            data={
                'offset': offset,
                'count': 50,
                'status_list': status_list
            }
        )

    def card_paycell_set(self, card_id, is_open):
        """
        设置快速买单
        功能介绍
        微信卡券买单功能是微信卡券的一项新的能力，可以方便消费者买单时，直接录入消费金额，自动使用领到的优惠（券或卡）抵扣，并拉起微信支付快速完成付款。
        微信买单（以下统称微信买单）的好处：
        1、无需商户具备微信支付开发能力，即可完成订单生成，与微信支付打通。
        2、可以通过手机公众号、电脑商户后台，轻松操作收款并查看核销记录，交易对账，并支持离线下载。
        3、支持会员营销，二次营销，如会员卡交易送积分，抵扣积分，买单后赠券等。
        详情请参考 https://api.weixin.qq.com/card/paycell/set?access_token=TOKEN
        :return: 返回的 JSON 数据包
        """
        return self.post(
            url="https://api.weixin.qq.com/card/paycell/set",
            params={
                "access_token": self.token,
            },
            data={
                'card_id': card_id,
                'is_open': is_open
            }
        )

    def card_modifystock(self, card_id, increase_stock_value, reduce_stock_value):
        """
        修改库存接口
        功能介绍
        调用修改库存接口增减某张卡券的库存。
        increase_stock_value:增加多少库存，支持不填或填0。
        reduce_stock_value:减少多少库存，可以不填或填0。
        详情请参考 https://api.weixin.qq.com/card/modifystock?access_token=TOKEN
        :return: 返回的 JSON 数据包
        """
        return self.post(
            url="https://api.weixin.qq.com/card/modifystock",
            params={
                "access_token": self.token,
            },
            data={
                'card_id': card_id,
                'increase_stock_value': increase_stock_value,
                'reduce_stock_value': reduce_stock_value
            }
        )

    def card_delete(self, card_id):
        """
        删除卡券接口
        功能介绍
        删除卡券接口允许商户删除任意一类卡券。删除卡券后，该卡券对应已生成的领取用二维码、添加到卡包JS API均会失效。
        注意：如用户在商家删除卡券前已领取一张或多张该卡券依旧有效。即删除卡券不能删除已被用户领取，保存在微信客户端中的卡券。
        详情请参考 https://api.weixin.qq.com/card/delete?access_token=TOKEN
        :return: 返回的 JSON 数据包
        """
        return self.post(
            url="https://api.weixin.qq.com/card/delete",
            params={
                "access_token": self.token,
            },
            data={
                'card_id': card_id
            }
        )

    def card_unavailable(self, card_id, code):
        """
        设置卡券失效接口
        功能介绍
        为满足改票、退款等异常情况，可调用卡券失效接口将用户的卡券设置为失效状态。
        注：设置卡券失效的操作不可逆，即无法将设置为失效的卡券调回有效状态，商家须慎重调用该接口。
        详情请参考 https://api.weixin.qq.com/card/code/unavailable?access_token=TOKEN
        :return: 返回的 JSON 数据包
        """
        return self.post(
            url="https://api.weixin.qq.com/card/code/unavailable",
            params={
                "access_token": self.token,
            },
            data={
                'card_id': card_id,
                'code': code
            }
        )

    def card_qrcode_create(self, data):
        """
        创建二维码接口
        开发者可调用该接口生成一张卡券二维码供用户扫码后添加卡券到卡包。
        自定义Code码的卡券调用接口时，post数据中需指定code，非自定义code不需指定，指定openid同理。指定后的二维码只能被用户扫描领取一次。
        注：该接口仅支持卡券功能，供已开通卡券功能权限的商户（订阅号、服务号）调用。 已认证服务号的商户也可使用高级接口中生成带参数的二维码接口生成卡券二维码。
        获取二维码ticket后，开发者可用通过ticket换取二维码接口换取二维码图片详情。
        详情请参考 https://api.weixin.qq.com/card/qrcode/create?access_token=TOKEN
        :return: 返回的 JSON 数据包
        """
        return self.post(
            url="https://api.weixin.qq.com/card/qrcode/create",
            params={
                "access_token": self.token,
            },
            data=data
        )

    def card_landingpage_create(self, data):
        """
        通过卡券货架投放卡券
        卡券货架支持开发者通过调用接口生成一个卡券领取H5页面，并获取页面链接，进行卡券投放动作。
        目前卡券货架仅支持非自定义code的卡券，自定义code的卡券需先调用导入code接口将code导入才能正常使用。
        详情请参考 https://api.weixin.qq.com/card/landingpage/create?access_token=TOKEN
        :return: 返回的 JSON 数据包
        """
        return self.post(
            url="https://api.weixin.qq.com/card/landingpage/create",
            params={
                "access_token": self.token,
            },
            data=data
        )

    def card_mpnews_gethtml(self, card_id):
        """
        图文消息群发卡券
        支持开发者调用该接口获取卡券嵌入图文消息的标准格式代码，
        将返回代码填入上传图文素材接口中content字段，即可获取嵌入卡券的图文消息素材。
        特别注意：目前该接口仅支持填入非自定义code的卡券,自定义code的卡券需先进行code导入后调用。
        详情请参考 https://api.weixin.qq.com/card/mpnews/gethtml?access_token=TOKEN
        :return: 返回的 JSON 数据包
        """
        return self.post(
            url="https://api.weixin.qq.com/card/mpnews/gethtml",
            params={
                "access_token": self.token,
            },
            data={
                'card_id': card_id
            }
        )

    def card_code_get(self, card_id, code, check_consume):
        """
        查询Code接口
        查询code接口可以查询当前code是否可以被核销并检查code状态。
        当前可以被定位的状态为正常、已核销、转赠中、已删除、已失效和无效code。
        check_consume:是否校验code核销状态，填入true和false时的code异常状态返回数据不同
        详情请参考 https://api.weixin.qq.com/card/code/get?access_token=TOKEN
        :return: 返回的 JSON 数据包
        """
        return self.post(
            url="https://api.weixin.qq.com/card/code/get",
            params={
                "access_token": self.token,
            },
            data={
                'card_id': card_id,
                'code': code,
                'check_consume': check_consume,
            }
        )

    def card_code_consume(self, card_id, code):
        """
        核销Code接口
        消耗code接口是核销卡券的唯一接口，仅支持核销有效期内的卡券，否则会返回错误码invalid time。
        自定义Code码（use_custom_code为true）的优惠券，在code被核销时，必须调用此接口。
        用于将用户客户端的code状态变更。自定义code的卡券调用接口时，
         post数据中需包含card_id，非自定义code不需上报。
        详情请参考 https://api.weixin.qq.com/card/code/consume?access_token=TOKEN
        :return: 返回的 JSON 数据包
        """
        return self.post(
            url="https://api.weixin.qq.com/card/code/consume",
            params={
                "access_token": self.token,
            },
            data={
                'card_id': card_id,
                'code': code,
            }
        )

    def card_code_decrypt(self, encrypt_code):
        """
        Code解码接口
        code解码接口支持两种场景：
        1.商家获取choos_card_info后，将card_id和encrypt_code字段通过解码接口，获取真实code。
        2.卡券内跳转外链的签名中会对code进行加密处理，通过调用解码接口获取真实code。
        详情请参考 https://api.weixin.qq.com/card/code/decrypt?access_token=TOKEN
        :return: 返回的 JSON 数据包
        """
        return self.post(
            url="https://api.weixin.qq.com/card/code/decrypt",
            params={
                "access_token": self.token,
            },
            data={
                'encrypt_code': encrypt_code,
            }
        )

    def card_user_getcardlist(self, openid):
        """
        获取用户已领取卡券接口
        code解码接口支持两种场景：
        1.用于获取用户卡包里的，属于该appid下的卡券。
        详情请参考 https://api.weixin.qq.com/card/user/getcardlist?access_token=TOKEN
        :return: 返回的 JSON 数据包
        """
        return self.post(
            url="https://api.weixin.qq.com/card/user/getcardlist",
            params={
                "access_token": self.token,
            },
            data={
                'openid': openid,
            }
        )




        ############## 卡券管理 End ##############

    def get_all_private_template(self):
        """
        获取已添加至帐号下所有模板列表
        详情请参考 https://api.weixin.qq.com/cgi-bin/template/get_all_private_template?access_token=ACCESS_TOKEN
        :return: 返回的 JSON 数据包
        """
        return self.get(
            url="https://api.weixin.qq.com/cgi-bin/template/get_all_private_template",
            params={
                "access_token": self.token,
            }
        )

    def api_set_industry(self, industry_id1, industry_id2):
        """
        设置行业可在MP中完成，每月可修改行业1次，账号仅可使用所属行业中相关的模板，
        为方便第三方开发者，提供通过接口调用的方式来修改账号所属行业
        详情请参考 https://api.weixin.qq.com/cgi-bin/template/api_set_industry?access_token=ACCESS_TOKEN
        :return: 返回的 JSON 数据包
        """
        return self.post(
            url="https://api.weixin.qq.com/cgi-bin/template/api_set_industry",
            params={
                "access_token": self.token,
            },
            data={
                'industry_id1': industry_id1,
                'industry_id2': industry_id2,
            }
        )

    def get_industry(self):
        """
        获取帐号设置的行业信息，可在MP中查看行业信息，为方便第三方开发者，提供通过接口调用的方式来获取帐号所设置的行业信息
        详情请参考 https://api.weixin.qq.com/cgi-bin/template/get_industry?access_token=ACCESS_TOKEN
        :return: 返回的 JSON 数据包
        """
        return self.get(
            url="https://api.weixin.qq.com/cgi-bin/template/get_industry",
            params={
                "access_token": self.token,
            }
        )
    def send_message(self, openid, template_id, url, data):
        """
        获取帐号设置的行业信息，可在MP中查看行业信息，为方便第三方开发者，提供通过接口调用的方式来获取帐号所设置的行业信息
        详情请参考 https://api.weixin.qq.com/cgi-bin/message/template/send?access_token=ACCESS_TOKEN
        :return: 返回的 JSON 数据包
        """
        return self.post(
            url="https://api.weixin.qq.com/cgi-bin/message/template/send",
            params={
                "access_token": self.token,
            },
            data={
                'touser': openid,
                'template_id': template_id,
                'url': url,
                "data": data
            }
        )

    def uploadvideo(self, media_id, title, description):
        """
        获取帐号设置的行业信息，可在MP中查看行业信息，为方便第三方开发者，提供通过接口调用的方式来获取帐号所设置的行业信息
        详情请参考  https://file.api.weixin.qq.com/cgi-bin/media/uploadvideo?access_token=ACCESS_TOKEN
        :return: 返回的 JSON 数据包
        """
        return self.post(
            url="https://file.api.weixin.qq.com/cgi-bin/media/uploadvideo",
            params={
                "access_token": self.token,
            },
            data={
                'media_id': media_id,
                'title': title,
                'description': description,
            }
        )

    def getkflist(self):
        """
        获取公众号中所设置的客服基本信息，包括客服工号、客服昵称、客服登录账号。
        详情请参考  https://api.weixin.qq.com/cgi-bin/customservice/getkflist?access_token=ACCESS_TOKEN
        :return: 返回的 JSON 数据包
        """
        return self.get(
            url="https://api.weixin.qq.com/cgi-bin/customservice/getkflist",
            params={
                "access_token": self.token,
            }
        )

    def add_kfaccount(self, kf_account, nickname, password):
        """
        获取公众号中所设置的客服基本信息，包括客服工号、客服昵称、客服登录账号。
        详情请参考  https://api.weixin.qq.com/customservice/kfaccount/add?access_token=ACCESS_TOKEN
        :return: 返回的 JSON 数据包
        """
        return self.post(
            url="https://api.weixin.qq.com/customservice/kfaccount/add",
            params={
                "access_token": self.token,
            },
            data={
                'kf_account': kf_account,
                'nickname': nickname,
                'password': password,
            }
        )

    def update_kfaccount(self, kf_account, nickname, password):
        """
        获取公众号中所设置的客服基本信息，包括客服工号、客服昵称、客服登录账号。
        详情请参考  https://api.weixin.qq.com/customservice/kfaccount/update?access_token=ACCESS_TOKEN
        :return: 返回的 JSON 数据包
        """
        return self.post(
            url="https://api.weixin.qq.com/customservice/kfaccount/update",
            params={
                "access_token": self.token,
            },
            data={
                'kf_account': kf_account,
                'nickname': nickname,
                'password': password,
            }
        )

    def delete_kfaccount(self, kf_account, nickname, password):
        """
        获取公众号中所设置的客服基本信息，包括客服工号、客服昵称、客服登录账号。
        详情请参考  https://api.weixin.qq.com/customservice/kfaccount/del?access_token=ACCESS_TOKEN
        :return: 返回的 JSON 数据包
        """
        return self.post(
            url="https://api.weixin.qq.com/customservice/kfaccount/del",
            params={
                "access_token": self.token,
            },
            data={
                'kf_account': kf_account,
                'nickname': nickname,
                'password': password,
            }
        )

    def headimg_kfaccount(self, kf_account, file_name, media_file):
        """
        获取公众号中所设置的客服基本信息，包括客服工号、客服昵称、客服登录账号。
        详情请参考  http://api.weixin.qq.com/customservice/kfaccount/uploadheadimg?access_token=ACCESS_TOKEN&kf_account=KFACCOUNT
        :return: 返回的 JSON 数据包
        """
        return self.post(
            url="http://api.weixin.qq.com/customservice/kfaccount/uploadheadimg",
            params={
                "access_token": self.token,
                "kf_account": kf_account,
            },
            files={
                'media': (file_name, media_file, 'application/octet-stream'),
            }

        )
