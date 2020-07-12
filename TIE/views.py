from django.shortcuts import render
from django.views.decorators.gzip import gzip_page
from django.views.decorators.clickjacking import xframe_options_exempt


from libs.cls import gzip_response


@gzip_page
def get_index(request):
    return render(request, 'index.html')

@gzip_page
@xframe_options_exempt
def get_chatroom(request):
    return render(request, 'chatroom.html')

@gzip_response
def get_static(request):
    pass