from django.urls import path

from . import views


urlpatterns = [
    path("dictionary/", views.dictionary_list, name="dictionary_list"),
    path("dictionary/<slug:slug>/", views.dictionary_detail, name="dictionary_detail"),
]
