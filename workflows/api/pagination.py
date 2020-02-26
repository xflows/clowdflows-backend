from rest_framework.pagination import PageNumberPagination, LimitOffsetPagination
from rest_framework.response import Response
import math

# TODO Return all workflows if page is not specified
class WorkflowPagination(PageNumberPagination):
    page_size = 5
    page_size_query_param = 'page_size'

    # Return unpaginated response if page is not specified
    def paginate_queryset(self, queryset, request, view=None):
        if request.GET.get('page'):
            return super().paginate_queryset(queryset, request, view)
        else:
            return None

    def get_paginated_response(self, data):
        print(self.page.number)
        print(self.page.start_index())
        return Response({
            'pagination': {
                'next': self.get_next_link(),
                'previous': self.get_previous_link(),
                'count': self.page.paginator.count,
                'num_pages': self.page.paginator.num_pages,
                'page_number': self.page.number,
                'page_start': self.page.start_index(),
                'page_end': self.page.end_index(),
                'page_size': len(data),
            },   
            'workflows': data
        })
