import traceback

from django.db.models import Q
from django.http import HttpResponse
from rest_framework import viewsets
from rest_framework.decorators import detail_route

from workflows.permissions import IsAdminOrSelf
from workflows.serializers import *


class WidgetViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows widgets to be viewed or edited.
    """
    permission_classes = (IsAdminOrSelf,)
    serializer_class = WidgetSerializer
    model = Widget
    filter_fields = ('workflow',)

    def get_serializer_class(self):
        return WidgetSerializer

    def get_queryset(self):
        return Widget.objects.filter(Q(workflow__user=self.request.user) | Q(workflow__public=True)).prefetch_related(
            'inputs', 'outputs')

    @detail_route(methods=['post'], url_path='reset', permission_classes=[IsAdminOrSelf,])
    def reset(self, request, pk=None):
        widget = self.get_object()
        try:
            widget.reset()
            descendants = widget.reset_descendants()
            for widget_pk in descendants:
                Widget.objects.get(pk=widget_pk).reset()
        except:
            return HttpResponse(json.dumps({'status': 'error', 'message': 'Problem resetting the widget'}),
                                content_type="application/json")
        return HttpResponse(json.dumps({'status': 'ok'}), content_type="application/json")

    @detail_route(methods=['patch'], url_path='save-parameters', permission_classes=[IsAdminOrSelf,])
    def save_parameters(self, request, pk=None):
        widget = self.get_object()
        try:
            parameter_data = request.data
            for parameter in parameter_data:
                inputs = widget.inputs.filter(id=parameter['id'])
                if inputs.count() != 1:
                    return HttpResponse(status=400)
                input = inputs[0]
                input.value = parameter['value']
                input.save()
            widget.unfinish()
        except:
            return HttpResponse(json.dumps({'status': 'error', 'message': 'Problem saving parameters'}),
                                content_type="application/json")
        return HttpResponse(json.dumps({'status': 'ok'}), content_type="application/json")

    @detail_route(methods=['post'], url_path='run', permission_classes=[IsAdminOrSelf,])
    def run(self, request, pk=None):
        w = self.get_object()
        data = ''
        try:
            # find all required inputs
            multi_satisfied = {}
            for inp in w.inputs.filter(required=True, parameter=False):
                if inp.connections.count() == 0:
                    if inp.multi_id == 0:
                        raise Exception(
                            "The input '{}' must have something connected to it in order to run.".format(str(inp)))
                    else:
                        multi_satisfied[inp.multi_id] = (str(inp), multi_satisfied.get(inp.multi_id, False))
                elif inp.multi_id != 0:
                    multi_satisfied[inp.multi_id] = (str(inp), True)
            for mid in multi_satisfied.keys():
                if multi_satisfied[mid][1] == False:
                    raise Exception("The input '{}' must have something connected to it in order to run.".format(
                        multi_satisfied[mid][0]))
            if w.type == 'for_input' or w.type == 'for_output':
                raise Exception("You can't run for loops like this. Please run the containing widget.")
            output_dict = w.run(False)
            if not w.abstract_widget is None:
                if w.abstract_widget.interactive:
                    w.interaction_waiting = True
                    w.save()
                    data = json.dumps(
                        {'status': 'interactive', 'message': 'Widget \'{}\' needs your attention.'.format(w.name),
                         'widget_id': w.id})
                elif w.abstract_widget.visualization_view != '':
                    data = json.dumps(
                        {'status': 'visualize', 'message': 'Visualizing widget \'{}\'.'.format(w.name),
                         'widget_id': w.id})
                else:
                    data = json.dumps(
                        {'status': 'ok', 'message': 'Widget \'{}\' executed successfully.'.format(w.name)})
            else:
                data = json.dumps({'status': 'ok', 'message': 'Widget \'{}\' executed successfully.'.format(w.name)})
        except Exception, e:
            mimetype = 'application/javascript'
            w.error = True
            w.running = False
            w.finished = False
            w.save()

            # raise
            for o in w.outputs.all():
                o.value = None
                o.save()
            data = json.dumps({'status': 'error',
                               'message': 'Error occurred when trying to execute widget \'{}\': {}'.format(w.name,
                                                                                                           str(e))})
        return HttpResponse(data, 'application/javascript')

    @detail_route(methods=['get'], url_path='visualize', permission_classes=[IsAdminOrSelf,])
    def visualize(self, request, pk=None):
        w = self.get_object()
        if w.is_visualization():
            output_dict = {}
            for o in w.outputs.all():
                output_dict[o.variable] = o.value
            input_dict = {}
            for i in w.inputs.all():
                if not i.parameter:
                    if i.connections.count() > 0:
                        i.value = i.connections.all()[0].output.value
                        i.save()
                    else:
                        i.value = None
                        i.save()
                if i.multi_id == 0:
                    input_dict[i.variable] = i.value
                else:
                    if not i.variable in input_dict:
                        input_dict[i.variable] = []
                    if not i.value == None:
                        input_dict[i.variable].append(i.value)
            view_to_call = getattr(workflows.visualization_views, w.abstract_widget.visualization_view)
            return view_to_call(request, input_dict, output_dict, w)
        else:
            data = json.dumps({'status': 'error', 'message': 'Widget {} is not a visualization widget.'.format(w.name)})
            return HttpResponse(data, 'application/javascript')

    @detail_route(methods=['get', 'post'], url_path='interact', permission_classes=[IsAdminOrSelf,])
    def interact(self, request, pk=None):
        w = self.get_object()
        if request.method == 'GET':
            input_dict = {}
            output_dict = {}
            for i in w.inputs.all():
                if not i.parameter:
                    if i.connections.count() > 0:
                        i.value = i.connections.all()[0].output.value
                        i.save()
                    else:
                        i.value = None
                        i.save()
                if i.multi_id == 0:
                    input_dict[i.variable] = i.value
                else:
                    if not i.variable in input_dict:
                        input_dict[i.variable] = []
                    if not i.value == None:
                        input_dict[i.variable].append(i.value)
            for o in w.outputs.all():
                output_dict[o.variable] = o.value
            view_to_call = getattr(workflows.interaction_views, w.abstract_widget.interaction_view)
            return view_to_call(request, input_dict, output_dict, w)
        else:  # POST
            try:
                data = dict(request.POST) if request.POST else request.data
                output_dict = w.run_post(data)
                #w.interaction_waiting = False
                #w.save()
                mimetype = 'application/javascript'
                if w.abstract_widget.visualization_view != '':
                    data = json.dumps(
                        {'status': 'visualize', 'message': 'Visualizing widget {}.'.format(w.name), 'widget_id': w.id})
                else:
                    data = json.dumps(
                        {'status': 'ok', 'message': 'Widget {} executed successfully.'.format(w.name),
                         'widget_id': w.id})
            except Exception, e:
                mimetype = 'application/javascript'
                w.error = True
                w.running = False
                w.finished = False
                w.interaction_waiting = False
                w.interaction_finished = False
                w.save()
                print traceback.format_exc(e)
                # raise
                for o in w.outputs.all():
                    o.value = None
                    o.save()
                data = json.dumps({'status': 'error',
                                   'message': 'Error occurred when trying to execute widget \'{}\': {}'.format(w.name,
                                                                                                               str(e))})
            return HttpResponse(data, mimetype)

    @detail_route(methods=['post'], url_path='copy', permission_classes=[IsAdminOrSelf, ])
    def copy(self, request, pk=None):
        orig_w = self.get_object()
        if orig_w.type == 'regular':
            workflow = orig_w.workflow
            w = Widget()
            w.workflow = workflow
            w.x = orig_w.x + 50
            y = orig_w.y + 50
            while workflow.widgets.filter(y=y, x=w.x).count() > 0:
                y += 100
            w.y = y
            w.name = orig_w.name + ' (copy)'
            w.abstract_widget = orig_w.abstract_widget
            w.type = orig_w.type
            w.save()
            for i in orig_w.inputs.all():
                j = Input()
                j.name = i.name
                j.short_name = i.short_name
                j.description = i.description
                j.variable = i.variable
                j.widget = w
                j.required = i.required
                j.parameter = i.parameter
                j.parameter_type = i.parameter_type
                j.value = i.value
                j.multi_id = i.multi_id
                j.save()
                for k in i.options.all():
                    o = Option()
                    o.name = k.name
                    o.value = k.value
                    o.input = j
                    o.save()
            for i in orig_w.outputs.all():
                j = Output()
                j.name = i.name
                j.short_name = i.short_name
                j.description = i.description
                j.variable = i.variable
                j.widget = w
                j.save()
            widget_data = WidgetSerializer(w, context={'request': request}).data
            return HttpResponse(json.dumps(widget_data), 'application/json')

        elif orig_w.type == 'subprocess':
            workflow = orig_w.workflow
            widget_conversion = {}
            input_conversion = {}
            output_conversion = {}
            w = Widget()
            w.workflow = workflow
            w.x = orig_w.x + 50
            y = orig_w.y + 50
            while workflow.widgets.filter(y=y, x=w.x).count() > 0:
                y += 100
            w.y = y
            w.name = orig_w.name + ' (copy)'
            w.abstract_widget = orig_w.abstract_widget
            w.type = orig_w.type
            w.save()
            widget_conversion[orig_w.pk] = w.pk
            for i in orig_w.inputs.all():
                j = Input()
                j.name = i.name
                j.short_name = i.short_name
                j.description = i.description
                j.variable = i.variable
                j.widget = w
                j.required = i.required
                j.parameter = i.parameter
                j.parameter_type = i.parameter_type
                j.value = i.value
                j.multi_id = i.multi_id
                j.save()
                input_conversion[i.pk] = j.pk
                for k in i.options.all():
                    o = Option()
                    o.name = k.name
                    o.value = k.value
                    o.input = j
                    o.save()
            for i in orig_w.outputs.all():
                j = Output()
                j.name = i.name
                j.short_name = i.short_name
                j.description = i.description
                j.variable = i.variable
                j.widget = w
                j.save()
                output_conversion[i.pk] = j.pk
            workflows.models.copy_workflow(orig_w.workflow_link, request.user, widget_conversion, input_conversion,
                                           output_conversion, w)
            widget_data = WidgetSerializer(w, context={'request': request}).data
            return HttpResponse(json.dumps(widget_data), 'application/json')
        else:
            return HttpResponse(status=400)

    def destroy(self, request, pk=None, **kwargs):
        widget = self.get_object()
        widget.delete()
        if widget.is_special_subprocess_type():
            subprocess_widget = widget.workflow.widget
            subprocess_widget.update_input_output_order()
        data = json.dumps({'status': 'ok'})
        return HttpResponse(data, 'application/json')
