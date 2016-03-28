# -*- coding: utf-8 -*-
##############################################################################
#  COMPANY: BONN
#  AUTHOR: KIWI
#  EMAIL: arborous@gmail.com
#  VERSION : 1.0   NEW  2015/12/12
#  UPDATE : NONE
#  Copyright (C) 2011-2016 www.mychinavip.com All Rights Reserved
##############################################################################

{
    'name': "微信",
    'author': '上海波恩网络科技服务有限公司',  # 作者
    'summary': 'BORN',
    'description': """
         微信管理
     """,
    'category': 'BORN',
    'sequence': 8,
    'website': 'http://www.mychinavip.com',
    'images': [],
    'depends': ['born_odoo'],
    'demo': [],
    'init_xml': [],
    'data': [
        'tl_weixin.xml',
        'tl_weixin_dev.xml',
        'data/industry_data.xml',
        'data/weixin_region_data.xml',
        # 'data/color_data.xml',
        # 'security/groups.xml',
        'open_weixin/open_weixin.xml',

    ],
    'auto_install': False,
    'application': True,
    'installable': True,
}