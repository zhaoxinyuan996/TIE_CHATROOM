from django.conf.urls import url

from .views import *

urlpatterns = [
    url(r'page_num$', page_num),
    url(r'page$', page),
    
]