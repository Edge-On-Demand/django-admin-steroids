=============================================================================
Django Admin Steroids - Tweaks and tools to simplify Django admin
=============================================================================

Overview
--------

Django's admin supports a lot of customization. However, the current
implementation relies on the use of class value and methods, requiring a lot
of code duplication. This project contains classes, mixins, and a few templates
that improve the usability and maintainability of Django's admin.

Features
--------

ModelAdmin mixins:

- ReadonlyModelAdmin - Removes all editability from the ModelAdmin.

- CSVModelAdmin - Adds a changelist action to export the selected records as a CSV.

- FormatterModelAdmin - Allows the use of admin field formatters.

- BetterRawIdFieldsModelAdmin - Adapted from a `Django Snippet
  <http://djangosnippets.org/snippets/2217/>`_,
  this formats all raw id fields with a convenient link to that record's
  corresponding admin change page.

Field formatters:

If you want to format a monetary dollar value with a dollar sign
and commas, you have to implement a myvariable_dollars() method in your
ModelAdmin class that returns the desired string, and then list this method
in the ModelAdmin's readonly_fields list.

In many non-trivial applications, I found myself writing a huge number of these
functions, most of which were nearly identical. So I decided to abstract this
functionality into a number of classes that could be instantiated and easily
plugged into a ModelAdmin.

Pre-built formatters include:

- DollarFormat

- PercentFormat

- CenterFormat

- NbspFormat

- BooleanFormat

- ForeignKeyLink

- OneToManyLink

Formatters are used by wrapping them around field names in a ModelAdmin.
Say you have a model with a field called `income` that you want to display in
admin formatted with a dollar sign. Normally, you'd do something like this::

    class BudgetAdmin(admin.ModelAdmin):
    
        fields = (
            'id',
            'name',
            'income_str',
        )
        
        readonly_fields = (
            'income_str',
        )
        
        def income_str(self, request, obj=None):
            if obj is None:
                return
            return '$%.2f' % obj.income

Formatters simply this process. In this example, you could use the DollarFormat
class to accomplish the same thing with much less code::

    from admin_steroids import FormatterModelAdmin
    from admin_steroids.formatters import DollarFormat
    
    class BudgetAdmin(FormatterModelAdmin):
    
        fields = (
            'id',
            'name',
            DollarFormat('income', decimals=2),
        )

Installation
------------

Install the package via pip with::

    pip install https://github.com/chrisspen/django-admin-steroids
    