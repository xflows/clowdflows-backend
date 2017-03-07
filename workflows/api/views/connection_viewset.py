from django.db.models import Q, Max
from django.http import HttpResponse
from rest_framework import viewsets
from rest_framework.renderers import JSONRenderer

from workflows.api.permissions import IsAdminOrSelf
from workflows.api.serializers import *
from workflows.utils import checkForCycles


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
        previousExists = False

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
                message = "Adding this connection would result in a cycle in the workflow."
                data = json.dumps({'message': message, 'status': 'error'})
                return HttpResponse(data, 'application/javascript')
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
            serializer = ConnectionSerializer(new_c, context={'request': request})
            data = JSONRenderer().render(serializer.data)
            return HttpResponse(data, 'application/javascript')
        else:
            message = "Cannot connect widgets from different workflows."
            data = json.dumps({'message': message, 'status': 'error'})
            return HttpResponse(data, 'application/javascript')

    def destroy(self, request, pk=None, **kwargs):
        c = self.get_object()
        # Are we just swapping connections? Don't delete any multi_id inputs if we are
        replacing = request.GET.get('replacing', '0') == '1'
        c.input.widget.unfinish()
        refresh = -1
        refreshworkflow = -1
        already_deleted = False
        if c.input.multi_id != 0 and not replacing:
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
        return HttpResponse(data, 'application/javascript')
