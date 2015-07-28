# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('canvas_course_site_wizard', '0002_auto_20150513_2224'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='CanvasContentMigrationJob',
            new_name='CanvasCourseGenerationJob',
        ),
        migrations.CreateModel(
            name='CanvasCourseGenerationJobProxy',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('canvas_course_site_wizard.canvascoursegenerationjob',),
        ),
        migrations.AlterModelTable(
            name='canvascoursegenerationjob',
            table='canvas_course_generation_job',
        ),
    ]
