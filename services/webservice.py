import pysimplesoap
from pysimplesoap.client import SoapClient

        
class WebService:
    def __init__(self, wsdl_url, timeout=60):
        pysimplesoap.client.TIMEOUT = timeout
        self.client = SoapClient(wsdl=wsdl_url,trace=False)
        self.wsdl_url = wsdl_url
        self.name = wsdl_url
        self.methods = []
        for service in self.client.services.values():
            for port in service['ports'].values():
                for op in port['operations'].values():
                    method = {}
                    try:
                        method['documentation']=op['documentation']
                    except:
                        method['documentation']="No documentation provided."
                    method['name']=op['name']
                    method['inputs']=[]
                    method['outputs']=[]
                    try:
                        input_dict = list(op['input'].values())[0]
                    except:
                        input_dict = []
                    for i in input_dict:
                        input = {}
                        input['name']=i
                        input['type']=input_dict[i]
                        method['inputs'].append(input)
                    try:
                        output_dict = list(op['output'].values())[0]
                    except:
                        output_dict = [[]]
                    if type(output_dict)==type([]):
                        output_dict = output_dict[0]
                    for o in output_dict:
                        output = {}
                        output['name']=o
                        method['outputs'].append(output)
                    self.methods.append(method)
    def __unicode__(self):
        return self.wsdl_url
    def __str__(self):
        return self.wsdl_url