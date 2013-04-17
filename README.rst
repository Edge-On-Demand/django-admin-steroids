=============================================================================
Django Admin Steroids - Tweaks and tools simplify Django admin configuration.
=============================================================================

Overview
--------

Django's admin supports a lot of customization. However, the current
implementation relies on the use of class value and methods, requiring a lot
of code duplication. This project contains classes, mixins, and a few templates
that improve the usability and maintainability of Django's admin.

Features
--------

Modeladmin mixins:

BetterRawIdFieldsAdmin - Adapted from a `Django Snippet
<http://djangosnippets.org/snippets/2217/>`_,
this formats all raw id fields with a convenient link to that record's
corresponding admin change page.

ReadonlyAdmin - Removes all editability from the modeladmin.

CSVAdmin - Adds a changelist action to export the selected records as a CSV.

Field formatters:

If you want to format a monetary dollar value with a dollar sign
and commas, you have to implement a myvariable_dollars() method in your
modeladmin class that returns the desired string, and then list this method
in the modeladmin's readonly_fields list.

In many non-trivial applications, I found myself writing a huge number of these
functions, most of which were nearly identical. So I decided to abstract this
functionality into a number of classes that could be instantiated and easily
plugged into a modeladmin.

Pre-built formatters include:

DollarFormat

PercentFormat

CenterFormat

NbspFormat

BooleanFormat

Formatters are used by wrapping them around field names in a modeladmin.::

    from admin_steroids.formatters import DollarFormat
    
    class BudgetAdmin(admin.ModelAdmin):
    
        fields = (
            'id',
            'name',
            DollarFormat('income'),
        )

Installation
------------

Install the package via pip with::

    pip install https://github.com/chrisspen/django-admin-steroids
    