from django.shortcuts import render
from django.views.decorators.gzip import gzip_page


from libs.cls import gzip_response


@gzip_page
def get_index(request):
    return render(request, 'index.html')

@gzip_page
def get_chatroom(request):
    return render(request, 'chatroom.html')

@gzip_response
def get_static(request):
    pass