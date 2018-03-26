import datetime
import json
import logging
from pprint import pformat

from channels import Group

logger = logging.getLogger()

# add level 'success'
logging.SUCCESS = 25  # 25 is between WARNING(30) and INFO(20)
logging.addLevelName(logging.SUCCESS, 'SUCCESS')

# stackoverflow told me to use method `_log`,  but the `log` is better
# because, `log` check its level's enablity

logging.success = lambda msg, *args, **kwargs: logging.log(logging.SUCCESS, msg, *args, **kwargs)


# class Singleton(type):
#     _instances = {}
#     def __call__(cls, *args, **kwargs):
#         if cls not in cls._instances:
#             cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
#         return cls._instances[cls]

#
# # @Singleton
# # class PushLogger(metaclass=Singleton):
# class PushLogger():
#     """ Base class for logging messages.
#     """
#
#     # def __init__(self, depth=3):
#     #     """
#     #         Parameters
#     #         ----------
#     #         depth: int, optional
#     #             The depth of objects printed.
#     #     """
#     #     self.depth = depth
#     @classmethod
#     def info(cls, workflow_id, msg):
#         logging.warning("[%s]: %s" % (cls, msg))
#         cls.send_log_message(workflow_id,msg)
#
#     @classmethod
#     def warn(cls, workflow_id, msg):
#         logging.warning("[%s]: %s" % (cls, msg))
#         cls.send_log_message(workflow_id,msg)
#
#     @classmethod
#     def debug(cls,workflow_id,  msg):
#         # XXX: This conflicts with the debug flag used in children class
#         logging.debug("[%s]: %s" % (cls, msg))
#         cls.send_log_message(workflow_id,msg)
#
#     @classmethod
#     def success(cls,workflow_id,  msg):
#         # XXX: This conflicts with the debug flag used in children class
#         logging.success("[%s]: %s" % (cls, msg))
#         cls.send_log_message(workflow_id,msg)
#
#     #
#     # def format(cls, obj, indent=0):
#     #     """ Return the formated representation of the object.
#     #     """
#     #     return pformat(obj, indent=indent, depth=3)
#
#
#     @classmethod
#     def send_log_message(self, workflow_id, msg, widget=None, status=None, **kwargs):
#         Group("editor-{}".format(workflow_id)).send({
#             'text': json.dumps({'type': 'logMessage','status': status, 'widget_name': widget and widget.name,'message': msg})},
#             immediately=True)
#         a=5



class PushHandler(logging.Handler):
    def __init__(self, workflow_id,widget=None):
        self.workflow_id = workflow_id
        self.widget = widget

        super(PushHandler, self).__init__()
    def emit(self, record):
        log_entry = self.format(record)
        return Group("editor-{}".format(self.workflow_id)).send({'text' : log_entry}, immediately=True)
#         json.dumps({'type': 'logMessage','status': "ok", 'widget_name': self.widget and self.widget.name,'message': "hello world"})},


class JsonPushFormatter(logging.Formatter):
    def __init__(self, widget=None):
        self.widget = widget

        super(JsonPushFormatter, self).__init__()

    def format(self, record):
        data = {'message': record.msg,
                'timestamp': datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                'type': 'logMessage',
                'level': record.levelname.lower()}

        if self.widget:
            data['widget'] = self.widget.name

        return json.dumps(data)
