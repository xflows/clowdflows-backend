from rest_framework import permissions

from workflows.models import *


class IsAdminOrSelf(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.user and request.user.is_authenticated():
            # Don't allow adding widgets to workflows not owned by the user
            if view.model == Widget and 'workflow' in request.data:
                serializer = view.serializer_class(data=request.data)
                serializer.is_valid()
                workflow = serializer.validated_data['workflow']
                if request.GET.get('preview', '0') == '1':
                    if workflow.public:
                        return True
                return workflow.user == request.user
            if view.model == Workflow and 'staff_pick' in request.data:
                return request.user.is_staff
            else:
                return True

    def has_object_permission(self, request, view, obj):
        if request.user and request.user.is_authenticated():
            if request.user.is_superuser:
                return True

            # Allow only editing of the user's workflow objects
            if isinstance(obj, Workflow):
                return obj.user == request.user
            if isinstance(obj, Widget):
                return obj.workflow.user == request.user
            if isinstance(obj, Connection):
                return obj.workflow.user == request.user
            if isinstance(obj, Input):
                return obj.widget.workflow.user == request.user
            if isinstance(obj, Output):
                return obj.widget.workflow.user == request.user

        return False
