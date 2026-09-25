from django.urls import path

from apps.surveys import views

urlpatterns = [
    path("surveys/", views.SurveyListView.as_view(), name="survey-list"),
    path(
        "surveys/close-expired/",
        views.SurveyCloseExpiredView.as_view(),
        name="survey-close-expired",
    ),
    path("surveys/<int:survey_id>/", views.SurveyDetailView.as_view(), name="survey-detail"),
    path(
        "surveys/<int:survey_id>/publish/", views.SurveyPublishView.as_view(), name="survey-publish"
    ),
    path("surveys/<int:survey_id>/close/", views.SurveyCloseView.as_view(), name="survey-close"),
    path(
        "surveys/<int:survey_id>/responses/",
        views.SurveyResponseView.as_view(),
        name="survey-respond",
    ),
    path(
        "surveys/<int:survey_id>/results/", views.SurveyResultsView.as_view(), name="survey-results"
    ),
    path("surveys/<int:survey_id>/files/", views.SurveyFilesView.as_view(), name="survey-files"),
]
