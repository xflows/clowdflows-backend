import sys

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from workflows import module_importer
from workflows.models import Widget

import workflows.visualization_views


def setattr_local(name, value, package):
    setattr(sys.modules[__name__], name, value)


module_importer.import_all_packages_libs("views", setattr_local)


@login_required
def widget_iframe(request, widget_id):
    w = get_object_or_404(Widget, pk=widget_id)
    if (w.workflow.user == request.user):
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
        return view_to_call(request, input_dict, output_dict, w, True)
    else:
        return HttpResponse(status=400)
    return HttpResponse("OK")
