def base_workflows_url(request):
    return {
        'base_workflows_url': request.build_absolute_uri('/workflows'),
        'base_url': request.build_absolute_uri('/')[:-1]
    }