from django.core.management.base import BaseCommand
from workflows.models import *


class Command(BaseCommand):
    help = 'This command updates the recommendations in the database.'

    def handle(self, *args, **options):
        recomm_for_abstract_output_id, recomm_for_abstract_input_id = Recommender.calculate_recommendations()
        Recommender.save_recommendations(recomm_for_abstract_output_id, recomm_for_abstract_input_id)
        print "Succesfully calculated and saved recommendations."
