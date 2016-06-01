# -*- coding: utf-8 -*-
##############################################################################
#  AUTHOR: SongHb
#  EMAIL: songhaibin1990@gmail.com
#  VERSION : 1.0   NEW  2015-11-16 22:35:50
#  UPDATE : NONE
#  Copyright (C) 2015 SongHb All Rights Reserved
##############################################################################
from xml.etree import ElementTree
import logging

from messages import MESSAGE_TYPES, UnknownMessage
from ..tools.utils import to_text


_logger = logging.getLogger(__name__)


def parse_user_msg(xml):
    """
    Parse xml from wechat server and return an Message
    :param xml: raw xml from wechat server.
    :return: an Message object
    """
    if not xml:
        return
    _logger.info(xml.decode('utf-8'))

    wechat_message = dict((child.tag, to_text(child.text))
                          for child in ElementTree.fromstring(xml))
    wechat_message["raw"] = xml
    wechat_message["type"] = wechat_message.pop("MsgType").lower()

    if wechat_message["type"] == 'event':
        wechat_message["event"] = wechat_message.pop("Event").lower()
        message_type = MESSAGE_TYPES.get(wechat_message["event"], UnknownMessage)
    else:
        message_type = MESSAGE_TYPES.get(wechat_message["type"], UnknownMessage)

    return message_type(wechat_message)
