# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('canvas_course_site_wizard', '0003_auto_20150518_1139'),
    ]

    operations = [
        migrations.AddField(
            model_name='bulkcanvascoursecreationjob',
            name='sis_course_group_id',
            field=models.IntegerField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='bulkcanvascoursecreationjob',
            name='sis_department_id',
            field=models.IntegerField(null=True, blank=True),
        ),
    ]
