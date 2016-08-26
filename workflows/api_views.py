from django.contrib.auth import authenticate
from django.http import HttpResponse
from rest_framework import viewsets, permissions
from rest_framework.decorators import api_view, permission_classes, detail_route
from django.contrib.auth import logout
from django.db.models import Q, Max
from rest_framework.generics import get_object_or_404

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
