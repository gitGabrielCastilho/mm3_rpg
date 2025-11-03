import os, sys, json
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mm3_site.settings')
import django
django.setup()
from itens.models import Item

names = sys.argv[1:] or ['Bracers of Defense','Animated Shield']
qs = Item.objects.filter(nome__in=names)
if not qs.exists():
    print('No matching items found for:', names)
    sys.exit(0)
for it in qs:
    print(f"Item: {it.nome} (id={it.id})")
    print('Tipo:', getattr(it, 'tipo', None), '| Raridade:', getattr(it, 'raridade', None))
    try:
        mods = it.mods or {}
    except Exception as e:
        mods = {}
    print('mods raw:', json.dumps(mods, ensure_ascii=False))
    if hasattr(it, 'poderes'):
        pods = list(it.poderes.values('nome','tipo','modo','duracao','nivel_efeito','bonus_ataque'))
        if pods:
            print('poderes:', json.dumps(pods, ensure_ascii=False))
    print('-'*60)
