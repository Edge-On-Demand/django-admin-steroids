from django.db import models, connections

from . import queryset

class ViewModelManager(models.Manager):
    """
    Helper manager for managing Django-managed SQL views.
    
    Given a Django ORM-generated RawQuerySet, creates an equivalent SQL view
    that can then be wrapped in a model class.
    
    To use, subclass ViewModelManager and attach it to an unmanaged model
    with a db_table value. Then implement get_view_query_set()
    and call write_sql_view(). Ensure the model has fields for all the columns
    returns by the raw queryset.
    """
    
    _mysql_view_template = '''SET max_error_count = 0;
DROP VIEW IF EXISTS {view_name} CASCADE;
CREATE VIEW {view_name}
AS
{view_query};
SET max_error_count = 64;
'''

    _postgresql_view_template = '''DROP VIEW IF EXISTS {view_name} CASCADE;
CREATE VIEW {view_name}
AS
{view_query};
'''
  
    _sqlite_view_template = '''DROP VIEW IF EXISTS {view_name};
CREATE VIEW {view_name}
AS
{view_query};
'''
  
    def get_view_query_set(self):
        raise NotImplementedError

    def get_sql_view(self, using=None):
        using = using or 'default'
        conn = connections[using]
        view_template = getattr(self, '_%s_view_template' % conn.vendor)
        view_sql = view_template.format(
            view_name=self.model._meta.db_table,
            view_query=str(self.get_view_query_set().query))
        return view_sql

    def write_sql_view(self, using=None):
        view_sql = self.get_sql_view(using=using)
        queryset.execute_sql(view_sql)
