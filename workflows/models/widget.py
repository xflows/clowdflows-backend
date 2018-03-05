import json

from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from channels import Group

from workflows.models.abstract_input import AbstractInput
from workflows.models.abstract_output import AbstractOutput
from workflows.models.abstract_widget import AbstractWidget
from workflows.models.connection import Connection
from workflows.models.input import Input
from workflows.models.output import Output
from workflows.models.recommender import Recommender

class Widget(models.Model):
    """ Widget """
    # django relationship (ForeignKey), each widget is related to a single workflow
    workflow = models.ForeignKey('Workflow', related_name="widgets")
    x = models.IntegerField()  # a field
    y = models.IntegerField()  # a field
    name = models.CharField(max_length=200)  # a field
    abstract_widget = models.ForeignKey('AbstractWidget', related_name="instances", blank=True, null=True)
    finished = models.BooleanField(default=False)  # a field
    error = models.BooleanField(default=False)  # a field
    running = models.BooleanField(default=False)  # a field
    interaction_waiting = models.BooleanField(default=False)  # a field
    interaction_finished = models.BooleanField(default=False)  # a field
    save_results = models.BooleanField(default=False)

    """ type of widgets """
    WIDGET_CHOICES = (
        ('regular', 'Regular widget'),
        ('subprocess', 'Subprocess widget'),
        ('input', 'Input widget'),
        ('output', 'Output widget'),
        ('for_input', 'For input'),
        ('for_output', 'For output'),
        ('cv_input', 'Cross Validation input'),
        ('cv_output', 'Cross Validation output'),
        ('cv_input2', 'Cross Validation input 2'),
        ('cv_input3', 'Cross Validation input 3'),
    )
    type = models.CharField(max_length=50, choices=WIDGET_CHOICES, default='regular')

    progress = models.IntegerField(default=0)

    def prerequisite_widgets(self):
        return Widget.objects.filter(outputs__connections__input__widget=self)

    def following_widgets(self):
        return Widget.objects.filter(inputs__connections__output__widget=self)


    def is_special_subprocess_type(self):
        return self.type in ['input', 'output', 'for_input', 'for_output', 'cv_input', 'cv_output', 'cv_input2',
                             'cv_input3']
    def is_unfinished(self):
        return not self.finished and not self.running
        #     ready_to_run = True
        #     connections = self.connections.filter(input__widget=w).select_related('input__widget')
        #     for c in connections:
        #         if not c.output.widget.finished:
        #             # print c.output.widget
        #             ready_to_run = False
        #             break
        #     if ready_to_run:
        #         return True
        # return False
    def set_as_finished(self):
        self.running = False
        self.error = False
        self.finished = True
        #send_finished_notification(Widget, self)

    def set_as_faulty(self):
        self.error=True
        self.running=False
        self.finished=False
        #send_finished_notification(Widget, self)


    def update_input_output_order(self):
        for i, input in enumerate(self.inputs.all()):
            input.order = i + 1
            input.save()

        for i, output in enumerate(self.outputs.all()):
            output.order = i + 1
            output.save()

    def import_from_json(self, json_data, input_conversion, output_conversion):
        self.x = json_data['x']
        self.y = json_data['y']
        self.name = json_data['name']
        if json_data['abstract_widget']:
            aw = AbstractWidget.objects.get(uid=json_data['abstract_widget'],
                                            package=json_data['abstract_widget_package'])
            self.abstract_widget = aw
        # If no save_results is provided (for legacy workflows for example), set to false
        # by default or true for interactive widgets
        self.save_results = json_data.get('save_results', self.abstract_widget.always_save_results if self.abstract_widget else False)
        self.type = json_data['type']
        self.save()
        for i in json_data['inputs']:
            new_i = Input()
            new_i.widget = self
            new_i.import_from_json(i, input_conversion, output_conversion)
        for o in json_data['outputs']:
            new_o = Output()
            new_o.widget = self
            new_o.import_from_json(o, input_conversion, output_conversion)

    def export(self):
        d = {}
        if self.workflow_link_exists:
            d['workflow'] = self.workflow_link_data.export()
        else:
            d['workflow'] = None
        d['x'] = self.x
        d['y'] = self.y
        d['name'] = self.name
        d['save_results'] = self.save_results
        if self.abstract_widget:
            if self.abstract_widget.uid:
                d['abstract_widget'] = self.abstract_widget.uid
                d['abstract_widget_package'] = self.abstract_widget.package
            else:
                raise Exception("Cannot export a widget that doesn't have a UID. (" + str(self.name) + ")")
        else:
            d['abstract_widget'] = None
        # d['finished']=self.finished
        # d['error']=self.error
        # d['running']=self.running
        # d['interaction_waiting']=self.interaction_waiting
        d['type'] = self.type
        # d['progress']=self.progress
        d['inputs'] = []
        d['outputs'] = []
        for i in self.inputs_all:
            d['inputs'].append(i.export())
        for o in self.outputs_all:
            d['outputs'].append(o.export())
        return d

    def recommended_input_widgets(self):
        return [i for i in self.calc_recomm_inp() if i]

    def recommended_output_widgets(self):
        return [o for o in self.calc_recomm_out() if o]

    def calc_recomm_inp(self):
        num_recomm = 10

        # Self[Widget] has FK to abstract_widget [AbstractWidget]
        # [AbstractInput] has FK to [AbstractWidget]

        aw = self.abstract_widget

        """ Get abswidg.inputs for this widget """
        ainputs = AbstractInput.objects.filter(widget=aw)

        recomm_dict = {}  # key: w.name, val: sum(counts)

        for ainp in ainputs:
            if not ainp.parameter:
                """ Get recomm for all inputs of this abswidg """
                rarr = Recommender.objects.filter(inp=ainp)
                rarr = sorted(rarr, key=lambda r: r.count, reverse=True)[:num_recomm]
                for r in rarr:
                    # print "  widget:" + str( r.out.widget.name ) + " (out:" + str( r.out.name ) + ")  count: " + str( r.count )
                    if not (r.out.widget.name in recomm_dict):
                        recomm_dict[r.out.widget.name] = 0

                    recomm_dict[r.out.widget.name] += r.count

        # convert to tuple and sort; result: list of tuples
        recomm_lt = sorted(list(recomm_dict.items()), key=lambda el: el[1], reverse=True)
        # print aw.name + ".recomm_inp: " + str(recomm_lt)
        recomm_l = [el[0] for el in recomm_lt]
        return recomm_l
        res = str(":::".join(recomm_l))
        return res

    def calc_recomm_out(self):
        num_recomm = 10
        aw = self.abstract_widget

        """ Get abswidg.inputs for this widget """
        aoutputs = AbstractOutput.objects.filter(widget=aw)

        recomm_dict = {}  # key: w.name, val: sum(counts)

        for aout in aoutputs:
            """ Get recomm for all outputs of this abswidg """
            rarr = Recommender.objects.filter(out=aout)
            rarr = sorted(rarr, key=lambda r: r.count, reverse=True)[:num_recomm]
            for r in rarr:
                # print "  widget:" + str( r.inp.widget.name ) + " (out:" + str( r.inp.name ) + ")  count: " + str( r.count )
                if not (r.inp.widget.name in recomm_dict):
                    recomm_dict[r.inp.widget.name] = 0

                recomm_dict[r.inp.widget.name] += r.count

        # convert to tuple and sort; result: list of tuples
        recomm_lt = sorted(list(recomm_dict.items()), key=lambda el: el[1], reverse=True)
        # print aw.name + ".recomm_out: " + str(recomm_lt)
        recomm_l = [el[0] for el in recomm_lt]
        return recomm_l
        res = str(":::".join(recomm_l))
        return res

    # ========================================================================

    def is_visualization(self):
        try:
            if self.abstract_widget.visualization_view != '':
                return True
        except:
            return False

    def is_interaction(self):
        try:
            if self.abstract_widget.interactive:
                return True
        except:
            return False

    def ready_to_run(self):
        return self.prerequisite_widgets().filter(finished=False).count() == 0

    def unfinish(self):
        self.descendants_to_reset()

    def subunfinish(self):
        if self.type == 'subprocess':
            for w in self.workflow_link.widgets.all():
                w.finished = False
                w.error = False
                w.save()
                if w.type == 'subprocess':
                    w.subunfinish()

    def rename(self, new_name):
        self.name = new_name
        self.save()
        if self.type == 'input':
            inp = self.outputs.all()[0]
            inp.short_name = self.name[:3]
            inp.name = self.name
            inp.save()
            inp.outer_input.name = self.name
            inp.outer_input.short_name = self.name[:3]
            inp.outer_input.save()
        if self.type == 'output':
            inp = self.inputs.all()[0]
            inp.short_name = self.name[:3]
            inp.name = self.name
            inp.save()
            inp.outer_output.name = self.name
            inp.outer_output.short_name = self.name[:3]
            inp.outer_output.save()
        try:
            w_link = self.workflow_link
            w_link.name = new_name
            w_link.save()
        except ObjectDoesNotExist:
            pass

    def run(self,_):
        from workflows.engine import WorkflowRunner
        WorkflowRunner(self.workflow,final_widget=self).run()  #run with ancestors


    def reset(self):
        self.inputs.filter(parameter=False).update(value=None)
        self.outputs.update(value=None)

        self.finished = False
        self.error = False
        self.running = False
        self.interaction_finished = False
        self.interaction_waiting = False
        self.save()
        if self.type == 'subprocess':
            self.subunfinish()

    def descendants_to_reset(self):
        """ Method resets all the widget connections/descendants. """
        pairs = []
        for c in self.workflow.connections.select_related("output", "input").defer("output__value",
                                                                                   "input__value").all():
            if not (c.output.widget_id, c.input.widget_id) in pairs:
                pairs.append((c.output.widget_id, c.input.widget_id))
        next = {}
        for p in pairs:
            if p[0] not in next:
                next[p[0]] = set()
            next[p[0]].add(p[1])
        widgets_that_need_reset = set([self.pk, ])
        current_widgets_that_need_reset = set([self.pk, ])
        while len(current_widgets_that_need_reset) > 0:
            new_widgets_that_need_reset = set()
            for w_id in current_widgets_that_need_reset:
                try:
                    for p in next.get(w_id):
                        new_widgets_that_need_reset.add(p)
                        widgets_that_need_reset.add(p)
                except:
                    pass
            current_widgets_that_need_reset = new_widgets_that_need_reset
        Widget.objects.filter(id__in=widgets_that_need_reset).update(finished=False, error=False, running=False)
        subprocesses = Widget.objects.filter(id__in=widgets_that_need_reset, type='subprocess')
        for w in subprocesses:
            w.subunfinish()
        return widgets_that_need_reset


    def save_with_inputs_and_outputs(self,inputs,outputs,force_update=False):
        if self.save_results:
            for i in inputs:
                i.save(force_update=force_update)
            for o in outputs:
                o.save(force_update=force_update)
        self.save(force_update=force_update)

    def __str__(self):
        return str(self.name)


@receiver(post_save, sender=Widget)
def send_finished_notification(sender, instance, **kwargs):
    print(instance.name,instance.id, instance.finished)
    status = {
        'finished': instance.finished,
        'error': instance.error,
        'running': instance.running,
        'interaction_waiting': instance.interaction_waiting,
        'is_visualization': instance.is_visualization(),
        'is_interaction': instance.is_interaction()
    }
    position = {
        'x': int(instance.x),
        'y': int(instance.y)
    }
    Group("workflow-{}".format(instance.workflow.pk)).send({
        'text': json.dumps({'status': status, 'position': position, 'widget_pk': instance.pk})
    }, immediately=True)
    a=5

