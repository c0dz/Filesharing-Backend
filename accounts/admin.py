from django.contrib import admin

# Register your models here.

from .models import UserModel, VerificationModel

admin.site.register(UserModel)
admin.site.register(VerificationModel)
