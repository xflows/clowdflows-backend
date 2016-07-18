from django.contrib.auth import authenticate
from django.http import HttpResponse
from rest_framework import viewsets, permissions
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes, detail_route
from django.contrib.auth import logout
from rest_framework.generics import get_object_or_404

from workflows.serializers import *
from workflows.permissions import IsAdminOrSelf


def login_response(request, user):
    request.user = user
    user = UserSerializer(user, context={'request': request})
    return json.dumps({
        'token': user.auth_token.key,
        'user': user.data
    })


@api_view(['POST', ])
@permission_classes((permissions.AllowAny,))
def user_register(request):
    username = request.POST.get('username', None)
    password = request.POST.get('password', None)
    email = request.POST.get('email', None)

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
    username = request.POST.get('username', None)
    password = request.POST.get('password', None)

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
        public = self.request.GET.get('public', '0') == '1'
        if public:
            workflows = Workflow.objects.filter(public=True)
        else:
            workflows = Workflow.objects.filter(user=self.request.user)
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
        return Widget.objects.filter(workflow__user=self.request.user).prefetch_related('inputs', 'outputs')

    @detail_route(methods=['post'], url_path='reset')
    def reset(self, request, pk=None):
        widget = get_object_or_404(Widget, pk=pk)
        widget.reset()
        return HttpResponse(json.dumps({'status': 'success'}), content_type="application/json")


class ConnectionViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows connections to be viewed or edited.
    """
    permission_classes = (IsAdminOrSelf,)
    serializer_class = ConnectionSerializer
    model = Connection

    def get_queryset(self):
        return Connection.objects.filter(workflow__user=self.request.user)


class InputViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows widget inputs to be viewed or edited.
    """
    permission_classes = (IsAdminOrSelf,)
    serializer_class = InputSerializer
    model = Input

    def get_queryset(self):
        return Input.objects.filter(widget__workflow__user=self.request.user)


class OutputViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows widget outputs to be viewed or edited.
    """
    permission_classes = (IsAdminOrSelf,)
    serializer_class = OutputSerializer
    model = Output

    def get_queryset(self):
        return Output.objects.filter(widget__workflow__user=self.request.user)


class AbstractInputViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAdminOrSelf,)
    serializer_class = AbstractInputSerializer
    model = AbstractInput


class AbstractOutputViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAdminOrSelf,)
    serializer_class = AbstractOutputSerializer
    model = AbstractOutput


class AbstractWidgetViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAdminOrSelf,)
    serializer_class = AbstractWidgetSerializer
    model = AbstractWidget


class CategoryViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows the widget library to be read.
    """
    permission_classes = (IsAdminOrSelf,)
    serializer_class = CategorySerializer
    model = Category

    def get_queryset(self):
        return Category.objects.filter(parent__isnull=True)#\
                    #.prefetch_related('widgets', 'widgets__inputs', 'widgets__outputs')
