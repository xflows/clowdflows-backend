from django.db.models import Q
from django.http import HttpResponse
from rest_framework import viewsets
from rest_framework.decorators import detail_route
from rest_framework.generics import get_object_or_404

from workflows.permissions import IsAdminOrSelf
from workflows.serializers import *


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
        user_only = self.request.GET.get('user', '0') == '1'
        if user_only:
            filters = Q(user=self.request.user)
        else:
            filters = Q(user=self.request.user) | Q(public=True)
        workflows = Workflow.objects.filter(filters)
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
        pass

    @detail_route(methods=['post'], url_path='subprocess-output')
    def add_subprocess_output(self, request, pk=None):
        pass

    @detail_route(methods=['post'], url_path='subprocess-forloop')
    def add_subprocess_forloop(self, request, pk=None):
        pass

    @detail_route(methods=['post'], url_path='subprocess-xvalidation')
    def add_subprocess_xvalidation(self, request, pk=None):
        pass

    @detail_route(methods=['post'], url_path='reset')
    def reset(self, request, pk=None):
        workflow = get_object_or_404(Workflow, pk=pk)
        for widget in workflow.widgets.filter():
            widget.reset()
        return HttpResponse(json.dumps({'status': 'ok'}), content_type="application/json")
