from django.urls import path
from django.views.generic import RedirectView

from . import views


urlpatterns = [
    path("unanidictionary/", views.dictionary_list, name="dictionary_list"),
    path("dictionary/unaniweight-converter/", views.unani_weight_converter, name="unani_weight_converter"),
    path("dictionary/<slug:slug>/", views.dictionary_detail, name="dictionary_detail"),
    path(
        "dictionary/",
        RedirectView.as_view(pattern_name="dictionary_list", permanent=True),
    ),
    path(
        "dictionary/weight-converter/",
        RedirectView.as_view(pattern_name="unani_weight_converter", permanent=True),
    ),
]
