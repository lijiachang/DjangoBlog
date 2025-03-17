from django.shortcuts import render

# Create your views here.
# amd_cpu/views.py
from django.shortcuts import render
from .services import AMDCPUService


def amd_search_view(request):
    search_term = request.GET.get('q', '')
    search_results = []

    if search_term:
        search_results = AMDCPUService.search_cpus(search_term)

    return render(request, 'amd_cpu/search.html', {
        'search_term': search_term,
        'search_results': search_results,
    })