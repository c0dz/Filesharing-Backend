from django.urls import path

from filesharing import views

urlpatterns = [
    path("upload/", views.FileUploadView.as_view(), name="upload"),
]
