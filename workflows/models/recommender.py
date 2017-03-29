from django.db import models
from django.db.models import Count

from workflows.models import AbstractInput, Connection, Input, Output
from workflows.models import AbstractOutput
from collections import defaultdict


class Recommender(models.Model):
    abstract_input = models.ForeignKey(AbstractInput, related_name='recommender')
    abstract_output = models.ForeignKey(AbstractOutput, related_name='recommender')
    count = models.IntegerField()

    @staticmethod
    def load_recommendations():
        recomm_for_abstract_output_id = defaultdict(list)
        recomm_for_abstract_input_id = defaultdict(list)

        for r in Recommender.objects.all():
            recomm_for_abstract_input_id[r.abstract_input_id].append(r.abstract_output_id)
            recomm_for_abstract_output_id[r.abstract_output_id].append(r.abstract_input_id)

        return recomm_for_abstract_output_id, recomm_for_abstract_input_id

    @staticmethod
    def calculate_recommendations():
        recommendations = 2

        recomm_for_abstract_output_id = defaultdict(list)
        recomm_for_abstract_input_id = defaultdict(list)

        for d in Connection.objects.filter(input__widget__type='regular', input__widget__finished=True,
                                           output__widget__type='regular', output__widget__finished=True) \
                .values('input__abstract_input_id', 'output__abstract_output_id') \
                .annotate(count=Count('id')).filter(count__gte=recommendations).order_by('-count'):
            abs_input_id, abs_output_id = d['input__abstract_input_id'], d['output__abstract_output_id']

            recomm_for_abstract_output_id[abs_output_id].append((abs_input_id, d['count']))
            recomm_for_abstract_input_id[abs_input_id].append((abs_output_id, d['count']))

        return recomm_for_abstract_output_id, recomm_for_abstract_input_id

    @staticmethod
    def save_recommendations(recomm_for_abstract_output_id, recomm_for_abstract_input_id):
        # Delete all Recommender objects and re-create them
        Recommender.objects.all().delete()

        for abstract_output_id, most_connected_ids_with_counts in recomm_for_abstract_output_id.items():
            for abstract_input_id, count in most_connected_ids_with_counts:
                Recommender(abstract_input_id=abstract_input_id, abstract_output_id=abstract_output_id,
                            count=count).save()

                # Currently not in use
                # for abstract_input_id, most_connected_ids_with_counts in recomm_for_abstract_input_id.items():
                #     for abstract_output_id, count in most_connected_ids_with_counts:
                #         Recommender(abstract_input_id=abstract_input_id, abstract_output_id=abstract_output_id,count=count).save()
