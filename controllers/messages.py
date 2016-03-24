# -*- coding: utf-8 -*-

MESSAGE_TYPES = {}


def handle_for_type(type):
    def register(f):
        MESSAGE_TYPES[type] = f
        return f
    return register


class WeChatMessage(object):
    def __init__(self, message):
        self.id = int(message.pop("MsgId", 0))
        self.target = message.pop("ToUserName", None)
        self.source = message.pop('FromUserName', None)
        self.time = int(message.get('CreateTime', 0))
        self.__dict__.update(message)


@handle_for_type("text")
class TextMessage(WeChatMessage):
    def __init__(self, message):
        self.content = message.pop("Content")
        super(TextMessage, self).__init__(message)


@handle_for_type("image")
class ImageMessage(WeChatMessage):
    def __init__(self, message):
        self.img = message.pop("PicUrl")
        self.mediaid = message.pop("MediaId")
        super(ImageMessage, self).__init__(message)


@handle_for_type("location")
class LocationMessage(WeChatMessage):
    def __init__(self, message):
        self.latitude = float(message.pop("Latitude"))
        self.longitude = float(message.pop("Longitude"))
        self.precision = float(message.pop("Precision"))
        super(LocationMessage, self).__init__(message)

@handle_for_type("subscribe")
class SubscribeMessage(WeChatMessage):
    def __init__(self, message):
        if "Ticket" in message:
            self.eventkey = message.pop("EventKey")
            self.ticket = message.pop("Ticket")
        super(SubscribeMessage, self).__init__(message)

@handle_for_type("scan")
class ScanMessage(WeChatMessage):
    def __init__(self, message):
        self.eventkey = message.pop("EventKey")
        self.ticket = message.pop("Ticket")
        super(ScanMessage, self).__init__(message)


@handle_for_type("click")
class ClickMessage(WeChatMessage):
    def __init__(self, message):
        self.eventkey = message.pop("EventKey")
        super(ClickMessage, self).__init__(message)


@handle_for_type("view")
class ViewMessage(WeChatMessage):
    def __init__(self, message):
        self.eventkey = message.pop("EventKey")
        super(ViewMessage, self).__init__(message)


@handle_for_type("link")
class LinkMessage(WeChatMessage):
    def __init__(self, message):
        self.title = message.pop('Title')
        self.description = message.pop('Description')
        self.url = message.pop('Url')
        super(LinkMessage, self).__init__(message)


# @handle_for_type("event")
# class EventMessage(WeChatMessage):
#     def __init__(self, message):
#         message.pop("type")
#         self.type = message.pop("Event").lower()
#         if self.type == "click":
#             self.key = message.pop('EventKey')
#         if self.type == "view":
#             self.key = message.pop('EventKey')
#         elif self.type == "location":
#             self.latitude = float(message.pop("Latitude"))
#             self.longitude = float(message.pop("Longitude"))
#             self.precision = float(message.pop("Precision"))
#         elif self.type == "scan":
#             self.eventkey = message.pop("EventKey")
#             self.ticket = message.pop("Ticket")
#         elif self.type == "subscribe":
#             if "Ticket" in message:
#                 self.eventkey = message.pop("EventKey")
#                 self.ticket = message.pop("Ticket")
#         super(EventMessage, self).__init__(message)


@handle_for_type("voice")
class VoiceMessage(WeChatMessage):
    def __init__(self, message):
        self.media_id = message.pop('MediaId')
        self.format = message.pop('Format')
        #         self.recognition = message.pop('Recognition')//开通语音识别后才会有
        super(VoiceMessage, self).__init__(message)


@handle_for_type("video")
class VideoMessage(WeChatMessage):
    def __init__(self, message):
        self.media_id = message.pop('MediaId')
        self.thumb_media_id = message.pop('ThumbMediaId')
        super(VideoMessage, self).__init__(message)


@handle_for_type("shortvideo")
class ShortVideoideoMessage(WeChatMessage):
    def __init__(self, message):
        self.media_id = message.pop('MediaId')
        self.thumb_media_id = message.pop('ThumbMediaId')
        super(ShortVideoideoMessage, self).__init__(message)


class UnknownMessage(WeChatMessage):
    def __init__(self, message):
        self.type = 'unknown'
        super(UnknownMessage, self).__init__(message)
