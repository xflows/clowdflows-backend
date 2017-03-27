from django.db.models import Prefetch

from workflows.engine.widget_runner import WidgetRunner
from workflows.models import *
from collections import defaultdict

class ValueNotSet:
    pass

class WorkflowRunner():


    def __init__(self, workflow, final_widget=None, clean=True, parent_workflow_runner=None):
        self.workflow = workflow
        self.connections = workflow.connections.all()
        self.widgets = workflow.get_runnable_widgets(last_runnable_widget_id=final_widget and final_widget.id)
        self.input_id_to_input= {}
        self.output_id_to_output= {}
        self.inputs_per_widget_id = defaultdict(list)
        self.outputs_per_widget_id = defaultdict(list)

        for w in self.workflow.widgets.prefetch_related(
                Prefetch('outputs', queryset=Output.objects.all()),
                Prefetch('inputs', queryset=Input.objects.filter(parameter=True),to_attr="parameter_inputs"),
                Prefetch('inputs', queryset=Input.objects.filter(parameter=False).defer("value"),to_attr="connection_inputs")):
            for i in w.parameter_inputs+w.connection_inputs:
                self.input_id_to_input[i.id] = i
                if not i.parameter:
                    i.value=ValueNotSet
                self.inputs_per_widget_id[w.id].append(i)
            for o in w.outputs.all():
                if not w.save_results:
                    o.value=ValueNotSet
                self.output_id_to_output[o.id] = o
                self.outputs_per_widget_id[w.id].append(o)
        self.clean = clean
        self.parent = parent_workflow_runner

    def is_for_loop(self):
        for w in self.widgets:
            if w.type=='for_input':
                return True
        return False

    def is_cross_validation(self):
        for w in self.widgets:
            if w.type=='cv_input':
                return True
        return False

    def cleanup(self):
        for w in self.widgets:
            if self.clean:
                w.finished = False
            w.error = False        

    def get_connection_for_output(self,output):
        for c in self.connections:
            if c.output_id==output.id:
                return c
        return None

    def get_connection_for_input(self,input):
        for c in self.connections:
            if c.input_id==input.id:
                return c
        return None
    #
    # @property
    # def finished_widgets(self):
    #     finished_widgets = []
    #     for w in self.widgets:
    #         if w.finished:
    #             finished_widgets.append(w)
    #     return finished_widgets

    @property
    def unfinished_widgets(self):
        unfinished_widgets = []
        for w in self.widgets:
            if not w.finished and not w.running and not w.error:
                unfinished_widgets.append(w)
        return unfinished_widgets

    @property
    def runnable_widgets(self):
        """ a widget is runnable if all widgets connected before
            it are finished (i.e. widgets that have outputs that 
            are connected to this widget's input) """

        # finished_widget_ids = [w.id for w in self.finished_widgets]
        runnable = []
        for w in self.unfinished_widgets:
            widget_connections= [c for c in self.connections if self.input_id_to_input[c.input_id].widget_id == w.id]
            # widget_connections= [c for c in self.connections if c.input_id in self.inputs_per_widget_id]

            #check if all outputs are connection outputs are calculated
            # c.output_id in self.outputs and
            if all([self.output_id_to_output[c.output_id].value!=ValueNotSet for c in widget_connections]):
                runnable.append(w)
        return runnable

    def run_all_unfinished_widgets(self):
        runnable_widgets = self.runnable_widgets
        while len(runnable_widgets)>0:
            for w in runnable_widgets:
                wr = WidgetRunner(w,self.inputs_per_widget_id[w.id],self.outputs_per_widget_id[w.id],self)
                try:
                    wr.run()
                except:
                    self.save()
                    raise
            runnable_widgets = self.runnable_widgets

    def run(self):
        self.cleanup()
        if self.is_for_loop():
            fi = None
            fo = None
            for w in self.widgets:
                if w.type=='for_input':
                    fi = w
                if w.type=='for_output':
                    fo = w
            outer_output = self.parent.outputs[fo.inputs.all()[0].outer_output_id]
            outer_output.value = []
            input_list = self.parent.inputs[fi.outputs.all()[0].outer_input_id].value
            for i in input_list:
                self.cleanup()
                proper_output = fi.outputs.all()[0]
                proper_output.value = i
                fi.finished = True
                self.run_all_unfinished_widgets()
        elif self.is_cross_validation():
            import random as rand
            fi = None
            fo = None
            for w in self.widgets:
                if w.type=='cv_input':
                    fi = w
                if w.type=='cv_output':
                    fo = w
            outer_output = self.parent.outputs[fo.inputs.all()[0].outer_output_id]
            outer_output.value = []
            input_list = self.parent.inputs[fi.outputs.all()[0].outer_input_id].value
            input_fold = self.parent.inputs[fi.outputs.all()[1].outer_input_id].value
            input_seed = self.parent.inputs[fi.outputs.all()[2].outer_input_id].value
            if input_fold != None:
                input_fold = int(input_fold)
            else:
                input_fold = 10

            if input_seed != None:
                input_seed = int(input_seed)
            else:
                input_seed = random.randint(0,10**9)

            input_type = input_list.__class__.__name__
            context = None
            if input_type == 'DBContext':
                context = input_list
                input_list = context.orng_tables.get(context.target_table,None)

            if not input_list:
                raise Exception('CrossValidation: Empty input list!')

            folds = []
            if hasattr(input_list, "get_items_ref"):
                import orange
                indices = orange.MakeRandomIndicesCV(input_list, randseed=input_seed, folds=input_fold, stratified=orange.MakeRandomIndices.Stratified)
                for i in range(input_fold):
                    output_train = input_list.select(indices, i, negate=1)
                    output_test = input_list.select(indices, i)
                    output_train.name = input_list.name
                    output_test.name = input_list.name
                    folds.append((output_train, output_test))
            else:
                rand.seed(input_seed)
                rand.shuffle(input_list)
                folds = [input_list[i::input_fold] for i in range(input_fold)]

            proper_output = fi.outputs.all()[2]
            proper_output.value = input_seed

            for i in range(len(folds)):
                #import pdb; pdb.set_trace()
                if hasattr(input_list, "get_items_ref"):
                    output_test = folds[i][1]
                    output_train = folds[i][0]
                else:
                    output_train = folds[:i] + folds[i+1:]
                    output_test = folds[i]
                if input_type == 'DBContext':
                    output_train_obj = context.copy()
                    output_train_obj.orng_tables[context.target_table] = output_train
                    output_test_obj = context.copy()
                    output_test_obj.orng_tables[context.target_table] = output_test
                    output_train = output_train_obj
                    output_test = output_test_obj

                self.cleanup()
                proper_output = fi.outputs.all()[0] # inner output
                proper_output.value = output_train
                proper_output = fi.outputs.all()[1] # inner output
                proper_output.value = output_test
                fi.finished=True # set the input widget as finished
                self.run_all_unfinished_widgets()
        else:
            self.run_all_unfinished_widgets()
        self.save()

    def save(self):
        for w in self.widgets:
            w.save_with_inputs_and_outputs(force_update=True)