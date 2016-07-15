from django.contrib.auth import authenticate
from django.http import HttpResponse
from rest_framework import viewsets, permissions
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from django.contrib.auth import logout
from workflows.serializers import *


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


class WorkflowViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows workflows to be viewed or edited.
    """
    model = Workflow
    filter_fields = ('public',)

    def get_serializer_class(self):
        if self.action == 'list':
            return WorkflowListSerializer
        return WorkflowSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_queryset(self):
        return Workflow.objects.filter(user=self.request.user).prefetch_related('widgets', 'widgets__inputs',
                                                                                'widgets__outputs')


class WidgetViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows widgets to be viewed or edited.
    """
    model = Widget
    filter_fields = ('workflow',)

    def get_serializer_class(self):
        if self.action == 'list':
            return WidgetListSerializer
        return WidgetSerializer

    def get_queryset(self):
        return Widget.objects.filter(workflow__user=self.request.user).prefetch_related('inputs', 'outputs')


class ConnectionViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows connections to be viewed or edited.
    """
    serializer_class = ConnectionSerializer
    model = Connection

    def get_queryset(self):
        return Connection.objects.filter(workflow__user=self.request.user)


class InputViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows widget inputs to be viewed or edited.
    """
    serializer_class = InputSerializer
    model = Input

    def get_queryset(self):
        return Input.objects.filter(widget__workflow__user=self.request.user)


class OutputViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows widget outputs to be viewed or edited.
    """
    serializer_class = OutputSerializer
    model = Output

    def get_queryset(self):
        return Output.objects.filter(widget__workflow__user=self.request.user)
