from django.db import migrations, models


class Migration(migrations.Migration):

	dependencies = [
		('personagens', '0028_alter_poder_duracao_add_sustentado'),
	]

	operations = [
		migrations.AddField(
			model_name='poder',
			name='ligados',
			field=models.ManyToManyField(blank=True, help_text='Poderes que disparam em cadeia junto com este. Precisam ter mesmo modo e duração.', to='personagens.poder'),
		),
	]
