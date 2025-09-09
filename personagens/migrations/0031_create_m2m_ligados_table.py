from django.db import migrations


class Migration(migrations.Migration):

	dependencies = [
		('personagens', '0030_alter_poder_ligados'),
	]

	operations = [
		# No-op because Django should have created the implicit M2M table in 0029/0030.
		# This placeholder ensures ordering so production picks up the previous alterations.
	]
