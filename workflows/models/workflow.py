from collections import defaultdict

from django.contrib.auth.models import User
from django.db import models

from workflows.models.option import Option
from workflows.models.output import Output
from workflows.models.input import Input
from workflows.models.connection import Connection
from workflows.models.widget import Widget


class Workflow(models.Model):
    name = models.CharField(max_length=200, default='Untitled workflow')  # a field
    user = models.ForeignKey(User,
                             related_name="workflows")  # django relationship (ForeignKey), each Workflow is related to a single User
    public = models.BooleanField(default=False)  # a field
    description = models.TextField(blank=True, default='')  # a field
    widget = models.OneToOneField('Widget', related_name="workflow_link", blank=True, null=True)
    template_parent = models.ForeignKey('Workflow', blank=True, null=True, default=None, on_delete=models.SET_NULL)

    def import_from_json(self, json_data, input_conversion, output_conversion):
        self.name = json_data['name']
        self.description = json_data['description']
        self.save()
        for widget in json_data['widgets']:
            w = Widget()
            w.workflow = self
            w.import_from_json(widget, input_conversion, output_conversion)
            if widget['workflow']:
                subwidget_workflow = Workflow()
                subwidget_workflow.user = self.user
                subwidget_workflow.import_from_json(widget['workflow'], input_conversion, output_conversion)
                subwidget_workflow.widget = w
                subwidget_workflow.save()
        for connection in json_data['connections']:
            c = Connection()
            c.workflow = self
            c.import_from_json(connection, input_conversion, output_conversion)

    def export(self):
        """ Exports the workflow to a dictionary that can be imported """
        d = {}
        d['name'] = self.name
        d['description'] = self.description
        d['widgets'] = []
        inps = Input.objects.filter(widget__workflow=self).defer('value').prefetch_related('options')
        outs = Output.objects.filter(widget__workflow=self).defer('value')
        widgets = self.widgets.all().select_related('abstract_widget')
        workflow_links = Workflow.objects.filter(widget__in=widgets)
        inps_by_id = {}
        outs_by_id = {}
        for i in inps:
            l = inps_by_id.get(i.widget_id, [])
            l.append(i)
            inps_by_id[i.widget_id] = l
        for o in outs:
            l = outs_by_id.get(o.widget_id, [])
            l.append(o)
            outs_by_id[o.widget_id] = l
        for w in widgets:
            for workflow in workflow_links:
                if workflow.widget_id == w.id:
                    w.workflow_link_data = workflow
                    w.workflow_link_exists = True
                    break
            else:
                w.workflow_link_exists = False
            w.inputs_all = inps_by_id.get(w.id, [])
            w.outputs_all = outs_by_id.get(w.id, [])
            d['widgets'].append(w.export())
        d['connections'] = []
        for c in self.connections.all():
            d['connections'].append(c.export())
        return d

    def can_be_streaming(self):
        """ Method checks if workflow can be streamed. Check if there is at least one widget with
        the flag abstract_widget__is_streaming on True.  """
        if self.widgets.filter(abstract_widget__is_streaming=True).count() > 0:
            return True
        else:
            return False

    def is_for_loop(self):
        """ Method checks if workflow is a for loop. Checks if at least one widget is
        type for_input. """
        if self.widgets.filter(type='for_input').count() > 0:
            return True
        else:
            return False

    def is_cross_validation(self):
        """ Method checks if workflow is a for loop. Checks if at least one widget is
        type cv input. """
        if self.widgets.filter(type='cv_input').count() > 0:
            return True
        else:
            return False

    def get_ready_to_run(self):
        """ Method prepares this workflows widgets. Returns a list of widget id-s. """
        widgets = self.widgets.all()
        unfinished_list = []
        for w in widgets:
            if not w.finished and not w.running:
                """ if widget isn't finished and is not running than true"""
                ready_to_run = True
                connections = self.connections.filter(input__widget=w)
                for c in connections:
                    if not c.output.widget.finished:
                        """ if widget not finished than true """
                        ready_to_run = False
                        break
                if ready_to_run:
                    unfinished_list.append(w.id)
        return unfinished_list

    def get_runnable_widget_ids(self, last_runnable_widget_id=None):
        """ Returns a list of widget ids, which are required to be run either for completion of the entire workflow or
        for completion of the widget represented with the last_runnable_widget_id. """
        widgets_id_to_widget = dict([(w.id,w) for w in self.widgets.all()])
        connections=self.connections.select_related('input','output').all()

        widget_id_to_predecessor_widget_ids=defaultdict(list)
        for c in connections:
            # predecessor -> output -> connection -> input -> widget
            widget_id_to_predecessor_widget_ids[c.input.widget_id].append(c.output.widget_id)

        if last_runnable_widget_id:
            widget_ids=set()
            check_widgets = set([last_runnable_widget_id])
            while len(check_widgets)>0:
                widget=widgets_id_to_widget[check_widgets.pop()]
                if not widget.save_results or widget.is_unfinished(): #results not already saved on widget
                    predecessors=widget_id_to_predecessor_widget_ids[widget.id]
                    widget_ids.add(widget.id)
                    check_widgets.update(predecessors)
            return list(widget_ids)
        else:
            return widgets_id_to_widget.keys()

    def get_runnable_widgets(self,last_runnable_widget_id=None):
        return self.widgets.filter(id__in=self.get_runnable_widget_ids(last_runnable_widget_id=last_runnable_widget_id))\
            .select_related('abstract_widget').prefetch_related('inputs','outputs')


    def add_normal_subprocess(self, start_x=0, start_y=0):
        new_w = Workflow()
        new_w.name = "Untitled widget"
        new_w.user = self.user
        w = Widget()
        w.workflow = self
        w.workflow_link = new_w
        w.x = start_x + 50
        y = start_y + 50
        while self.widgets.filter(y=y, x=w.x).count() > 0:
            y = y + 100
        w.y = y
        w.name = "Untitled widget"
        w.type = 'subprocess'
        w.save()
        new_w.widget = w
        new_w.save()
        w.defered_outputs = w.outputs.defer("value").all()
        w.defered_inputs = w.inputs.defer("value").all()
        return new_w, w

    def rename(self, new_name):
        self.name = new_name
        self.save()

    @models.permalink
    def get_absolute_url(self):
        return ('open workflow', [str(self.id)])

    @models.permalink
    def get_copy_url(self):
        return ('copy workflow', [str(self.id)])

    @models.permalink
    def get_info_url(self):
        return ('workflow information', [str(self.id)])

    @models.permalink
    def get_export_url(self):
        return ('export workflow', [str(self.id)])

    def __unicode__(self):
        return unicode(self.name)

    class Meta:
        ordering = ['name']






def copy_workflow(old, user, parent_widget_conversion={}, parent_input_conversion={}, parent_output_conversion={},
                  parent_widget=None):
    w = Workflow()
    if parent_widget is None:
        w.name = old.name + " (copy)"
    else:
        w.name = old.name
    w.user = user
    w.public = False
    w.description = old.description
    w.template_parent = old
    if not parent_widget is None:
        w.widget = parent_widget
    w.save()
    widget_conversion = {}
    input_conversion = {}
    output_conversion = {}
    for widget in old.widgets.all():
        new_widget = Widget()
        new_widget.workflow = w
        new_widget.x = widget.x
        new_widget.y = widget.y
        new_widget.name = widget.name
        new_widget.abstract_widget = widget.abstract_widget
        new_widget.finished = widget.finished
        new_widget.error = widget.error
        new_widget.running = widget.running
        new_widget.interaction_waiting = widget.interaction_waiting
        new_widget.type = widget.type
        new_widget.progress = widget.progress
        new_widget.save()
        widget_conversion[widget.id] = new_widget.id
        for input in widget.inputs.all():
            new_input = Input()
            new_input.name = input.name
            new_input.short_name = input.short_name
            new_input.description = input.description
            new_input.variable = input.variable
            new_input.widget = new_widget
            new_input.required = input.required
            new_input.parameter = input.parameter
            new_input.value = input.value
            new_input.multi_id = input.multi_id
            # inner_output nikol ne nastavlamo
            # outer_output in njemu spremenimo inner input
            if not parent_widget is None:
                if not input.outer_output is None:
                    new_input.outer_output = Output.objects.get(pk=parent_output_conversion[input.outer_output.id])
            new_input.parameter_type = input.parameter_type
            new_input.save()
            for option in input.options.all():
                new_option = Option()
                new_option.input = new_input
                new_option.name = option.name
                new_option.value = option.value
                new_option.save()
            if not parent_widget is None:
                if not input.outer_output is None:
                    new_input.outer_output.inner_input = new_input
                    new_input.outer_output.save()
            input_conversion[input.id] = new_input.id
        for output in widget.outputs.all():
            new_output = Output()
            new_output.name = output.name
            new_output.short_name = output.short_name
            new_output.description = output.description
            new_output.variable = output.variable
            new_output.widget = new_widget
            new_output.value = output.value
            # inner input nikol ne nastavlamo
            # outer input in njemu spremenimo inner output
            if not parent_widget is None:
                if not output.outer_input is None:
                    new_output.outer_input = Input.objects.get(pk=parent_input_conversion[output.outer_input.id])
            new_output.save()
            if not parent_widget is None:
                if not output.outer_input is None:
                    new_output.outer_input.inner_output = new_output
                    new_output.outer_input.save()
            output_conversion[output.id] = new_output.id
    for connection in old.connections.all():
        new_connection = Connection()
        new_connection.workflow = w
        new_connection.output = Output.objects.get(pk=output_conversion[connection.output.id])
        new_connection.input = Input.objects.get(pk=input_conversion[connection.input.id])
        new_connection.save()
    for widget in old.widgets.filter(type='subprocess'):
        # tuki mormo vse subprocesse zrihtat
        copy_workflow(widget.workflow_link, user, widget_conversion, input_conversion, output_conversion,
                      Widget.objects.get(pk=widget_conversion[widget.id]))
    return w
