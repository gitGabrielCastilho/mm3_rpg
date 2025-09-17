import os
import sys
import pathlib
import django
from django.core.exceptions import ValidationError

# Ensure project root is on sys.path so 'mm3_site' can be imported
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mm3_site.settings')
django.setup()

from django.contrib.auth.models import User
from personagens.models import Personagem


def trycase(label, **kw):
    u, _ = User.objects.get_or_create(username='tmp_smoke')
    p = Personagem(usuario=u, nome='T', nivel_poder=10, **kw)
    try:
        p.full_clean()
        print('OK  ', label, kw)
    except ValidationError as e:
        msgs = []
        if hasattr(e, 'messages') and e.messages:
            msgs = e.messages
        elif hasattr(e, 'message_dict'):
            for v in e.message_dict.values():
                msgs.extend(v)
        print('ERR ', label, kw, '|', '; '.join(msgs))


print('--- Smoke test: defense pair rules ---')
# Should pass (10+10 <= 20)
trycase('E+R == 20 OK', esquivar=10, resistencia=10)
# Should fail (11+10 > 20)
trycase('E+R > 20 FAIL', esquivar=11, resistencia=10)
# Should fail (15+6 > 20)
trycase('A+R > 20 FAIL', aparar=15, resistencia=6)
# Should fail (11+10 > 20)
trycase('F+V > 20 FAIL', fortitude=11, vontade=10)
# Should pass: A+E no longer constrained
trycase('A+E high OK', aparar=20, esquivar=20)
# Extra: unrelated large values but pairs under limits
trycase('mixed OK', esquivar=9, resistencia=11, aparar=18, fortitude=10, vontade=10)
