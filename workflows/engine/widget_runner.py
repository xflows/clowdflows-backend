import time
import workflows.library
from workflows.engine import ValueNotSet

from workflows.models import *
from workflows.tasks import *
from django.conf import settings


class WidgetRunner():
    def __init__(self, widget, inputs, outputs, workflow_runner):
        self.widget = widget
        self.widget_inputs = inputs
        self.widget_outputs = outputs
        self.workflow_runner = workflow_runner
        # save inputs? if savable and workflow_runner.parent_workflow_runner is None

    def run(self):
        self.widget.running = True
        new_value_per_variable = {}

        """ subprocesses and regular widgets get treated here """
        if self.widget.type == 'regular':  # or self.widget.type == 'subprocess':
            if self.widget.abstract_widget:
                function_to_call = getattr(workflows.library,
                                           self.widget.abstract_widget.action)  # getattr(workflows.library, self.abstract_widget.post_interact_action)
            input_dict = self.build_input_dictionary()
            start = time.time()
            # try:
            if self.widget.abstract_widget:
                if self.widget.abstract_widget.wsdl != '':
                    input_dict['wsdl'] = self.widget.abstract_widget.wsdl
                    input_dict['wsdl_method'] = self.widget.abstract_widget.wsdl_method
                if self.widget.abstract_widget.windows_queue and settings.USE_WINDOWS_QUEUE:
                    if self.widget.abstract_widget.has_progress_bar:
                        new_value_per_variable = executeWidgetProgressBar.apply_async([self.widget, input_dict],
                                                                                      queue="windows").wait()
                    elif self.widget.abstract_widget.is_streaming:
                        new_value_per_variable = executeWidgetStreaming.apply_async([self.widget, input_dict],
                                                                                    queue="windows").wait()
                    else:
                        new_value_per_variable = executeWidgetFunction.apply_async([self.widget, input_dict],
                                                                                   queue="windows").wait()
                else:
                    if self.widget.abstract_widget.has_progress_bar:
                        new_value_per_variable = function_to_call(input_dict, self.widget)
                    elif self.widget.abstract_widget.is_streaming:
                        new_value_per_variable = function_to_call(input_dict, self.widget, None)
                    else:
                        new_value_per_variable = function_to_call(input_dict)
            else:
                raise "this shouldn't happen (TM)"

            elapsed = (time.time() - start)
            new_value_per_variable['clowdflows_elapsed'] = elapsed
        elif self.widget.type == 'input':
            for o in self.widget_outputs:
                new_value_per_variable[o.variable] = self.workflow_runner.parent_workflow_runner.input_id_to_input[
                    o.outer_input_id].value
        else:  # self.widget.type IN 'output', 'for_output','cv_output'
            inner_input = self.widget_inputs[0]
            outer_output = self.workflow_runner.parent_workflow_runner.output_id_to_output[inner_input.outer_output_id]
            self.build_input_dictionary()

            # we need to assign outer outputs
            new_value_per_variable_outer = {}
            if self.widget.type == 'output':
                new_value_per_variable_outer[outer_output.variable] = inner_input.value
            elif self.widget.type == 'for_output' or self.widget.type == 'cv_output':
                new_value_per_variable_outer[outer_output.variable] = outer_output.value + [inner_input.value]

            # assign outer outputs and connected inputs
            self.assign_outputs([outer_output], new_value_per_variable_outer,
                                self.workflow_runner.parent_workflow_runner)

        self.widget.set_as_finished()
        # assign outputs and connected inputs
        self.assign_outputs(self.widget_outputs, new_value_per_variable, self.workflow_runner)

        if not self.workflow_runner.parent_workflow_runner: #is a widget which is not part of a subprocess
            self.widget.save_with_inputs_and_outputs(self.widget_inputs,self.widget_outputs,force_update=False)

    @staticmethod  # TODO could this method also use __init__ and WorkflowRunner
    def run_post(widget, request):
        if not widget.ready_to_run():
            raise WidgetException("The prerequisites for running this widget have not been met.")

        widget_inputs = widget.inputs.all()
        widget_outputs = widget.outputs.all()

        widget.interaction_waiting = False
        widget.running = True
        widget.save()
        input_dict = {}
        outputs = {}
        output_dict = {}
        for o in widget_outputs:
            output_dict[o.variable] = o.value
        for i in widget_inputs:
            # gremo pogledat ce obstaja povezava in ce obstaja gremo value prebrat iz outputa
            if not i.parameter:
                if i.connections.count() > 0:
                    i.value = i.connections.all()[0].output.value
                    i.save()
                else:
                    i.value = ValueNotSet
                    i.save()
            if i.multi_id == 0:
                input_dict[i.variable] = i.value
            else:
                if not i.variable in input_dict:
                    input_dict[i.variable] = []
                if i.value is not ValueNotSet:
                    input_dict[i.variable].append(i.value)
        try:
            if widget.abstract_widget.windows_queue and settings.USE_WINDOWS_QUEUE:
                t = executeWidgetPostInteract.apply_async([widget, input_dict, output_dict, request], queue="windows")
                outputs = t.wait()
            else:
                outputs = executeWidgetPostInteract(widget, input_dict, output_dict, request)

        except:
            widget.interaction_finished = False
            widget.set_as_faulty()
            widget.save()
            raise
        else:
            for o in widget_outputs:
                o.value = outputs[o.variable]
                o.save()
            widget.interaction_waiting = False
            widget.interaction_finished = True
            widget.set_as_finished()
            widget.save()
            cons = Connection.objects.filter(output__widget=widget)
            for c in cons:
                c.input.widget.unfinish()
            return outputs

    def assign_outputs(self, outputs, new_value_for_variable, workflow_runner, assign_inputs=True):
        for o in outputs:
            o.value = new_value_for_variable[o.variable]

            if assign_inputs:  # don't set connected inputs when waiting for an interaction
                for con in workflow_runner.get_connections_for_output(o):
                    workflow_runner.input_id_to_input[con.input_id].value = new_value_for_variable[o.variable]

    def build_input_dictionary(self):
        input_dictionary = {}
        for i in self.widget_inputs:
            """ if this isn't a parameter we need to fetch it
                from the output. """
            # if not i.parameter:
            #     connection = self.workflow_runner.get_connection_for_input(i)
            #     if connection:
            #         i.value = self.workflow_runner.output_id_to_output[connection.output_id].value
            #     else:
            #         i.value = None
            """ here we assign the value to the dictionary """
            if i.multi_id == 0:
                input_dictionary[i.variable] = i.value if i.value is not ValueNotSet else None
            else:  # it's a multiple input
                if not i.variable in input_dictionary:
                    input_dictionary[i.variable] = []
                if i.value is not ValueNotSet:  # not i.value==None and
                    input_dictionary[i.variable].append(i.value)
        return input_dictionary
