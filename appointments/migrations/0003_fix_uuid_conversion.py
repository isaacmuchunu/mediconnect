# appointments/migrations/0003_simple_uuid_fix.py

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):
    
    dependencies = [
        ('appointments', '0002_appointmentattachment_appointmentnote_and_more'),
    ]
    
    operations = [
        # Since the original migration was faked, we just need to tell Django 
        # that the field is now UUID without actually changing the database
        migrations.AlterField(
            model_name='appointment',
            name='id',
            field=models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False),
        ),
    ]