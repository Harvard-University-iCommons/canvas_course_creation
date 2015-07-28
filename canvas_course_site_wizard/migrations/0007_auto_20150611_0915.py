# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('canvas_course_site_wizard', '0006_auto_20150610_1017'),
    ]

    operations = [
        migrations.AddField(
            model_name='bulkcanvascoursecreationjob',
            name='template_canvas_course_id',
            field=models.IntegerField(null=True, blank=True),
        ),
    ]
