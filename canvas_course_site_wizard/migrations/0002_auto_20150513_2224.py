# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('canvas_course_site_wizard', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='canvascontentmigrationjob',
            name='canvas_course_id',
            field=models.IntegerField(db_index=True, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='canvascontentmigrationjob',
            name='content_migration_id',
            field=models.IntegerField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='canvascontentmigrationjob',
            name='status_url',
            field=models.CharField(max_length=200, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='canvascontentmigrationjob',
            name='workflow_state',
            field=models.CharField(default=b'setup', max_length=20, choices=[(b'setup', b'setup'), (b'setup_failed', b'setup_failed'), (b'queued', b'queued'), (b'running', b'running'), (b'completed', b'completed'), (b'failed', b'failed'), (b'finalized', b'finalized'), (b'finalize_failed', b'finalize_failed')]),
        ),
    ]
