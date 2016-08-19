from __future__ import print_function

import sys
from datetime import date
from pprint import pprint
import traceback
from collections import defaultdict

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q, Min, Max, Sum, Count, F
from django.db.models.deletion import Collector
from django.db.transaction import commit, commit_on_success, commit_manually, autocommit, rollback
from django.db import IntegrityError, DatabaseError
from django.contrib.contenttypes.models import ContentType
                
from optparse import make_option

class Command(BaseCommand):
    help = 'Replaces one record with another, making sure to update all foreign key references.'
    args = 'app.model old_id new_id'
    option_list = BaseCommand.option_list + (
        make_option('--dryrun', action='store_true', default=False),
        make_option('--only-show-classes', action='store_true', default=False),
        make_option('--do-update', action='store_true', default=False,
            help='If given, does a SQL update instead of calling the model\'s save() method. '
                'This is only recommended for use when there are circular FK references coupled '
                'with validation logic preventing incremental saves.'),
    )

    @commit_manually
    def handle(self, name, old_id, new_id, **options):
        try:
            tmp_debug = settings.DEBUG
            settings.DEBUG = False
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
            links = old_obj._meta.get_all_related_objects()
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
                            setattr(referring_object,  link.field.name, new_obj)
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
                    
        except Exception as e:
            print(traceback.format_exc(), file=sys.stderr)
            rollback()
        else:
            if dryrun:
                rollback()
            else:
                commit()
        finally:
            settings.DEBUG = tmp_debug
            