# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('canvas_course_site_wizard', '0004_auto_20150519_1112'),
    ]

    operations = [
        migrations.DeleteModel(
            name='BulkCanvasCourseCreationJobProxy',
        ),
        migrations.DeleteModel(
            name='CanvasCourseGenerationJobProxy',
        ),
    ]
