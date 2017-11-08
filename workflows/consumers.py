from urllib.parse import parse_qs
from channels import Group
from channels.sessions import channel_session


@channel_session
def ws_add(message):
    message.reply_channel.send({"accept": True})
    qs = parse_qs(message['query_string'])
    workflow_pk = qs['workflow_pk'][0]
    message.channel_session['workflow_pk'] = workflow_pk
    Group("workflow-{}".format(workflow_pk)).add(message.reply_channel)


@channel_session
def ws_disconnect(message):
    workflow_pk = message.channel_session['workflow_pk']
    Group("workflow-{}".format(workflow_pk)).discard(message.reply_channel)
