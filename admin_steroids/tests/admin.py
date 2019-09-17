from django.contrib import admin

from admin_steroids.options import BetterRawIdFieldsModelAdmin
from admin_steroids.tests.models import Person


class PersonAdmin(BetterRawIdFieldsModelAdmin):

    list_display = ('name',)

    search_fields = ('name',)

    raw_id_fields = ('associates',)


admin.site.register(Person, PersonAdmin)
