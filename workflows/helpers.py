import os
from mothra.local_settings import FILES_FOLDER
from workflows.models import Input,Output


def ensure_dir(f):
    d = os.path.dirname(f)
    if not os.path.exists(d):
        os.makedirs(d)

def safeOpen(filename):
    if filename.startswith(FILES_FOLDER):
        if filename.find("..")==-1:
            return open(filename,'r')
        else:
            raise Exception("Invalid filename")
    else:
        raise Exception("Invalid filename.")



def fix_inputs_and_outputs_without_abstract_ids():
    '''finds inputs and outputs which have blank abstract_input(output)_ids and sets it by finding the appropriate
    abstract_widget's inputs/output through variable'''

    for input in Input.objects.filter(widget__type='regular',abstract_input_id=None).defer('value')\
            .prefetch_related('widget','widget__abstract_widget','widget__abstract_widget__inputs').all():
        abstract_inputs=input.widget.abstract_widget.inputs.all()
        abstract_input=[ai for ai in abstract_inputs if ai.variable==input.variable][0]
        input.abstract_input=abstract_input
        input.save()

    for output in Output.objects.filter(widget__type='regular',abstract_output_id=None).defer('value')\
            .prefetch_related('widget','widget__abstract_widget','widget__abstract_widget__outputs').all():
        abstract_outputs=output.widget.abstract_widget.outputs.all()
        abstract_output=[ai for ai in abstract_outputs if ai.variable==output.variable][0]
        output.abstract_output=abstract_output
        output.save()
