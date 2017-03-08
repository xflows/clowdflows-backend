import time
import workflows.library

from workflows.models import *
from workflows.tasks import *
from django.conf import settings


class WidgetRunner():
    def __init__(self,widget,inputs,outputs,workflow_runner):
        self.widget = widget
        self.widget_inputs = inputs
        self.widget_outputs = outputs
        self.workflow_runner = workflow_runner
        self.inner_workflow_runner = None
        # prepare inputs (with proper values) in workflow_runner?
        # save inputs? if savable and workflow_runner.parent_workflow_runner is None

    def run(self):
        self.widget.running = True
        """ subprocesses and regular widgets get treated here """
        if self.widget.type == 'regular' or self.widget.type == 'subprocess':
            if self.widget.abstract_widget:
                function_to_call = getattr(workflows.library,self.widget.abstract_widget.action) #getattr(workflows.library, self.abstract_widget.post_interact_action)
            input_dict = self.get_input_dictionary_and_assign_values()
            outputs = {}
            start = time.time()
            try:
                if self.widget.abstract_widget:
                    if self.widget.abstract_widget.wsdl != '':
                        input_dict['wsdl']=self.widget.abstract_widget.wsdl
                        input_dict['wsdl_method']=self.widget.abstract_widget.wsdl_method
                    if self.widget.abstract_widget.windows_queue and settings.USE_WINDOWS_QUEUE:
                        if self.widget.abstract_widget.has_progress_bar:
                            outputs = executeWidgetProgressBar.apply_async([self.widget,input_dict],queue="windows").wait()
                        elif self.widget.abstract_widget.is_streaming:
                            outputs = executeWidgetStreaming.apply_async([self.widget,input_dict],queue="windows").wait()
                        else:
                            outputs = executeWidgetFunction.apply_async([self.widget,input_dict],queue="windows").wait()
                    else:
                        if self.widget.abstract_widget.has_progress_bar:
                            outputs = function_to_call(input_dict,self.widget)
                        elif self.widget.abstract_widget.is_streaming:
                            outputs = function_to_call(input_dict,self.widget,None)
                        else:
                            outputs = function_to_call(input_dict)
                else:
                    """ we run the subprocess """
                    from workflows.engine.workflow_runner import WorkflowRunner #TODO temp solution, maybe delete this run method?
                    self.inner_workflow_runner = WorkflowRunner(self.widget.workflow_link,
                                                                parent_workflow_runner=self.workflow_runner)
                    self.inner_workflow_runner.run()
            except Exception,c:
                self.widget.error=True
                self.widget.running=False
                self.widget.finished=False
                raise c
            elapsed = (time.time()-start)
            outputs['clowdflows_elapsed']=elapsed
            self.assign_outputs(outputs)
        elif self.widget.type == 'input':
            for o in self.widget_outputs:
                o.value = self.workflow_runner.parent.inputs[o.outer_input_id].value
        elif self.widget.type == 'output':
            self.get_input_dictionary_and_assign_values()
            for i in self.widget_inputs:
                self.workflow_runner.parent.outputs[i.outer_output_id].value = i.value
        elif self.widget.type == 'for_output':
            self.get_input_dictionary_and_assign_values()
            for i in self.widget_inputs:
                self.workflow_runner.parent.outputs[i.outer_output_id].value.append(i.value)
        elif self.widget.type == 'cv_output':
            self.get_input_dictionary_and_assign_values()
            for i in self.widget_inputs:
                self.workflow_runner.parent.outputs[i.outer_output_id].value.append(i.value)

        self.widget.running = False
        self.widget.error = False
        self.widget.finished = True


    @staticmethod #TODO could this method also use __init__ and WorkflowRunner
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
                    i.value = None
                    i.save()
            if i.multi_id == 0:
                input_dict[i.variable] = i.value
            else:
                if not i.variable in input_dict:
                    input_dict[i.variable] = []
                if not i.value == None:
                    input_dict[i.variable].append(i.value)
        try:
            if widget.abstract_widget.windows_queue and settings.USE_WINDOWS_QUEUE:
                t = executeWidgetPostInteract.apply_async([widget, input_dict, output_dict, request], queue="windows")
                outputs = t.wait()
            else:
                outputs = executeWidgetPostInteract(widget, input_dict, output_dict, request)

        except:
            widget.error = True
            widget.running = False
            widget.finished = False
            widget.interaction_finished = False
            widget.save()
            raise
        for o in widget_outputs:
            o.value = outputs[o.variable]
            o.save()
        widget.finished = True
        widget.running = False
        widget.error = False
        widget.interaction_waiting = False
        widget.interaction_finished = True
        widget.save()
        cons = Connection.objects.filter(output__widget=widget)
        for c in cons:
            c.input.widget.unfinish()
        return outputs

    def assign_outputs(self,outputs):
        for o in self.widget_outputs:
            try:
                o.value = outputs[o.variable]
            except:
                pass

    def get_input_dictionary_and_assign_values(self):
        input_dictionary = {}
        for i in self.widget_inputs:
            """ if this isn't a parameter we need to fetch it
                from the output. """
            if not i.parameter:
                connection = self.workflow_runner.get_connection_for_input(i)
                if connection:
                    i.value = self.workflow_runner.output_id_to_output[connection.output_id].value
                else:
                    i.value = None
            """ here we assign the value to the dictionary """
            if i.multi_id==0:
                input_dictionary[i.variable]=i.value
            else: # it's a multiple input
                if not i.variable in input_dictionary:
                    input_dictionary[i.variable]=[]
                if not i.value==None:
                    input_dictionary[i.variable].append(i.value)
        return input_dictionary

