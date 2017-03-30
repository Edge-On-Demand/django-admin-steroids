from __future__ import print_function

import sys
#import traceback
from collections import defaultdict
from optparse import make_option

from django import get_version, VERSION
from django.core.management.base import BaseCommand
from django.contrib.contenttypes.models import ContentType

try:
    from django.test import override_settings
except ImportError:
    from override_settings import override_settings

from admin_steroids.queryset import atomic

def get_options(parser=None):
    make_opt = make_option
    if parser:
        make_opt = parser.add_argument
    return [
        make_opt('--dryrun', action='store_true', default=False),
        make_opt('--only-show-classes', action='store_true', default=False),
        make_opt('--do-update', action='store_true', default=False,
            help='If given, does a SQL update instead of calling the model\'s save() method. '
                'This is only recommended for use when there are circular FK references coupled '
                'with validation logic preventing incremental saves.'),
    ]

def get_all_related_objects(obj):
    try:
        links = obj._meta.get_all_related_objects()
    except AttributeError:
        # get_all_related_objects() was removed in Django >= 1.9
        # https://docs.djangoproject.com/es/1.9/ref/models/meta/
        links = [
            f for f in obj._meta.get_fields()
            if (f.one_to_many or f.one_to_one) and f.auto_created and not f.concrete
        ]
    return links

class Command(BaseCommand):
    help = 'Replaces one record with another, making sure to update all foreign key references.'
    args = 'app.model old_id new_id'
    option_list = getattr(BaseCommand, 'option_list', ()) + tuple(get_options())

    def create_parser(self, prog_name, subcommand):
        """
        For ``Django>=1.10``
        Create and return the ``ArgumentParser`` which extends ``BaseCommand`` parser with
        chroniker extra args and will be used to parse the arguments to this command.
        """
        from distutils.version import StrictVersion # pylint: disable=E0611,import-error
        parser = super(Command, self).create_parser(prog_name, subcommand)
        version_threshold = StrictVersion('1.10')
        current_version = StrictVersion(get_version(VERSION))
        if current_version >= version_threshold:
            parser.add_argument('name')
            parser.add_argument('old_id')
            parser.add_argument('new_id')
            get_options(parser)
            self.add_arguments(parser)
        return parser

    @atomic
    @override_settings(DEBUG=False)
    def handle(self, name, old_id, new_id, **options):

        dryrun = options['dryrun']
        only_show_classes = options['only_show_classes']
        do_update = options['do_update']

        app_label, model_name = name.split('.')
        ct = ContentType.objects.get(app_label=app_label, model=model_name)
        model_cls = ct.model_class()

        old_obj = model_cls.objects.get(pk=int(old_id))
        new_obj = model_cls.objects.get(pk=int(new_id))

        print('Attempting to replace %s with %s...' % (old_obj, new_obj))

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
                continue
            try:
                referring_objects = getattr(old_obj, link.get_accessor_name()).all()
                total = referring_objects.count()
                referring_objects_iters = referring_objects.iterator()
            except AttributeError:
                referring_objects = getattr(old_obj, link.get_accessor_name())
                if referring_objects:
                    total = 1
                    referring_objects_iters = [referring_objects]
                else:
                    total = 0
                    referring_objects_iters = []
            i = 0
            print('%i referring objects found on link %s.' % (total, link.get_accessor_name()))
            for referring_object in referring_objects_iters:
                i += 1

                if only_show_classes:
                    referring_classes[link.model.__name__] += 1
                    continue

                print('Changing %s(id=%i).%s = "%s"(%i) -> "%s"(%i). (%i of %i)' % (
                    link.model.__name__,
                    referring_object.id,
                    link.field.name,
                    getattr(referring_object, link.field.name),
                    getattr(referring_object, link.field.name).id,
                    new_obj,
                    new_obj.id,
                    i,
                    total,
                ))
                deleted_objects.add(
                    (type(old_obj).__name__, old_obj.id, new_obj)
                )
                try:
                    if do_update:
                        # Bypass save() logic and directly update the FK field.
                        type(referring_object).objects\
                            .filter(pk=referring_object.pk)\
                            .update(**{link.field.name: new_obj})
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
                print(cls_name, ', '.join(
                    '%s -> %s' % (old_id, new_id) for old_id, new_id in id_lst
                ))
        else:
            print('%i objects deleted.' % len(deleted_objects))

        if deletion_failures:
            print('!'*80)
            print('%i deletion failures!' % deletion_failures)
            for del_exc in deletion_exceptions:
                new_obj, dup_obj, other_instance, other_field_name, exc = del_exc
                print('Unable to change %s(id=%i).%s from %s(%s) to %s(%s): %s' % (
                    type(other_instance).__name__,
                    other_instance.id,
                    other_field_name,
                    dup_obj, dup_obj.id,
                    new_obj, new_obj.id,
                    exc,
                ))
