from django.db import models
from django.utils import timezone
from datetime import timedelta
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User
from django.conf import settings


class District(models.Model):
    code = models.CharField(max_length=3, primary_key=True, verbose_name=_("District Code"))
    name = models.CharField(max_length=50, unique=True, verbose_name=_("District Name"))

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Created By"
    )

    class Meta:
        verbose_name = _("District")
        verbose_name_plural = _("Districts")
        ordering = ['name']

    def __str__(self):
        return self.name


class Department(models.Model):
    code = models.CharField(max_length=10, primary_key=True, verbose_name=_("Department Code"))
    name = models.CharField(max_length=100, unique=True, verbose_name=_("Department Name"))
    district = models.ForeignKey(District, on_delete=models.CASCADE, verbose_name=_("Department District"))

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Created By"
    )

    class Meta:
        verbose_name = _("Department")
        verbose_name_plural = _("Departments")
        ordering = ['name']
    
    def __str__(self):
        return self.name
