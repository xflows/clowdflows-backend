import random

from Orange.data import Table
from django.db.models import Prefetch

from workflows.engine import ValueNotSet
from workflows.engine.widget_runner import WidgetRunner
from workflows.models import *
from collections import defaultdict
import sklearn.model_selection as skl

class WorkflowRunner():
    def __init__(self, workflow, final_widget=None, parent_workflow_runner=None,representing_widget=None): # clean=True,
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

        #self.clean = clean
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
            #if self.clean:
            if self.representing_widget or not w.save_results:
                w.finished = False
                for i in self.inputs_per_widget_id[w.id]:
                    if not i.parameter:
                        i.value = ValueNotSet
            w.error = False        

    def get_connections_for_output(self, output):
        return [c for c in self.connections if c.output_id==output.id]

    def get_connection_for_input(self,input):
        for c in self.connections:
            if c.input_id==input.id:
                return c
        return None

    def unfinished_widgets(self):
        unfinished_widgets = []
        for w in self.widgets:
            if not w.finished and not w.running and not w.error:
                unfinished_widgets.append(w)
        return unfinished_widgets

    def runnable_widgets(self):
        """ a widget is runnable if all widgets connected before
            it are finished (i.e. widgets that have outputs that 
            are connected to this widget's input) """

        # finished_widget_ids = [w.id for w in self.finished_widgets]
        runnable = []
        # ufw=self.unfinished_widgets
        for w in self.unfinished_widgets():
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
        runnable_widgets = self.runnable_widgets()
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
            runnable_widgets = self.runnable_widgets()

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
            outer_input_data = self.parent_workflow_runner.inputs[for_input_widget.outputs.all()[0].outer_input_id].value
            for i in outer_input_data:
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

            train_output, test_output, seed_output=self.outputs_per_widget_id[cv_input_widget.id]

            #GET INNER INPUTS
            #
            # !!!!
            # E.g., outer input for fold corresponds to inner output for the test fold
            # !!!!
            outer_input_data = self.parent_workflow_runner.input_id_to_input[train_output.outer_input_id].value
            outer_input_fold = self.parent_workflow_runner.input_id_to_input[test_output.outer_input_id].value
            outer_input_seed = self.parent_workflow_runner.input_id_to_input[seed_output.outer_input_id].value

            outer_input_fold = int(outer_input_fold) if outer_input_fold is not ValueNotSet else 10
            outer_input_seed = int(outer_input_seed) if outer_input_seed is not ValueNotSet else random.randint(0, 10**9)

            #proper_output = cv_input_widget.outputs.all()[2]
            seed_output.value = outer_input_seed

            input_type = outer_input_data.__class__.__name__
            if input_type == 'DBContext':
                context = outer_input_data
                outer_input_data = context.orng_tables.get(context.target_table, None)
            elif input_type == 'DocumentCorpus':
                document_corpus = outer_input_data
                outer_input_data = document_corpus.documents

            if not outer_input_data:
                raise Exception('CrossValidation: Empty input data!')


            #SPLIT INPUT DATA INTO FOLDS
            folds = []

            if input_type in {'Table', 'DBContext'}: #input_list is orange table
                indices = None
                if outer_input_data.domain.has_discrete_class:
                    try:
                        splitter = skl.StratifiedKFold(
                            outer_input_fold, shuffle=True, random_state=outer_input_seed
                        )
                        splitter.get_n_splits(outer_input_data.X, outer_input_data.Y)
                        self.indices = list(splitter.split(outer_input_data.X, outer_input_data.Y))
                    except ValueError:
                        self.warnings.append("Using non-stratified sampling.")
                        indices = None
                if indices is None:
                    splitter = skl.KFold(
                        outer_input_fold, shuffle=True, random_state=outer_input_seed
                    )
                    splitter.get_n_splits(outer_input_data)
                    indices = list(splitter.split(outer_input_data))

                for i in range(outer_input_fold):
                    output_train = Table.from_table_rows(outer_input_data,indices[i][0])
                    output_test = Table.from_table_rows(outer_input_data,indices[i][1])
                    output_train.name = outer_input_data.name
                    output_test.name = outer_input_data.name
                    folds.append((output_train, output_test))

            elif input_type == 'DocumentCorpus':
                from sklearn.model_selection import StratifiedKFold, KFold

                if 'Labels' in document_corpus.features:
                    labels = document_corpus.get_document_labels()
                    # print "Seed:"+str(input_seed)
                    stf = StratifiedKFold(labels, n_folds=outer_input_fold, random_state=outer_input_seed)
                else:
                    stf = KFold(len(document_corpus.documents), n_folds=outer_input_fold, random_state=outer_input_seed)

                folds = [(list(train_index), list(test_index)) for train_index, test_index in stf]
            else:
                random.seed(outer_input_seed)
                random.shuffle(outer_input_data)
                folds = [outer_input_data[i::outer_input_fold] for i in range(outer_input_fold)]

            for i in range(len(folds)):
                if input_type in {'Table', 'DBContext'}:
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

                train_output.value = output_train
                test_output.value = output_test

                for o in [train_output, test_output]:
                    for con in self.get_connections_for_output(o):
                        self.input_id_to_input[con.input_id].value = o.value

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