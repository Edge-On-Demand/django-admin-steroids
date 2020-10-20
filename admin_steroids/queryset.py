from __future__ import print_function

import hashlib
import re
import sys
import traceback

from django.core.cache import cache
from django.db import connections, transaction
from django.db.models.query import QuerySet
from django.db.models.sql import EmptyResultSet
from django.db.models.query import RawQuerySet

try:
    from django.db.transaction import atomic
except ImportError:
    # Allow Django<1.6 to use atomic().
    from django.db.transaction import commit_on_success as atomic


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
            part = re.sub(r'/\*.*\*/', '', part, flags=re.I | re.DOTALL | re.MULTILINE).strip()
            part = re.sub(r'\-\-.*\n', '', part, flags=re.I).strip()
            part = '\n'.join(line for line in part.split('\n') if not line.strip().startswith('--'))
            part = part.strip()
            if not part:
                continue
            if not part.endswith(';'):
                part = part + ';'
            print('sql:', part, file=sys.stdout)
            _execute_sql_part(part, using=using)
    except Exception:
        traceback.print_exc(file=sys.stderr)
        if not connections[using or 'default'].in_atomic_block:
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

        if self._result_cache is not None:
            return len(self._result_cache)

        db_backend_name = connections[self.db].client.executable_name.lower()
        is_postgres = 'psql' in db_backend_name \
            or 'postgres' in db_backend_name \
            or 'postgis' in db_backend_name
        is_mysql = 'mysql' in db_backend_name

        query = self.query
        if (is_postgres or is_mysql
            ) and (not query.where and query.high_mark is None and query.low_mark == 0 and not query.select and not query.group_by and not query.distinct):
            if is_postgres:
                # Read table count approximation from PostgreSQL's pg_class.
                cursor = connections[self.db].cursor()
                # Note, there's a bug in the default execute() that
                # misquotes arguments by using double-quotes when PG only
                # uses single-quotes.
                sql = "SELECT reltuples::int FROM pg_class WHERE oid = '%s'::regclass;" % (self.model._meta.db_table,)
                cursor.execute(sql)
                results = cursor.fetchall()
                return results[0][0]
            if is_mysql:
                # Read table count approximation from MySQL's "SHOW TABLE".
                cursor = connections[self.db].cursor()
                cursor.execute("SHOW TABLE STATUS LIKE %s", (self.model._meta.db_table,))
                return cursor.fetchall()[0][4]
            raise NotImplementedError
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
                count = super().count()
                cache.set(cache_key, count, self.cache_seconds)
        except EmptyResultSet:
            count = super().count()
        return count


class SmartRawQuerySet(RawQuerySet):
    """
    Adds common queryset operators, like exists() and count() to Django's RawQuerySet.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.clear_cache()

    @classmethod
    def from_queryset(cls, qs):
        return SmartRawQuerySet(
            raw_query=qs.raw_query, model=qs.model, query=qs.query, params=qs.params, translations=qs.translations, using=qs._db, hints=qs._hints
        )

    def clear_cache(self):
        self._cache_count = None
        self._cache_exists = None

    def count(self):
        if self._cache_count is None:
            new_sql = self.raw_query
            new_sql = re.sub('SELECT(.*?)FROM', 'SELECT COUNT(1) FROM', new_sql, 1, re.M)
            new_sql = re.sub(r'ORDER BY(.|\s)*$', '', new_sql, re.MULTILINE | re.DOTALL)
            with connections[self._db].cursor() as cursor:
                cursor.execute(new_sql)
                row = cursor.fetchone()
                self._cache_count = row[0]
        return self._cache_count

    def exists(self):
        if self._cache_exists is None:
            new_sql = self.raw_query
            new_sql = re.sub('SELECT(.*?)FROM', 'SELECT 1 FROM', new_sql, 1, re.M)
            new_sql = re.sub(r'ORDER BY(.|\s)*$', 'LIMIT 1', new_sql, re.MULTILINE | re.DOTALL)
            with connections[self._db].cursor() as cursor:
                cursor.execute(new_sql)
                row = cursor.fetchone()
                self._cache_exists = bool(row)
        return self._cache_exists
