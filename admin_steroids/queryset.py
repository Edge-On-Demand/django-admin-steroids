from __future__ import print_function

import hashlib
import re
import sys
import traceback

from django.core.cache import cache
from django.db import connections, transaction
from django.db.models.query import QuerySet
from django.db.models.sql import EmptyResultSet

try:
    from django.db.transaction import atomic
except ImportError:
    # Allow Django<1.6 to use atomic().
    from django.db.transaction import commit_on_success as atomic
    # Removed due to TypeError: 'atomic' object is not callable?
#     class atomic(object):
#         def __init__(self, using=None):
#             self.using = using
#
#         def __enter__(self):
#             if not transaction.is_managed(using=self.using):
#                 transaction.enter_transaction_management(using=self.using)
#                 self.forced_managed = True
#             else:
#                 self.forced_managed = False
#
#         def __exit__(self, *args, **kwargs):
#             try:
#                 if self.forced_managed:
#                     transaction.commit(using=self.using)
#                 else:
#                     transaction.commit_unless_managed(using=self.using)
#             finally:
#                 if self.forced_managed:
#                     transaction.leave_transaction_management(using=self.using)

def execute_sql_from_file(fn, using=None):
    """
    Executes multiple SQL statements in the given file.
    """
    return execute_sql(open(fn).read(), using=using)

def execute_sql(sql, using=None):
    """
    Executes multiple SQL statements in the given string.
    """
    try:
        sql_parts = sql.split(';')
        for part in sql_parts:
            part = re.sub(r'/\*.*\*/', '', part, flags=re.I|re.DOTALL|re.MULTILINE).strip()
            part = re.sub(r'\-\-.*\n', '', part, flags=re.I).strip()
            if not part:
                continue
            if not part.endswith(';'):
                part = part + ';'
            print('sql:', part, file=sys.stdout)
            _execute_sql_part(part, using=using)
    except Exception:
        traceback.print_exc(file=sys.stderr)
        transaction.rollback()

def _execute_sql_part(part, using=None):
    """
    Executes a single SQL statement.
    """
    using = using or 'default'
    conn = connections[using]
    with atomic(using=using):
        cursor = conn.cursor()
        cursor.execute(part)

class ApproxCountQuerySet(QuerySet):
    """
    Counting all rows is very expensive on large Innodb tables. This
    is a replacement for QuerySet that returns an approximation if count()
    is called with no additional constraints. In all other cases it should
    behave exactly as QuerySet.

    Only works with MySQL. Behaves normally for all other engines.

    You'd use it by cloning your queryset, substituting this class

    e.g. to apply to a ModelAdmin, you'd override queryset() like:

        def queryset(self, *args, **kwargs):
            qs = super(MyModelAdmin, self).queryset(*args, **kwargs)
            qs = qs._clone(klass=ApproxCountQuerySet)
            return qs

    Based on code from answer http://stackoverflow.com/a/10446271/247542.
    """

    def count(self):
        # Code from django/db/models/query.py

        #if self._result_cache is not None and not self._iter:# ._iter removed in Django 1.6?
        if self._result_cache is not None:
            return len(self._result_cache)

        db_backend_name = connections[self.db].client.executable_name.lower()
#        print('db_backend_name:',db_backend_name
        is_postgres = 'psql' in db_backend_name \
            or 'postgres' in db_backend_name \
            or 'postgis' in db_backend_name
        is_mysql = 'mysql' in db_backend_name
#        print('is_postgres:',is_postgres

        query = self.query
        if (is_postgres or is_mysql) and (
            not query.where and
            query.high_mark is None and
            query.low_mark == 0 and
            not query.select and
            not query.group_by and
            not query.having and
            not query.distinct):
            if is_postgres:
                # Read table count approximation from PostgreSQL's pg_class.
                cursor = connections[self.db].cursor()
                # Note, there's a bug in the default execute() that
                # misquotes arguments by using double-quotes when PG only
                # uses single-quotes.
                sql = "SELECT reltuples::int FROM pg_class WHERE oid = '%s'::regclass;" \
                    % (self.model._meta.db_table,)
                cursor.execute(sql)
                results = cursor.fetchall()
                return results[0][0]
            elif is_mysql:
                # Read table count approximation from MySQL's "SHOW TABLE".
                cursor = connections[self.db].cursor()
                cursor.execute("SHOW TABLE STATUS LIKE %s",
                        (self.model._meta.db_table,))
                return cursor.fetchall()[0][4]
            else:
                raise NotImplementedError
        else:
            return self.query.get_count(using=self.db)

class CachedCountQuerySet(ApproxCountQuerySet):
    """
    Wraps a caching layer over ApproxCountQuerySet, since it only gives global
    table counts and reverts to a direct query if any filters are applied.
    """

    cache_seconds = 3600 # 1-hour

    def count(self):
        try:
            sql = str(self.query)
            cache_key = hashlib.sha512(sql).hexdigest()
            count = cache.get(cache_key)
            if count is None:
                count = super(CachedCountQuerySet, self).count()
                cache.set(cache_key, count, self.cache_seconds)
        except EmptyResultSet:
            count = super(CachedCountQuerySet, self).count()
        return count
