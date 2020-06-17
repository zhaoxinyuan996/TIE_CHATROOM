from django.shortcuts import render
from django.views.decorators.gzip import gzip_page


@gzip_page
def test(request):
    return render(request, 'test.html')