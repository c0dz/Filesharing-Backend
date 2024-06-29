from django.contrib import admin

from filesharing.models import FileModel, FilePermissionModel

admin.site.register(FileModel)
admin.site.register(FilePermissionModel)
