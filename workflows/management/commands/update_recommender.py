from django.core.management.base import BaseCommand
from workflows.models import *

class Command(BaseCommand):
    help = 'This command updates the recommendations in the database.'

    def handle(self, *args, **options):
        d={}
        for c0 in Connection.objects.all():
            # ===========================================
            minp = Input.objects.get(pk=c0.input_id)

            var_name = minp.variable
            mw1 = minp.widget       # only one
            maw = mw1.abstract_widget
            if not maw:  # Skip widgets with no abstract widgets
                continue

            mai = AbstractInput.objects.filter(widget=maw.id, variable=var_name)
            mai = mai[0]            

            # ===========================================
            mout = Output.objects.get(pk=c0.output_id)

            var_name = mout.variable
            mw2 = mout.widget       # only one
            maw = mw2.abstract_widget
            if not maw:  # Skip widgets with no abstract widgets
                continue
                
            mao = AbstractOutput.objects.filter(widget=maw.id, variable=var_name)
            mao = mao[0]
            if not mw1.error and not mw2.error:
                k=(mai.id,mao.id)
                if d.has_key(k):
                    d[k] = d[k] + 1
                else:
                    d[k] = 1
        
        # Delete all Recommender objects and re-create them
        Recommender.objects.all().delete()
        for (id_inp,id_out) in d.keys():
            r = Recommender()
            r.inp = AbstractInput.objects.get(pk=id_inp)
            r.out = AbstractOutput.objects.get(pk=id_out)
            r.count = d[ (id_inp,id_out) ]
            r.save()

        print "Succesfully inserted %d recommendations." % len(d.keys())
