import sys
import socket
from django.core.management.base import NoArgsCommand
from workflows.models import *
import sqlite3 as lite

class Command(NoArgsCommand):
    help = 'This command updates the recommendations in the database.'
    option_list = NoArgsCommand.option_list

    def handle_noargs(self, **options):
        """ Look for DB settings in local_settings file """
        try:
            from mothra.local_settings import DATABASES
        except ImportError:
            raise Exception('Problem looking up [local_settings]')
        
        """ Execute complex query (either sqlite or mysql) """
        if 'sqlite' in DATABASES['default']['ENGINE']:
            # SQLITE3, probably local installation...
            import sqlite3 as lite
            try:
                con = lite.connect(DATABASES['default']['NAME'])
            except Exception,e:
                raise Exception('Problem connecting to the database.')
            query = 'select wao.id as idout, wai.id as idinp, wao."variable" as w1,  wo."variable" as w1var, wai."variable" as w2,  wi."variable" as w2var from workflows_connection wc, workflows_input wi, workflows_output wo, workflows_widget ww1, workflows_widget ww2, workflows_abstractwidget waw1, workflows_abstractwidget waw2, workflows_abstractoutput wao, workflows_abstractinput wai where      wc.input_id = wi.id and wc.output_id = wo.id and wo.widget_id = ww1.id and wi.widget_id = ww2.id and ww1.abstract_widget_id = waw1.id and ww2.abstract_widget_id = waw2.id and waw1.id = wao.widget_id and waw2.id = wai.widget_id and ww1.error = 0 and  ww2.error = 0 and wo."variable" = wao."variable" and wi."variable" = wai."variable"'

        else:
            # MYSQL
            import MySQLdb
            try:
                # con = MySQLdb.connect("localhost","workflows","","workflows" )
                con = MySQLdb.connect(DATABASES['default']['HOST'], DATABASES['default']['USER'], DATABASES['default']['PASSWORD'], DATABASES['default']['NAME'])
            except Exception,e:
                raise Exception('Problem connecting to the database.')
            query = 'select wao.id as idout,wai.id as idinp, wao.variable as w1, wo.variable as w1var, wai.variable as w2, wi.variable as w2var from workflows_connection wc, workflows_input wi, workflows_output wo,workflows_widget ww1,workflows_widget ww2,workflows_abstractwidget waw1,workflows_abstractwidget waw2,workflows_abstractoutput wao,workflows_abstractinput wai where wc.input_id = wi.id and  wc.output_id = wo.id and  wo.widget_id = ww1.id and wi.widget_id = ww2.id and ww1.abstract_widget_id = waw1.id and ww2.abstract_widget_id = waw2.id and waw1.id = wao.widget_id and waw2.id = wai.widget_id and ww1.error = 0 and ww2.error = 0 and wo.variable = wao.variable and wi.variable = wai.variable;'

        mdict_oi={}     # keys: "outputId_inputId"; ex: mdict_oi["1_4"]=count
        mdict_io={}     
        output_ids = []
        input_ids = []

        """ Create a dictionary from the query results """
        with con:
            ids=[]
            cur=con.cursor()    
                
            cur.execute(query)                                  # sqlite3 or mysql

            i=0
            for item in cur.fetchall():
                # print( ""+ str(item[0])+", "+str(item[1]) )     # idout, idinp
                mkey=str(item[0])+"_"+str(item[1]);             # direction: out->inp
                output_ids.append(item[0])

                if mdict_oi.__contains__(mkey):
                    val = mdict_oi[mkey]
                    val = val + 1
                    mdict_oi[mkey] = val
                else:
                    mdict_oi[mkey] = 1

                mkey=str(item[1])+"_"+str(item[0]);             # direction: inp->out
                input_ids.append(item[1])
                if mdict_io.__contains__(mkey):
                    val = mdict_io[mkey]
                    val = val + 1
                    mdict_io[mkey] = val
                else:
                    mdict_io[mkey] = 1

                i=i+1

            self.stdout.write('The query has produced a total of %d DB records.\n' % i)
        con.close()

        # =================================================================
        self.stdout.write('Now will try to insert %d elems in DB.\n' % len(mdict_oi.keys()))

        for mkey in mdict_oi.keys():
            id_out,id_inp = mkey.split("_")
            id_out = int(id_out)
            id_inp = int(id_inp)

            """ check if that particular recommender already exists in the DB """
            my_inp = AbstractInput.objects.get(pk=id_inp)
            my_out = AbstractOutput.objects.get(pk=id_out)

            r_objs = Recommender.objects.filter(inp=my_inp, out=my_out)

            if r_objs.count() == 0:
                r = Recommender()
                r.inp = my_inp
                r.out = my_out
                self.stdout.write('  :: Recommender(out=%d, inp=%d): not in DB.\n' % (id_out, id_inp))
            else:
                r = r_objs[0]
                self.stdout.write('  :: Recommender(out=%d, inp=%d): already in DB, just updating the count.\n' % (id_out, id_inp))

            r.count = mdict_oi[mkey]
            r.save()
