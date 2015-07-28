# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('canvas_course_site_wizard', '0007_auto_20150611_0915'),
    ]

    operations = [
        migrations.AddField(
            model_name='canvasschooltemplate',
            name='include_course_info',
            field=models.BooleanField(default=False),
        ),
    ]
