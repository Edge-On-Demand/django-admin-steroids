Django Admin Steroids - Tweaks and tools to extend Django admin
===============================================================

[![](https://img.shields.io/pypi/v/django-admin-steroids.svg)](https://pypi.python.org/pypi/django-admin-steroids)
[![Pipeline Status](https://gitlab.com/chrisspen/django-admin-steroids/badges/master/pipeline.svg)](https://gitlab.com/chrisspen/django-admin-steroids/commits/master) 

Overview
--------

Django's admin supports a lot of customization. However, the current
implementation relies on the use of class values and methods, requiring a lot
of code duplication. This project contains classes, mixins, and a few templates
that improve the usability and maintainability of Django's admin, and implement
some missing features.

Features
--------

**ModelAdmin mixins:**

- ReadonlyModelAdmin - Removes all editability from the ModelAdmin.

- CSVModelAdmin - Adds a changelist action to export the selected records as a CSV.

- FormatterModelAdmin - Allows the use of admin field formatters.

- BetterRawIdFieldsModelAdmin - Adapted from a `Django Snippet
  <http://djangosnippets.org/snippets/2217/>`_,
  this formats all raw id fields with a convenient link to that record's
  corresponding admin change page.

**Field formatters:**

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
admin formatted with a dollar sign. Normally, you'd do something like this:

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
class to accomplish the same thing with much less code:

    from admin_steroids import FormatterModelAdmin
    from admin_steroids.formatters import DollarFormat
    
    class BudgetAdmin(FormatterModelAdmin):
    
        fields = (
            'id',
            'name',
            DollarFormat('income', decimals=2),
        )

**Ajax list filters:**

Django's default admin list filters don't allow selecting multiple values
for a field, nor do they handle fields with large numbers of values.
Fields render **all** values in a list or select drop-down, slowing down page
load and wasting screen space.

I've implemented a custom AjaxFieldFilter which allows you to search for one
or more values via an Ajax-powered search bar, so admin still renders quickly
while the user is still able to search for any value used by the field.

In your admin, add the AjaxFieldFilter like:

    from django.contrib import admin
    from admin_steroids.filters import AjaxFieldFilter
    import models
    
    class MyModelAdmin(admin.ModelAdmin):
    
        list_filters = (
            ('myfield', AjaxFieldFilter),
        )
        
    admin.site.register(models.MyModel, MyModelAdmin)

Then, in your settings.py, add 'admin_steroids' to your `INSTALLED_APPS`, and flag your field as safe to search:

    INSTALLED_APPS = [
        ...,
        'admin_steroids',
    ]

    DAS_ALLOWED_AJAX_SEARCH_PATHS = [
        ('myapp', 'mymodel', 'myfield'),
    ]
    
    DAS_AJAX_SEARCH_PATH_FIELDS = {
        # This assumed "myfield" a ForeignKey, pointing to a model that has
        # a "name" and "slug" field you want to search.
        # If "myfield" is a simple CharField, you don't need to specify
        # anything here.
        ('myapp', 'mymodel', 'myfield'): ('name', 'slug'),
    }

Finally, add admin_steroids to your urls.py to expose the Ajax search URLs,
which by default will be rendered in the form `/admin/<app>/<model>/field/<field>/search`:

    urlpatterns = patterns('',
        ...
    
        # Should go before the actual admin, so it won't be overridden.
        (r'^admin/', include('admin_steroids.urls')),
        
        (r'^admin/', include(admin.site.urls)),
        
        ...
    )

You can override these URLs by excluding the URL include above and specifying
your own pattern pointing to admin_steroids.views.ModelFieldSearchView.

See admin_steroids.urls for an example.

Installation
------------

Install the package via pip with:

    pip install django-admin-steroids

Development
-----------

Tests require the Python development headers to be installed, which you can install on Ubuntu
using the [Dead Snakes PPA](https://launchpad.net/~fkrull/+archive/ubuntu/deadsnakes) with:

    sudo apt-get install python-dev python3-dev python3.4-minimal python3.4-dev python3.5-minimal python3.5-dev  python3.6-minimal python3.6-dev

To run all [tests](http://tox.readthedocs.org/en/latest/):

    export TESTNAME=; tox

To run tests for a specific environment (e.g. Python 2.7 with Django 1.4):
    
    export TESTNAME=; tox -e py27-django111

To run a specific test:
    
    export TESTNAME=.test_widgets; tox -e py27-django111
