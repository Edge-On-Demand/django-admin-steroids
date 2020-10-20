from __future__ import print_function

import sys
#import traceback
from collections import defaultdict
from collections.abc import Iterator

from django.core.management.base import BaseCommand
from django.contrib.contenttypes.models import ContentType

try:
    from django.test import override_settings
except ImportError:
    from override_settings import override_settings

from admin_steroids.queryset import atomic


def get_all_related_objects(obj):
    try:
        links = obj._meta.get_all_related_objects()
    except AttributeError:
        # get_all_related_objects() was removed in Django >= 1.9
        # https://docs.djangoproject.com/es/1.9/ref/models/meta/
        links = [f for f in obj._meta.get_fields() if (f.one_to_many or f.one_to_one) and f.auto_created and not f.concrete]
    return links


class Command(BaseCommand):
    help = 'Replaces one record with another, making sure to update all foreign key references.'

    def add_arguments(self, parser):
        parser.add_argument('name')
        parser.add_argument('old_id')
        parser.add_argument('new_id')
        parser.add_argument('--dryrun', action='store_true', default=False)
        parser.add_argument('--only-show-classes', action='store_true', default=False)
        parser.add_argument(
            '--do-update',
            action='store_true',
            default=False,
            help='If given, does a SQL update instead of calling the model\'s save() method. '
            'This is only recommended for use when there are circular FK references coupled '
            'with validation logic preventing incremental saves.'
        )

    @atomic
    @override_settings(DEBUG=False)
    def handle(self, name, old_id, new_id, **options):

        def iter_db(itr):
            """
            Wrapper around an iterator, handling attribute assignment errors caused by the database router blocking relations.
            Exceptions caused by the database router as silently ignored.
            """
            if not isinstance(itr, Iterator):
                itr = iter(itr)
            while 1:
                try:
                    value = next(itr)
                    if not value._meta.managed:
                        continue
                    yield value
                except ValueError as exc:
                    if 'the current database router prevents this relation' in str(exc):
                        print('Warning, skipping value: %s' % exc)
                        continue
                    raise
                except TypeError as exc:
                    if "'list' object is not an iterator" in str(exc) or "list object is not an iterator" in str(exc):
                        break
                    raise
                except StopIteration:
                    break

        dryrun = options['dryrun']
        only_show_classes = options['only_show_classes']
        do_update = options['do_update']

        app_label, model_name = name.split('.')
        ct = ContentType.objects.get(app_label=app_label, model=model_name)
        model_cls = ct.model_class()

        old_obj = model_cls.objects.get(pk=int(old_id))
        new_obj = model_cls.objects.get(pk=int(new_id))

        print('Attempting to replace %s with %s...' % (old_obj, new_obj))

        if new_obj._state.db != old_obj._state.db:
            print('Unable to replace. Objects are not on the same database.', file=sys.stderr)
            sys.exit(1)

        deleted_objects = set()
        # [(new_obj, old_obj, referring_obj, referring_field, exception)]
        deletion_exceptions = set()
        deletion_failures = 0
        safe_to_delete = True
        referring_classes = defaultdict(int)
        links = get_all_related_objects(old_obj)
        print('%i links found.' % len(links))
        for link in links:

            if not link.model._meta.managed:
                print('Skipping unmanaged model %s.' % link.model)
                continue

            if not link.related_model._meta.managed:
                print('Skipping unmanaged related model %s.' % link.related_model)
                continue

            try:
                referring_objects = getattr(old_obj, link.get_accessor_name()).all()
                total = referring_objects.count()
                referring_objects_iters = referring_objects.iterator()
            except AttributeError:
                total = 0
                referring_objects_iters = []
                try:
                    referring_objects = getattr(old_obj, link.get_accessor_name())
                    if referring_objects:
                        total = 1
                        referring_objects_iters = [referring_objects]
                except Exception as exc:
                    if 'RelatedObjectDoesNotExist' not in type(exc).__name__:
                        raise
            i = 0
            print('%i referring objects found on link %s.' % (total, link.get_accessor_name()))
            for referring_object in iter_db(referring_objects_iters):
                i += 1

                if only_show_classes:
                    referring_classes[link.model.__name__] += 1
                    continue

                if referring_object._state.db != new_obj._state.db:
                    print('Skipping record %s because it exists on database %s instead of the target database %s.' \
                        % (referring_object, referring_object._state.db, new_obj._state.db))
                    continue

                print(
                    'Changing %s(id=%s).%s = "%s"(%s) -> "%s"(%s). (%s of %s)' % (
                        type(referring_object).__name__,
                        referring_object.id,
                        link.field.name,
                        getattr(referring_object, link.field.name),
                        getattr(referring_object, link.field.name).id,
                        new_obj,
                        new_obj.id,
                        i,
                        total,
                    )
                )
                deleted_objects.add((type(old_obj).__name__, old_obj.id, new_obj))
                try:
                    if do_update:
                        # Bypass save() logic and directly update the FK field.
                        type(referring_object).objects.filter(pk=referring_object.pk).update(**{link.field.name: new_obj})
                    else:
                        # Set field and then save through the ORM.
                        setattr(referring_object, link.field.name, new_obj)
                        referring_object.save()
                except Exception as e:
                    print(e, file=sys.stderr)
                    safe_to_delete = False
                    deletion_exceptions.add((
                        new_obj,
                        old_obj,
                        referring_object,
                        link.field.name,
                        e,
                    ))

        if only_show_classes:
            print('Classes referring to %s:' % old_obj)
            for _mdl, _cnt in referring_classes.iteritems():
                print(_cnt, _mdl)
        else:
            # Now all FK links should be gone so we can safely delete the duplicate.
            if safe_to_delete:
                old_obj.delete()
            else:
                deletion_failures += 1

        if dryrun:
            print('%i objects pending deletion.' % len(deleted_objects))
            deleted_by_type = {}
            for cls_name, deleted_obj_id, real_obj in deleted_objects:
                deleted_by_type.setdefault(cls_name, [])
                deleted_by_type[cls_name].append((deleted_obj_id, real_obj.id))
            for cls_name, id_lst in deleted_by_type.iteritems():
                print(cls_name, ', '.join('%s -> %s' % (old_id, new_id) for old_id, new_id in id_lst))
        else:
            print('%i objects deleted.' % len(deleted_objects))

        if deletion_failures:
            print('!' * 80)
            print('%i deletion failures!' % deletion_failures)
            for del_exc in deletion_exceptions:
                new_obj, dup_obj, other_instance, other_field_name, exc = del_exc
                print(
                    'Unable to change %s(id=%i).%s from %s(%s) to %s(%s): %s' % (
                        type(other_instance).__name__,
                        other_instance.id,
                        other_field_name,
                        dup_obj,
                        dup_obj.id,
                        new_obj,
                        new_obj.id,
                        exc,
                    )
                )
