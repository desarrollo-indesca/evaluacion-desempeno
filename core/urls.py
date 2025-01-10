from django.contrib.auth.views import LogoutView
from django.urls import path
from .views import *

urlpatterns = [
    path('', Dashboard.as_view(), name="dashboard"),
    path('login/', Login.as_view(), name="login"),
    path('logout/', LogoutView.as_view(next_page="/"), name="logout"),
]
