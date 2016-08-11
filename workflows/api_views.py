from django.contrib.auth import authenticate
from django.http import HttpResponse
from rest_framework import viewsets, permissions
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes, detail_route
from django.contrib.auth import logout
from django.db.models import Q
from rest_framework.generics import get_object_or_404

from workflows.serializers import *
from workflows.permissions import IsAdminOrSelf


def login_response(request, user):
    request.user = user
    user = UserSerializer(request.user, context={'request': request})
    return json.dumps({
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
            return HttpResponse(json.dumps({'error': 'Username or email already registered'}),
                                content_type="application/json", status=400)

        authenticate(username=username, password=password)
        token, _ = Token.objects.get_or_create(user=user)
    else:
        return HttpResponse(json.dumps({'error': 'All fields are required'}), content_type="application/json",
                            status=400)

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
            return HttpResponse(json.dumps({'error': 'Disabled user'}), content_type="application/json",
                                status=400)
    else:
        return HttpResponse(json.dumps({'error': 'Incorrect username or password'}), content_type="application/json",
                            status=400)


@api_view(['POST', ])
@permission_classes((permissions.IsAuthenticated,))
def user_logout(request):
    request.user.auth_token.delete()
    logout(request)
    return HttpResponse(json.dumps({'status': 'success'}), content_type="application/json")


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
        workflow.run()
        return HttpResponse(json.dumps({'status': 'success'}), content_type="application/json")

    @detail_route(methods=['post'], url_path='stop')
    def stop_workflow(self, request, pk=None):
        workflow = get_object_or_404(Workflow, pk=pk)
        # TODO: stop workflow execution
        return HttpResponse(json.dumps({'status': 'success'}), content_type="application/json")

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
        return HttpResponse(json.dumps({'status': 'success'}), content_type="application/json")


class WidgetViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows widgets to be viewed or edited.
    """
    permission_classes = (IsAdminOrSelf,)
    serializer_class = WidgetSerializer
    model = Widget
    filter_fields = ('workflow',)

    def get_serializer_class(self):
        if self.action == 'list':
            return WidgetListSerializer
        return WidgetSerializer

    def get_queryset(self):
        return Widget.objects.filter(Q(workflow__user=self.request.user) | Q(workflow__public=True)).prefetch_related(
            'inputs', 'outputs')

    @detail_route(methods=['post'], url_path='reset')
    def reset(self, request, pk=None):
        widget = get_object_or_404(Widget, pk=pk)
        widget.reset()
        return HttpResponse(json.dumps({'status': 'success'}), content_type="application/json")

    @detail_route(methods=['patch'], url_path='save-parameters')
    def save_parameters(self, request, pk=None):
        widget = get_object_or_404(Widget, pk=pk)
        parameter_data = request.data
        for parameter in parameter_data:
            inputs = widget.inputs.filter(id=parameter['id'])
            if inputs.count() != 1:
                return HttpResponse(status=400)
            input = inputs[0]
            input.value = parameter['value']
            input.save()
        widget.unfinish()
        return HttpResponse(json.dumps({'status': 'success'}), content_type="application/json")


class ConnectionViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows connections to be viewed or edited.
    """
    permission_classes = (IsAdminOrSelf,)
    serializer_class = ConnectionSerializer
    model = Connection

    def get_queryset(self):
        return Connection.objects.filter(Q(workflow__user=self.request.user) | Q(workflow__public=True))


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
