import sys
from django.shortcuts import render

from workflows import module_importer
def setattr_local(name, value, package):
    setattr(sys.modules[__name__], name, value)
module_importer.import_all_packages_libs("interaction_views",setattr_local)

def test_interaction(request,input_dict,output_dict,widget):
    return render(request, 'interactions/test_interaction.html',{'widget':widget})

def core_filter_integers(request,input_dict,output_dict,widget): #todo move to cf_core
    return render(request, 'interactions/filter_integers.html',{'widget':widget,'integers':input_dict['integers']})
    
