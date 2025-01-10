from django.contrib import admin
from django.urls import path
from .views import *

urlpatterns = [
    path('', Dashboard.as_view(), name="dashboard"),
    path('login/', Login.as_view(), name="login"),
    path('logout/', Logout.as_view(), name="logout"),
]
