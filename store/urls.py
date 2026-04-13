from django.urls import path
from django.views.generic import RedirectView

from . import views


urlpatterns = [
    path("mock-tests/", views.mocktest_hub, name="mocktest_hub"),
    path("mock-tests/dashboard/", views.mocktest_dashboard, name="mocktest_dashboard"),
    path("mock-tests/start/<slug:slug>/", views.mocktest_start, name="mocktest_start"),
    path("mock-tests/attempt/<int:attempt_id>/", views.mocktest_take, name="mocktest_take"),
    path("mock-tests/result/<int:attempt_id>/", views.mocktest_result, name="mocktest_result"),
    path("mock-tests/revision/<int:entry_id>/done/", views.mocktest_revision_done, name="mocktest_revision_done"),
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
