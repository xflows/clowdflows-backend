import random

from Orange.data import Table
from django.db.models import Prefetch

from workflows.engine import ValueNotSet
from workflows.engine.widget_runner import WidgetRunner
from workflows.models import *
from collections import defaultdict
import sklearn.model_selection as skl

class WorkflowRunner():
    def __init__(self, workflow, final_widget=None, clean=True, parent_workflow_runner=None,representing_widget=None):
        self.workflow = workflow
        self.connections = workflow.connections.all()
        self.widgets = workflow.get_runnable_widgets(last_runnable_widget_id=final_widget and final_widget.id)

        #used for storing results
        self.input_id_to_input= {}
        self.output_id_to_output= {}

        #used for discovery of connections
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
                if not (w.save_results and w.finished):
                    o.value=ValueNotSet
                self.output_id_to_output[o.id] = o
                self.outputs_per_widget_id[w.id].append(o)

        #preassing input values
        relevant_input_ids=set()
        for w in self.widgets:
            relevant_input_ids.update([i.id for i in self.inputs_per_widget_id[w.id]])
        for c in self.connections:
            if c.input_id in relevant_input_ids:
                self.input_id_to_input[c.input_id].value=self.output_id_to_output[c.output_id].value

        self.clean = clean
        self.parent_workflow_runner = parent_workflow_runner
        self.representing_widget = representing_widget

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

    def get_connections_for_output(self, output):
        return [c for c in self.connections if c.output_id==output.id]

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
        # ufw=self.unfinished_widgets
        for w in self.unfinished_widgets:
            incoming_widget_connections= [c for c in self.connections if self.input_id_to_input[c.input_id].widget_id == w.id]
            # incoming_widget_connection_inputs=[self.input_id_to_input[c.input_id].value for c in incoming_widget_connections]
            # widget_connections= [c for c in self.connections if c.input_id in self.inputs_per_widget_id]

            #check if all outputs are connection outputs are calculated
            # c.output_id in self.outputs and
            # if all([self.output_id_to_output[c.output_id].value!=ValueNotSet for c in widget_connections]):
            #     runnable.append(w)
            if not any([self.input_id_to_input[c.input_id].value is ValueNotSet for c in incoming_widget_connections]):
                runnable.append(w)
        return runnable

    def run_all_unfinished_widgets(self):
        runnable_widgets = self.runnable_widgets
        while len(runnable_widgets)>0:
            print(runnable_widgets)

            for w in runnable_widgets:
                try:
                    if w.type == 'subprocess':
                        WorkflowRunner(w.workflow_link, parent_workflow_runner=self,representing_widget=w).run()
                    else:
                        WidgetRunner(w,self.inputs_per_widget_id[w.id],self.outputs_per_widget_id[w.id],self).run()
                except NotImplementedError as c:
                    w.set_as_faulty()
                    self.save()
                    raise c
            runnable_widgets = self.runnable_widgets

    def run(self):
        self.cleanup()
        if self.is_for_loop():
            for_input_widget = None
            for_output_widget = None
            for w in self.widgets:
                if w.type=='for_input':
                    for_input_widget = w
                if w.type=='for_output':
                    for_output_widget = w
            outer_output = self.parent_workflow_runner.outputs[for_output_widget.inputs.all()[0].outer_output_id]
            outer_output.value = []
            input_list = self.parent_workflow_runner.inputs[for_input_widget.outputs.all()[0].outer_input_id].value
            for i in input_list:
                self.cleanup()
                proper_output = for_input_widget.outputs.all()[0]
                proper_output.value = i
                for_input_widget.finished = True
                self.run_all_unfinished_widgets()
        elif self.is_cross_validation():
            cv_input_widget = None
            cv_output_widget = None
            for w in self.widgets:
                if w.type=='cv_input':
                    cv_input_widget = w
                if w.type=='cv_output':
                    cv_output_widget = w

            outer_output = self.parent_workflow_runner.output_id_to_output[self.inputs_per_widget_id[cv_output_widget.id][0].outer_output_id]
            outer_output.value = []

            list_output,fold_output,seed_output=self.outputs_per_widget_id[cv_input_widget.id]

            #input_list = self.parent_workflow_runner.inputs[cv_input_widget.outputs.all()[0].outer_input_id].value
            #input_fold = self.parent_workflow_runner.inputs[cv_input_widget.outputs.all()[1].outer_input_id].value
            #input_seed = self.parent_workflow_runner.inputs[cv_input_widget.outputs.all()[2].outer_input_id].value

            #GET INNER INPUTS
            input_list = self.parent_workflow_runner.input_id_to_input[list_output.outer_input_id].value
            input_fold = self.parent_workflow_runner.input_id_to_input[fold_output.outer_input_id].value
            input_seed = self.parent_workflow_runner.input_id_to_input[seed_output.outer_input_id].value
            if input_fold is not ValueNotSet:
                input_fold = int(input_fold)
            else:
                input_fold = 10

            if input_seed is not ValueNotSet:
                input_seed = int(input_seed)
            else:
                input_seed = random.randint(0,10**9)
            proper_output = cv_input_widget.outputs.all()[2]
            proper_output.value = input_seed



            input_type = input_list.__class__.__name__
            context = None
            if input_type == 'DBContext':
                context = input_list
                input_list = context.orng_tables.get(context.target_table,None)
            elif input_type == 'DocumentCorpus':
                document_corpus = input_list
                input_list = document_corpus.documents

            if not input_list:
                raise Exception('CrossValidation: Empty input list!')


            #SPLIT INPUT DATA INTO FOLDS
            folds = []

            if input_type == 'Table': #input_list is orange table
                indices = None
                if input_list.domain.has_discrete_class:
                    try:
                        splitter = skl.StratifiedKFold(
                            input_fold, shuffle=True, random_state=input_seed
                        )
                        splitter.get_n_splits(input_list.X, input_list.Y)
                        self.indices = list(splitter.split(input_list.X, input_list.Y))
                    except ValueError:
                        self.warnings.append("Using non-stratified sampling.")
                        indices = None
                    if indices is None:
                        splitter = skl.KFold(
                            input_fold, shuffle=True, random_state=input_seed
                        )
                        splitter.get_n_splits(input_list)
                        indices = list(splitter.split(input_list))

                for i in range(input_fold):
                    output_train = Table.from_table_rows(input_list,indices[i][0])
                    output_test = Table.from_table_rows(input_list,indices[i][1])
                    output_train.name = input_list.name
                    output_test.name = input_list.name
                    folds.append((output_train, output_test))

            elif input_type == 'DocumentCorpus':
                from sklearn.model_selection import StratifiedKFold, KFold

                if 'Labels' in document_corpus.features:
                    labels = document_corpus.get_document_labels()
                    # print "Seed:"+str(input_seed)
                    stf = StratifiedKFold(labels, n_folds=input_fold, random_state=input_seed)
                else:
                    stf = KFold(len(document_corpus.documents), n_folds=input_fold, random_state=input_seed)

                folds = [(list(train_index), list(test_index)) for train_index, test_index in stf]
            else:
                random.seed(input_seed)
                random.shuffle(input_list)
                folds = [input_list[i::input_fold] for i in range(input_fold)]







            for i in range(len(folds)):
                if input_type == 'Table':
                    output_test = folds[i][1]
                    output_train = folds[i][0]
                elif input_type == 'DocumentCorpus':
                    train_indices, test_indices= folds[i]
                    print("engine")
                    print("TRAIN:", train_indices, "TEST:", test_indices)

                    output_train, output_test = document_corpus.split(train_indices,test_indices)
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

                #proper_output = cv_input_widget.outputs.all()[0] # inner output
                #proper_output.value = output_train
                #proper_output = cv_input_widget.outputs.all()[1] # inner output
                #proper_output.value = output_test
                cv_input_widget.finished=True # set the input widget as finished
                self.run_all_unfinished_widgets()
        else:
            self.run_all_unfinished_widgets()
        self.save()

        if self.representing_widget:
            self.representing_widget.set_as_finished()

    def save(self):
        for w in self.widgets:
            w.save_with_inputs_and_outputs(force_update=True,
                inputs=w.save_results and [self.input_id_to_input[i.id] for i in self.inputs_per_widget_id[w.id]],
                outputs=w.save_results and [self.output_id_to_output[i.id] for i in self.outputs_per_widget_id[w.id]])