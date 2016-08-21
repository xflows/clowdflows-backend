import traceback

from django.core.urlresolvers import resolve
from django.contrib.auth import authenticate
from django.http import HttpResponse
from rest_framework import viewsets, permissions
from rest_framework.decorators import api_view, permission_classes, detail_route
from django.contrib.auth import logout
from django.db.models import Q
from rest_framework.generics import get_object_or_404
from rest_framework.relations import HyperlinkedRelatedField
from rest_framework.renderers import JSONRenderer

from workflows.serializers import *
from workflows.permissions import IsAdminOrSelf


def login_response(request, user):
    request.user = user
    user = UserSerializer(request.user, context={'request': request})
    return json.dumps({
        'status': 'ok',
        'token': request.user.auth_token.key,
        'user': user.data
    })


@api_view(['POST', ])
@permission_classes((permissions.AllowAny,))
def user_register(request):
    username = request.data.get('username', None)
    password = request.data.get('password', None)
    email = request.data.get('email', None)

    if username and email and password:
        try:
            user = User.objects.create_user(username, password=password, email=email)
        except:
            return HttpResponse(json.dumps({'status': 'error', 'message': 'Username or email already registered'}),
                                content_type="application/json")

        authenticate(username=username, password=password)
        token, _ = Token.objects.get_or_create(user=user)
    else:
        return HttpResponse(json.dumps({'status': 'error', 'message': 'All fields are required'}),
                            content_type="application/json")

    return HttpResponse(login_response(request, user), content_type="application/json")


@api_view(['POST', ])
@permission_classes((permissions.AllowAny,))
def user_login(request):
    username = request.data.get('username', None)
    password = request.data.get('password', None)

    user = authenticate(username=username, password=password)
    if user:
        if user.is_active:
            token, _ = Token.objects.get_or_create(user=user)
            return HttpResponse(login_response(request, user), content_type="application/json")
        else:
            return HttpResponse(json.dumps({'status': 'error', 'message': 'Disabled user'}),
                                content_type="application/json")
    else:
        return HttpResponse(json.dumps({'status': 'error', 'message': 'Incorrect username or password'}),
                            content_type="application/json")


@api_view(['POST', ])
@permission_classes((permissions.IsAuthenticated,))
def user_logout(request):
    request.user.auth_token.delete()
    logout(request)
    return HttpResponse(json.dumps({'status': 'ok'}), content_type="application/json")


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows connections to be viewed or edited.
    """
    permission_classes = (IsAdminOrSelf,)
    serializer_class = UserSerializer
    model = User
    queryset = User.objects.all()


class WorkflowViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows workflows to be viewed or edited.
    """
    permission_classes = (IsAdminOrSelf,)
    model = Workflow
    filter_fields = ('public',)

    def get_serializer_class(self):
        if self.action == 'list':
            return WorkflowListSerializer
        return WorkflowSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_queryset(self):
        workflows = Workflow.objects.filter(Q(user=self.request.user) | Q(public=True))
        return workflows.prefetch_related('widgets', 'widgets__inputs', 'widgets__outputs')

    @detail_route(methods=['post'], url_path='run')
    def run_workflow(self, request, pk=None):
        workflow = get_object_or_404(Workflow, pk=pk)
        try:
            workflow.run()
        except:
            return HttpResponse(json.dumps({'status': 'error', 'message': 'Problem running workflow'}),
                                content_type="application/json")
        return HttpResponse(json.dumps({'status': 'ok'}), content_type="application/json")

    @detail_route(methods=['post'], url_path='stop')
    def stop_workflow(self, request, pk=None):
        workflow = get_object_or_404(Workflow, pk=pk)
        # TODO: stop workflow execution
        return HttpResponse(json.dumps({'status': 'ok'}), content_type="application/json")

    @detail_route(methods=['post'], url_path='subprocess')
    def add_subprocess(self, request, pk=None):
        workflow = get_object_or_404(Workflow, pk=pk)
        subprocess_type = request.POST.get('type', 'normal')
        start_x = request.POST.get('start_x', 0)
        start_y = request.POST.get('start_y', 0)

        subprocess_workflow, subprocess_widget = None, None
        if subprocess_type == 'normal':
            subprocess_workflow, subprocess_widget = workflow.add_normal_subprocess(start_x=start_x, start_y=start_y)
        elif subprocess_type == 'for-loop':
            subprocess_workflow, subprocess_widget = workflow.add_normal_subprocess(start_x=start_x, start_y=start_y)
        elif subprocess_type == 'x-validation':
            subprocess_workflow, subprocess_widget = workflow.add_normal_subprocess(start_x=start_x, start_y=start_y)

        if subprocess_workflow and subprocess_widget:
            return HttpResponse(json.dumps({
                'subprocess_workflow': WorkflowSerializer(subprocess_workflow).data,
                'subprocess_widget': WidgetSerializer(subprocess_widget).data
            }))
        else:
            return HttpResponse(status=400)

    @detail_route(methods=['post'], url_path='reset')
    def reset(self, request, pk=None):
        workflow = get_object_or_404(Workflow, pk=pk)
        for widget in workflow.widgets.filter():
            widget.reset()
        return HttpResponse(json.dumps({'status': 'ok'}), content_type="application/json")


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

    @detail_route(methods=['post'], url_path='reset')
    def reset(self, request, pk=None):
        widget = get_object_or_404(Widget, pk=pk)
        try:
            widget.reset()
        except:
            return HttpResponse(json.dumps({'status': 'error', 'message': 'Problem resetting the widget'}),
                                content_type="application/json")
        return HttpResponse(json.dumps({'status': 'ok'}), content_type="application/json")

    @detail_route(methods=['patch'], url_path='save-parameters')
    def save_parameters(self, request, pk=None):
        widget = get_object_or_404(Widget, pk=pk)
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

    @detail_route(methods=['post'], url_path='run')
    def run(self, request, pk=None):
        w = get_object_or_404(Widget, pk=pk)
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

    @detail_route(methods=['get'], url_path='visualize')
    def visualize(self, request, pk=None):
        w = get_object_or_404(Widget, pk=pk)
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

    @detail_route(methods=['get', 'post'], url_path='interact')
    def interact(self, request, pk=None):
        w = get_object_or_404(Widget, pk=pk)
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


class ConnectionViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows connections to be viewed or edited.
    """
    permission_classes = (IsAdminOrSelf,)
    serializer_class = ConnectionSerializer
    model = Connection

    def get_queryset(self):
        return Connection.objects.filter(Q(workflow__user=self.request.user) | Q(workflow__public=True))

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        i = serializer.validated_data['input']
        o = serializer.validated_data['output']

        deleted = -1
        added = -1
        refresh = -1
        refreshworkflow = -1
        success = False
        mimetype = 'application/javascript'
        message = ""
        previousExists = False
        data = request.data

        if i.widget.workflow == o.widget.workflow:
            if Connection.objects.filter(input=i).exists():
                previousExists = True
                new_c = Connection.objects.get(input=i)
                oldOutput = Output.objects.defer("value").get(pk=new_c.output_id)
                deleted = new_c.id
            else:
                new_c = Connection()
            new_c.input = i
            new_c.output = o
            new_c.workflow = i.widget.workflow
            new_c.save()
            if not checkForCycles(i.widget, i.widget):
                if previousExists:
                    new_c.output = oldOutput
                    new_c.save()
                else:
                    new_c.delete()
                success = False
                message = "Adding this connection would result in a cycle in the workflow."
                data = json.dumps({'message': message, 'status': 'error'})
                return HttpResponse(data, mimetype)
            added = new_c.id
            new_c.input.widget.unfinish()
            if deleted == -1:
                if new_c.input.multi_id != 0:
                    i = new_c.input
                    j = Input()
                    m = i.widget.inputs.aggregate(Max('order'))
                    j.name = i.name
                    j.short_name = i.short_name
                    j.description = i.description
                    j.variable = i.variable
                    j.widget = i.widget
                    j.required = i.required
                    j.parameter = i.parameter
                    j.value = None
                    j.parameter_type = i.parameter_type
                    j.multi_id = i.multi_id
                    j.order = m['order__max'] + 1
                    j.save()
                    refresh = i.widget.id
                    refreshworkflow = i.widget.workflow.id
            success = True
            serializer = ConnectionSerializer(new_c, context={'request': request})
            data = JSONRenderer().render(serializer.data)
            return HttpResponse(data, mimetype)
        else:
            message = "Cannot connect widgets from different workflows."
            data = json.dumps({'message': message, 'status': 'error'})
            return HttpResponse(data, mimetype)

    def destroy(self, request, pk=None):
        #serializer = self.get_serializer(data=request.data)
        #serializer.is_valid(raise_exception=True)
        #c = serializer.validated_data['instance']
        c = get_object_or_404(Connection, pk=pk)
        c.input.widget.unfinish()
        mimetype = 'application/javascript'
        refresh = -1
        refreshworkflow = -1
        already_deleted = False
        if c.input.multi_id != 0:
            # pogledamo kok jih je s tem idjem, ce je vec k en, tega pobrisemo
            inputs = c.input.widget.inputs.filter(multi_id=c.input.multi_id)
            if inputs.count() > 1:
                refresh = c.input.widget.id
                refreshworkflow = c.input.widget.workflow.id
                deleted_order = c.input.order
                c.input.delete()
                already_deleted = True
                for input in inputs.filter(order__gt=deleted_order):
                    input.order -= 1
                    input.save()
        if not already_deleted:
            c.delete()
        data = json.dumps({'refresh': refresh, 'refreshworkflow': refreshworkflow})
        return HttpResponse(data, mimetype)


class InputViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows widget inputs to be viewed or edited.
    """
    permission_classes = (IsAdminOrSelf,)
    serializer_class = InputSerializer
    model = Input

    def get_queryset(self):
        return Input.objects.filter(Q(widget__workflow__user=self.request.user) | Q(widget__workflow__public=True))


class OutputViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows widget outputs to be viewed or edited.
    """
    permission_classes = (IsAdminOrSelf,)
    serializer_class = OutputSerializer
    model = Output

    def get_queryset(self):
        return Output.objects.filter(Q(widget__workflow__user=self.request.user) | Q(widget__workflow__public=True))

    @detail_route(methods=['get'], url_path='value')
    def fetch_value(self, request, pk=None):
        '''
        Route for explicitly fetching output values
        '''
        output = get_object_or_404(Output, pk=pk)
        try:
            json.dumps(output.value)
        except:
            serialized_value = repr(output.value)
        else:
            serialized_value = output.value
        return HttpResponse(json.dumps({'value': serialized_value}), content_type="application/json")


class AbstractOptionViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAdminOrSelf,)
    serializer_class = AbstractOptionSerializer
    model = AbstractOption
    queryset = AbstractOption.objects.all()


class AbstractInputViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAdminOrSelf,)
    serializer_class = AbstractInputSerializer
    model = AbstractInput

    def get_queryset(self):
        return AbstractInput.objects.filter(Q(widget__user=self.request.user) | Q(widget__user__isnull=True))


class AbstractOutputViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAdminOrSelf,)
    serializer_class = AbstractOutputSerializer
    model = AbstractOutput

    def get_queryset(self):
        return AbstractOutput.objects.filter(Q(widget__user=self.request.user) | Q(widget__user__isnull=True))


class AbstractWidgetViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAdminOrSelf,)
    serializer_class = AbstractWidgetSerializer
    model = AbstractWidget

    def get_queryset(self):
        return AbstractWidget.objects.filter(Q(user=self.request.user) | Q(user__isnull=True))


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows the widget library to be read.
    """
    permission_classes = (IsAdminOrSelf,)
    serializer_class = CategorySerializer
    model = Category

    def get_queryset(self):
        return Category.objects.filter(parent__isnull=True)
