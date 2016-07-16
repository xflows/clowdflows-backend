from rest_framework import permissions

from workflows.models import *


class IsAdminOrSelf(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.user and request.user.is_authenticated():
            return True

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS or request.user.is_superuser:
            return True

        # Allow only editing of the user's workflow objects
        if isinstance(obj, Workflow):
            return obj.user == request.user
        if isinstance(obj, Widget):
            obj.workflow.user == request.user
        if isinstance(obj, Connection):
            obj.workflow.user == request.user
        if isinstance(obj, Input):
            obj.widget.workflow.user == request.user
        if isinstance(obj, Output):
            obj.widget.workflow.user == request.user
        else:
            return False
