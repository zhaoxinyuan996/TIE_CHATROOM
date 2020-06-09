from django.conf.urls import url

from .views import *

urlpatterns = [
    url('chat', cli_accept)
]