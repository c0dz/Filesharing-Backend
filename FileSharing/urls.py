from django.urls import path

from filesharing import views

urlpatterns = [
    path("upload/", views.FileUploadView.as_view(), name="upload"),
    path("fetch/", views.FileDataListView.as_view(), name="filedata-list"),
    path("delete/<file_id>/", views.DeleteFileView.as_view(), name="file-delete"),
    path("download/<file_id>/", views.DownloadFileView.as_view(), name="file-download"),
]
