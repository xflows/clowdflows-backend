import traceback
from django.db.models import Q, Max
from django.http import HttpResponse
from rest_framework import viewsets
from rest_framework.decorators import detail_route, list_route

from workflows.api.permissions import IsAdminOrSelf
from workflows.api.serializers import *
from workflows.engine import WorkflowRunner
from workflows.forms import ImportForm


def next_order(inputs_or_outputs):
    m = inputs_or_outputs.aggregate(Max('order'))
    return m['order__max'] + 1 if m['order__max'] else 1


class WorkflowViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows workflows to be viewed or edited.
    """
    permission_classes = (IsAdminOrSelf,)
    model = Workflow
    filter_fields = ('public',)

    def get_serializer_class(self):
        preview = self.request.GET.get('preview', '0') == '1'
        if preview:
            return WorkflowPreviewSerializer
        if self.action == 'list':
            return WorkflowListSerializer
        return WorkflowSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_queryset(self):
        workflows = Workflow.objects.prefetch_related('widget', 'user')
        preview = self.request.GET.get('preview', '0') == '1'
        if self.action == 'list' or preview:
            user = self.request.user
            user_only = self.request.GET.get('user', '0') == '1'

            if user_only:
                filters = Q(user=user)
            else:
                filters = Q(user=user) | Q(public=True)
            workflows = workflows.filter(filters).prefetch_related('connections')
            if preview:
                workflows = workflows.prefetch_related("widgets", "connections__output", "connections__input") \
                    .defer("connections__output__value", "connections__input__value")
        elif self.action == "retrieve":
            workflows = Workflow.objects.prefetch_related('widget', 'user') \
                .prefetch_related("connections", "connections__output", "connections__input") \
                .defer("connections__output__value", "connections__input__value") \
                .prefetch_related(
                'widget',
                'widgets',
                'widgets__inputs', 'widgets__inputs',
                'widgets__inputs__options',
                'widgets__inputs__inner_output',  # TODO check why
                'widgets__outputs',  # 'outputs__inner_input',
                'widgets__workflow_link',
                'widgets__abstract_widget', 'widgets__abstract_widget__inputs', 'widgets__abstract_widget__outputs') \
                .defer("widgets__outputs__value", "widgets__inputs__value")


            # .prefetch_related(
            #     Prefetch('widgets',
            #         queryset=Widget.objects.prefetch_related(
            #         'inputs',
            #         'inputs__options',
            #         'inputs__inner_output', #why why oh why check
            #         'outputs', #'outputs__inner_input',
            #         'workflow'
            #         'workflow_link',
            #         'abstract_widget')
            #         .defer("outputs__value", "inputs__value")
            #     )
            # )
        return workflows

    @detail_route(methods=['post'], url_path='run')
    def run(self, request, pk=None):
        workflow = self.get_object()
        try:
            WorkflowRunner(workflow).run()
        except:
            return HttpResponse(json.dumps({'status': 'error', 'message': 'Problem running workflow'}),
                                content_type="application/json")
        return HttpResponse(json.dumps({'status': 'ok'}), content_type="application/json")

    @detail_route(methods=['post'], url_path='stop')
    def stop(self, request, pk=None):
        workflow = self.get_object()
        # TODO: stop workflow execution
        return HttpResponse(json.dumps({'status': 'ok'}), content_type="application/json")

    @detail_route(methods=['post'], url_path='subprocess')
    def add_subprocess(self, request, pk=None):
        workflow = self.get_object()
        start_x = request.POST.get('start_x', 0)
        start_y = request.POST.get('start_y', 0)

        subprocess_workflow, subprocess_widget = workflow.add_normal_subprocess(start_x=start_x, start_y=start_y)

        if subprocess_workflow and subprocess_widget:
            widget_data = WidgetSerializer(subprocess_widget, context={'request': request}).data
            return HttpResponse(json.dumps(widget_data), content_type="application/json")
        else:
            return HttpResponse(status=400)

    @detail_route(methods=['post'], url_path='subprocess-input')
    def add_subprocess_input(self, request, pk=None):
        workflow = self.get_object()
        if workflow.widget == None:
            message = 'The input widget can only be put in a subprocess.'
            data = json.dumps({'message': message, 'status': 'error'})
            return HttpResponse(data, 'application/json')
        else:
            widget = Widget()
            widget.workflow = workflow
            widget.x = 50
            y = 50
            while workflow.widgets.filter(y=y, x=widget.x).count() > 0:
                y = y + 100
            widget.y = y
            widget.name = 'Input'
            widget.type = 'input'
            widget.save()
            variable_name = 'Input' + str(widget.pk)
            output = Output()
            output.name = 'Input'
            output.short_name = 'inp'
            output.variable = variable_name
            output.widget = widget
            output.save()
            input = Input()
            input.widget = workflow.widget
            input.name = 'Input'
            input.short_name = 'inp'
            input.variable = variable_name
            input.inner_output = output
            input.order = next_order(workflow.widget.inputs)
            input.save()
            output.outer_input = input
            output.save()
            widget.defered_outputs = widget.outputs.defer("value").all()
            widget.defered_inputs = widget.inputs.defer("value").all()
            widget_data = WidgetSerializer(widget, context={'request': request}).data
            return HttpResponse(json.dumps(widget_data), 'application/json')

    @detail_route(methods=['post'], url_path='subprocess-output')
    def add_subprocess_output(self, request, pk=None):
        workflow = self.get_object()
        if workflow.widget == None:
            message = 'The output widget can only be put in a subprocess.'
            data = json.dumps({'message': message, 'status': 'error'})
            return HttpResponse(data, 'application/json')
        else:
            widget = Widget()
            widget.workflow = workflow
            widget.x = 50
            y = 50
            while workflow.widgets.filter(y=y, x=widget.x).count() > 0:
                y = y + 100
            widget.y = y
            widget.name = 'Output'
            widget.type = 'output'
            widget.save()
            variable_name = 'Output' + str(widget.pk)
            input = Input()
            input.name = 'Output'
            input.short_name = 'out'
            input.variable = variable_name
            input.widget = widget
            input.save()
            output = Output()
            output.widget = workflow.widget
            output.name = 'Output'
            output.short_name = 'out'
            output.variable = variable_name
            output.inner_input = input
            output.order = next_order(workflow.widget.outputs)
            output.save()
            input.outer_output = output
            input.save()
            widget.defered_outputs = widget.outputs.defer("value").all()
            widget.defered_inputs = widget.inputs.defer("value").all()
            widget_data = WidgetSerializer(widget, context={'request': request}).data
            return HttpResponse(json.dumps(widget_data), 'application/json')

    @detail_route(methods=['post'], url_path='subprocess-forloop')
    def add_subprocess_forloop(self, request, pk=None):
        workflow = self.get_object()
        if workflow.widget == None:
            message = 'The for widgets can only be put in a subprocess.'
            data = json.dumps({'message': message, 'status': 'error'})
            return HttpResponse(data, 'application/json')
        elif workflow.widgets.filter(type='for_input').count() > 0:
            message = 'This subprocess already has a for loop. Try deleting it and adding it again.'
            data = json.dumps({'message': message, 'status': 'error'})
            return HttpResponse(data, 'application/json')
        else:
            for_input = Widget()
            for_input.workflow = workflow
            for_input.x = 50
            y = 50
            while workflow.widgets.filter(y=y, x=for_input.x).count() > 0:
                y = y + 100
            for_input.y = y
            for_input.name = 'For input'
            for_input.type = 'for_input'
            for_input.save()
            output = Output()
            output.name = 'For input'  # subproces inner input
            output.short_name = 'for'
            output.variable = 'For'
            output.widget = for_input
            output.save()
            input = Input()
            input.widget = workflow.widget
            input.name = 'For input'  # subproces input
            input.short_name = 'for'
            input.variable = 'For'
            input.inner_output = output
            input.order = next_order(workflow.widget.inputs)
            input.save()
            output.outer_input = input
            output.save()

            widget = Widget()
            widget.workflow = workflow
            widget.x = 200
            widget.y = 50
            widget.name = 'For output'
            widget.type = 'for_output'
            widget.save()
            input = Input()
            input.name = 'For output'
            input.short_name = 'for'
            input.variable = 'For'
            input.widget = widget
            input.save()
            output = Output()
            output.widget = workflow.widget
            output.name = 'For output'
            output.short_name = 'for'
            output.variable = 'For'
            output.order = next_order(workflow.widget.outputs)
            output.inner_input = input
            output.save()
            input.outer_output = output
            input.save()
            for_input.defered_outputs = for_input.outputs.defer("value").all()
            for_input.defered_inputs = for_input.inputs.defer("value").all()
            widget.defered_outputs = widget.outputs.defer("value").all()
            widget.defered_inputs = widget.inputs.defer("value").all()
            widgets = [for_input, widget]
            widget_data = [WidgetSerializer(w, context={'request': request}).data for w in widgets]
            return HttpResponse(json.dumps(widget_data), 'application/json')

    @detail_route(methods=['post'], url_path='subprocess-xvalidation')
    def add_subprocess_xvalidation(self, request, pk=None):
        workflow = self.get_object()
        if workflow.widget == None:
            message = 'The cross validation widgets can only be put in a subprocess.'
            data = json.dumps({'message': message, 'status': 'error'})
            return HttpResponse(data, 'application/json')
        elif workflow.widgets.filter(type='for_input').count() > 0:
            message = 'This subprocess already has a for loop. Try deleting it and adding it again.'
            data = json.dumps({'message': message, 'status': 'error'})
            return HttpResponse(data, 'application/json')
        elif workflow.widgets.filter(type='cv_input').count() > 0:
            message = 'This subprocess already has cross validation. Try deleting it and adding it again.'
            data = json.dumps({'message': message, 'status': 'error'})
            return HttpResponse(data, 'application/json')
        else:
            # input: data
            cv_input_data = Widget()
            cv_input_data.workflow = workflow
            cv_input_data.x = 50
            y = 50
            while workflow.widgets.filter(y=y, x=cv_input_data.x).count() > 0:
                y = y + 100
            cv_input_data.y = y
            cv_input_data.name = 'cv input'
            cv_input_data.type = 'cv_input'
            cv_input_data.save()

            output = Output()
            output.name = 'cv input data'
            output.short_name = 'trn'  # subproces inner input
            output.variable = 'TRAIN'
            output.order = 1
            output.widget = cv_input_data
            output.save()
            input = Input()
            input.widget = workflow.widget
            input.name = 'cv input data'
            input.short_name = 'dat'  # subproces input
            input.variable = 'CVD'
            input.inner_output = output
            input.order = next_order(workflow.widget.inputs)
            input.save()
            output.outer_input = input
            output.save()

            output = Output()
            output.name = 'cv input data'
            output.short_name = 'tst'  # subproces inner input
            output.variable = 'TEST'
            output.order = 2
            output.widget = cv_input_data
            output.save()
            input = Input()
            input.widget = workflow.widget
            input.name = 'cv input folds'
            input.short_name = 'cvf'
            input.variable = 'CVF'
            input.inner_output = output
            input.order = next_order(workflow.widget.inputs)
            input.save()
            output.outer_input = input
            output.save()

            output = Output()
            output.name = 'cv input data'
            output.short_name = 'sed'  # subproces inner input
            output.variable = 'SEED'
            output.order = 3
            output.widget = cv_input_data
            output.save()
            input = Input()
            input.widget = workflow.widget
            input.name = 'cv input seed'
            input.short_name = 'sed'
            input.variable = 'CVS'
            input.order = next_order(workflow.widget.inputs)
            input.inner_output = output
            input.save()
            output.outer_input = input
            output.save()

            # output
            widget = Widget()
            widget.workflow = workflow
            widget.x = 200
            widget.y = 50
            widget.name = 'cv output'
            widget.type = 'cv_output'
            widget.save()
            input = Input()
            input.name = 'cv output'
            input.short_name = 'res'
            input.variable = 'Res'
            input.widget = widget
            input.save()
            output = Output()
            output.widget = workflow.widget
            output.name = 'cv output'
            output.short_name = 'res'
            output.variable = 'Res'
            output.order = next_order(workflow.widget.outputs)
            output.inner_input = input
            output.save()
            input.outer_output = output
            input.save()
            cv_input_data.defered_outputs = cv_input_data.outputs.defer("value").all()
            cv_input_data.defered_inputs = cv_input_data.inputs.defer("value").all()
            widget.defered_outputs = widget.outputs.defer("value").all()
            widget.defered_inputs = widget.inputs.defer("value").all()
            widgets = [cv_input_data, widget]
            widget_data = [WidgetSerializer(w, context={'request': request}).data for w in widgets]
            return HttpResponse(json.dumps(widget_data), 'application/json')

    @detail_route(methods=['post'], url_path='reset')
    def reset(self, request, pk=None):
        workflow = self.get_object()
        for widget in workflow.widgets.filter():
            widget.reset()
        return HttpResponse(json.dumps({'status': 'ok'}), content_type="application/json")

    @detail_route(methods=['get'], url_path='export')
    def export_workflow(self, request, pk=None):
        workflow = self.get_object()
        workflow_json = {}
        try:
            workflow_json = workflow.export()
        except:
            return HttpResponse(json.dumps({'status': 'error', 'message': 'Problem exporting workflow'}),
                                content_type="application/json")
        return HttpResponse(json.dumps({'status': 'ok', 'workflow_json': workflow_json}),
                            content_type="application/json")

    @list_route(methods=['post'], url_path='import')
    def import_workflow(self, request, pk=None):
        new_workflow_id = None
        successfully_imported = False
        form = ImportForm(request.data)
        message = ''
        try:
            if form.is_valid():
                new_workflow = Workflow()
                new_workflow.user = request.user
                new_workflow.import_from_json(json.loads(form.cleaned_data['data']), {}, {})
                new_workflow_id = new_workflow.id
                successfully_imported = True
        except Exception as e:
            print(traceback.format_exc(e))
            message = e.message
        if not successfully_imported:
            if not form.is_valid():
                message = '\n'.join([err[1][0] for err in form.errors.items()])
            return HttpResponse(json.dumps({'status': 'error', 'message': message}),
                                content_type="application/json")
        return HttpResponse(json.dumps({'status': 'ok', 'new_workflow_id': new_workflow_id}),
                            content_type="application/json")

    @detail_route(methods=['post'], url_path='start-streaming')
    def start_stream(self, request, pk=None):
        w = self.get_object()
        if w.can_be_streaming():
            s = Stream(workflow=w, user=request.user, active=True)
            s.save()
        else:
            message = 'You can only stream workflows containing streaming widgets.'
            data = json.dumps({'message': message, 'status': 'error'})
            return HttpResponse(data, 'application/json')
        return HttpResponse(json.dumps({'status': 'ok', 'stream_id': s.pk}), content_type="application/json")
