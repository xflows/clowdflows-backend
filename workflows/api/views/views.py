from django.contrib.auth import authenticate
from django.contrib.auth import logout
from django.db.models import Q
from django.http import HttpResponse
from rest_framework import viewsets, permissions
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes, detail_route, list_route

from mothra.local_settings import FILES_FOLDER, PACKAGE_TREE
from services.webservice import WebService
from workflows.api.permissions import IsAdminOrSelf
from workflows.api.serializers import *
from workflows.helpers import ensure_dir


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


@api_view(['GET', ])
@permission_classes((permissions.IsAuthenticated,))
def recommender_model(request):
    '''
    @return: A recommender model, basically a mapping between abstract inputs and outpus 
    '''
    recommender_maps = Recommender.load_recommendations()
    recommender = {
        'recomm_for_abstract_output_id': recommender_maps[0],
        'recomm_for_abstract_input_id': recommender_maps[1]
    }
    return HttpResponse(json.dumps(recommender), content_type="application/json")

@api_view(['GET', ])
@permission_classes((permissions.IsAuthenticated,))
def widget_library(request):
    '''
    @return: TODO 
    '''
    categories=Category.objects.filter(parent__isnull=True).prefetch_related(
            'widgets','widgets__inputs','widgets__outputs','widgets__inputs__options','children')
    hierarchy=[]
    packages_already_added=[]
    for category in PACKAGE_TREE:
        filtered_categories =categories.filter(widgets__package__in=category['packages']).distinct()
        packages_already_added.extend(category['packages'])

        hierarchy.append({'children': CategorySerializer(filtered_categories,many=True).data,
                    'name': category['name']+" widgets", 'order': category['order'], 'user': None, 'widgets': []})

    hierarchy.append({'name': 'Base widgets', 'order': -1, 'user': None, 'widgets': [],
        'children': CategorySerializer(categories.exclude(widgets__package__in=packages_already_added), context={'request': request}, many=True).data})


    return HttpResponse(json.dumps(sorted(hierarchy, key=lambda x: x['order'])), content_type="application/json")


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

    @detail_route(methods=['post'], url_path='upload')
    def upload(self, request, pk=None):
        input = self.get_object()
        try:
            destination = FILES_FOLDER + str(input.widget.workflow.id) + '/' + request.FILES['file'].name
            ensure_dir(destination)
            destination_file = open(destination, 'wb')
            for chunk in request.FILES['file'].chunks():
                destination_file.write(chunk)
            destination_file.close()
            input.value = destination
            input.save()
            input.widget.unfinish()
            data = json.dumps(
                {'status': 'ok', 'message': 'File successfully uploaded'})
        except Exception, e:
            data = json.dumps(
                {'status': 'error', 'message': 'Problem uploading file: {}'.format(str(e))})
        return HttpResponse(data, 'application/json')


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
        STRING_CUTOFF_CHARS = 300
        output = self.get_object()
        try:
            json.dumps(output.value)
        except:
            serialized_value = repr(output.value)
        else:
            serialized_value = output.value
            if type(serialized_value) == str:
                serialized_value = '{} [ ... ]'.format(serialized_value[:STRING_CUTOFF_CHARS])
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
        return Category.objects.filter(parent__isnull=True).prefetch_related(
            'widgets','widgets__inputs','widgets__outputs','widgets__inputs__options','children')

    @list_route(methods=['post'], url_path='import-ws')
    def import_webservice(self, request):
        wsdl = request.data.get('wsdl')
        ws = WebService(wsdl)
        wsdl_category, _ = Category.objects.get_or_create(name='WSDL Imports')
        new_c = Category()
        current_name = ws.name
        i = 0
        while request.user.categories.filter(name=current_name).count() > 0:
            i = i + 1
            current_name = ws.name + ' (' + str(i) + ')'
        new_c.name = current_name
        new_c.user = request.user
        new_c.workflow = request.user.userprofile.active_workflow
        new_c.parent = wsdl_category
        new_c.save()
        for m in ws.methods:
            new_a = AbstractWidget()
            new_a.name = m['name']
            new_a.action = 'call_webservice'
            new_a.wsdl = ws.wsdl_url
            new_a.wsdl_method = m['name']
            new_a.description = m['documentation']
            new_a.user = request.user
            new_a.category = new_c
            new_a.save()
            new_i = AbstractInput()
            new_i.parameter = True
            new_i.widget = new_a
            new_i.name = "Timeout"
            new_i.short_name = "to"
            new_i.variable = "timeout"
            new_i.default = '60'
            new_i.parameter_type = 'text'
            new_i.save()
            new_i = AbstractInput()
            new_i.parameter = True
            new_i.widget = new_a
            new_i.name = "Send empty strings to webservices"
            new_i.short_name = "ses"
            new_i.variable = "sendemptystrings"
            new_i.default = ''
            new_i.parameter_type = 'checkbox'
            new_i.save()
            for i in m['inputs']:
                new_i = AbstractInput()
                new_i.name = i['name']
                new_i.variable = i['name']
                new_i.short_name = i['name'][:3]
                new_i.description = ''
                new_i.required = False
                new_i.parameter = False
                if i['type'] == bool:
                    new_i.parameter_type = 'checkbox'
                else:
                    new_i.parameter_type = 'textarea'
                new_i.default = ''
                new_i.widget = new_a
                new_i.save()
            for o in m['outputs']:
                new_o = AbstractOutput()
                new_o.name = o['name']
                new_o.variable = o['name']
                new_o.short_name = o['name'][:3]
                new_o.description = ''
                new_o.widget = new_a
                new_o.save()
        data = json.dumps({'category_id': new_c.id})
        return HttpResponse(data, 'application/json')
