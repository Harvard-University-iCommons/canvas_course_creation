# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('canvas_course_site_wizard', '0005_auto_20150528_1557'),
    ]

    operations = [
        migrations.AddField(
            model_name='canvasschooltemplate',
            name='is_default',
            field=models.BooleanField(default=False),
        ),
    ]
