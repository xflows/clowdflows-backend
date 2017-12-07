from workflows.engine import ValueNotSet
from workflows.helpers import safeOpen
import json
import sys

from workflows import module_importer
def setattr_local(name, value, package):
    setattr(sys.modules[__name__], name, value)
module_importer.import_all_packages_libs("library",setattr_local)

def test_interaction(input_dict):
    return input_dict

def add_multiple(input_dict):
    output_dict = {}
    output_dict['sum'] = 0
    for i in input_dict['integer']:
        output_dict['sum'] = float(i)+output_dict['sum']
    return output_dict

def load_file(input_dict):
    return input_dict
    
def file_to_string(input_dict):
    f = safeOpen(input_dict['file'])
    output_dict = {}
    output_dict['string']=f.read()
    return output_dict

def load_to_string(input_dict):
    '''
    Opens the file and reads its contents into a string.
    '''
    f = safeOpen(input_dict['file'])
    output_dict = {}
    output_dict['string']=f.read()
    return output_dict

def call_webservice(input_dict):
    from services.webservice import WebService
    ws = WebService(input_dict['wsdl'],float(input_dict['timeout']))
    selected_method = {}
    for method in ws.methods:
        if method['name']==input_dict['wsdl_method']:
            selected_method = method
    function_to_call = getattr(ws.client,selected_method['name'])
    ws_dict = {}
    for i in selected_method['inputs']:
        try:
            ws_dict[i['name']]=input_dict[i['name']]
            if ws_dict[i['name']] == ValueNotSet:
                ws_dict[i['name']] = None
            if ws_dict[i['name']] is None:
                pass
            if i['type'] == bool:
                if input_dict[i['name']]=="true":
                    ws_dict[i['name']]=1
                else:
                    ws_dict[i['name']]=0
            if ws_dict[i['name']] == '':
                if input_dict['sendemptystrings']=="true":
                    ws_dict[i['name']] = ''
                else:
                    ws_dict.pop(i['name'])
        except Exception as e: 
            print(e)
            ws_dict[i['name']]=''
    results = function_to_call(**ws_dict)
    output_dict=results
    if type(results)==dict:
        return output_dict
    elif type(results)==list:
        output_dict = {}
        for l in results:
            if type(l)==dict:
                for k in l.keys():
                    a = output_dict.get(k,[])
                    a.append(l[k])
                    output_dict[k]=a
        return output_dict
    return results

def multiply_integers(input_dict):
    product = 1
    for i in input_dict['integers']:
        product = product*int(i)
    output_dict={'integer':product}
    return output_dict

def filter_integers(input_dict):
    return input_dict
    
def filter_integers_post(postdata,input_dict,output_dict):
    try:
        output_dict['integers'] = postdata['integer']
    except:
        pass
    return output_dict

def create_integer(input_dict):
    output_dict = {}
    output_dict['integer'] = input_dict['integer']
    return output_dict
    
def create_string(input_dict):
    return input_dict  
    
def concatenate_strings(input_dict):
    output_dict = {}
    j = len(input_dict['strings'])
    for i in range(j):
        input_dict['strings'][i]=str(input_dict['strings'][i])
    output_dict['string'] = input_dict['delimiter'].join(input_dict['strings'])
    return output_dict
    
def display_string(input_dict):
    return {}

def add_integers(input_dict):
    output_dict = {}
    output_dict['integer'] = int(input_dict['integer1'])+int(input_dict['integer2'])
    return output_dict

def object_viewer(input_dict):
    return {}

def table_viewer(input_dict):
    return {}

def subtract_integers(input_dict):
    output_dict = {}
    output_dict['integer'] = int(input_dict['integer1'])-int(input_dict['integer2'])
    return output_dict
    
def select_attrs(input_dict):
    return input_dict


def select_data(input_dict):
    return input_dict


def string_to_file(input_dict):
    return {}

def alter_table(input_dict):
    return {'altered_data' : None}

def tree_visualization(input_dict):
    return{}

def example_distance(input_dict):
    return input_dict

def example_distance_post(postdata, input_dict, output_dict):
    return{}


import hashlib

def hash_it(input_dict):
   output_dict = {}
   output_dict["output1"] = hashlib.sha256(input_dict["input1"]).hexdigest()
   output_dict["numLoop"] = input_dict["numLoop"]
   for i in range(1,input_dict["numLoop"]):
       output_dict["output1"] = hashlib.sha256(output_dict["output1"]).hexdigest();
   return output_dict
   