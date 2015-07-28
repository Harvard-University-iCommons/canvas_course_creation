# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import canvas_course_site_wizard.models


class Migration(migrations.Migration):

    dependencies = [
        ('icommons_common', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='BulkCanvasCourseCreationJob',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('school_id', models.CharField(max_length=10)),
                ('sis_term_id', models.IntegerField()),
                ('status', models.CharField(default=b'setup', max_length=25, choices=[(b'setup', b'setup'), (b'pending', b'pending'), (b'finalizing', b'finalizing'), (b'notification_successful', b'notification_successful'), (b'notification_failed', b'notification_failed')])),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by_user_id', models.CharField(max_length=20)),
                ('updated_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'bulk_canvas_course_crtn_job',
            },
        ),
        migrations.CreateModel(
            name='CanvasContentMigrationJob',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('canvas_course_id', models.IntegerField(db_index=True)),
                ('sis_course_id', models.CharField(max_length=20, db_index=True)),
                ('content_migration_id', models.IntegerField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now_add=True)),
                ('status_url', models.CharField(max_length=200)),
                ('workflow_state', models.CharField(default=b'queued', max_length=20, choices=[(b'setup', b'setup'), (b'setup_failed', b'setup_failed'), (b'queued', b'queued'), (b'running', b'running'), (b'completed', b'completed'), (b'failed', b'failed'), (b'finalized', b'finalized'), (b'finalize_failed', b'finalize_failed')])),
                ('created_by_user_id', models.CharField(max_length=20)),
                ('bulk_job_id', models.IntegerField(null=True, blank=True)),
            ],
            options={
                'db_table': 'canvas_content_migration_job',
            },
        ),
        migrations.CreateModel(
            name='CanvasSchoolTemplate',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('template_id', models.IntegerField()),
                ('school_id', models.CharField(max_length=10, db_index=True)),
            ],
            options={
                'db_table': 'canvas_school_template',
            },
        ),
        migrations.CreateModel(
            name='SISCourseData',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('icommons_common.courseinstance', canvas_course_site_wizard.models.SISCourseDataMixin),
        ),
        migrations.CreateModel(
            name='BulkCanvasCourseCreationJobProxy',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('canvas_course_site_wizard.bulkcanvascoursecreationjob',),
        ),
    ]
