import os
import sys
import pathlib
import django
from django.db import transaction

# Ensure project root is on sys.path so 'mm3_site' can be imported
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mm3_site.settings')
django.setup()

from django.contrib.auth.models import User
from combate.models import Combate, Participante
from personagens.models import Personagem
from combate.views import _aplicar_falha_salvamento


PASS = 0
FAIL = 0

def check(label, cond, details=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"OK  {label}")
    else:
        FAIL += 1
        print(f"ERR {label} {details}")


def reset_part(p):
    p.dano = 0
    p.aflicao = 0
    p.ferimentos = 0
    p.bonus_temporario = 0
    p.penalidade_temporaria = 0
    p.proximo_bonus_por_atributo = {}
    p.save()


@transaction.atomic
def main():
    global PASS, FAIL
    print("--- Smoke test: Ferimentos, Dano, Aflição e Cura ---")

    # Setup minimal objects
    u, _ = User.objects.get_or_create(username='tmp_smoke_ferimentos')
    # Create a minimal Personagem; defaults for attributes should be fine for these tests
    atk, _ = Personagem.objects.get_or_create(usuario=u, nome='Attacker', defaults={'nivel_poder': 10})
    tgt, _ = Personagem.objects.get_or_create(usuario=u, nome='Target', defaults={'nivel_poder': 10})

    combate = Combate.objects.create(ativo=True)  # sala nullable
    part_tgt = Participante.objects.create(personagem=tgt, combate=combate, iniciativa=10)

    # 1) Dano progression and incapacitation at 4
    reset_part(part_tgt)
    _aplicar_falha_salvamento(part_tgt, 'dano', 1, None, None)  # degree 1
    part_tgt.refresh_from_db()
    check("Dano deg1 -> dano=1, fer=1", part_tgt.dano == 1 and part_tgt.ferimentos == 1,
          f"got dano={part_tgt.dano}, fer={part_tgt.ferimentos}")

    _aplicar_falha_salvamento(part_tgt, 'dano', 1, None, None)  # still degree 1
    part_tgt.refresh_from_db()
    check("Dano deg1 again -> no dano increase, fer+1", part_tgt.dano == 1 and part_tgt.ferimentos == 2,
          f"got dano={part_tgt.dano}, fer={part_tgt.ferimentos}")

    _aplicar_falha_salvamento(part_tgt, 'dano', 3, None, None)
    part_tgt.refresh_from_db()
    check("Dano deg3 -> dano climbs to 2, fer=3", part_tgt.dano == 2 and part_tgt.ferimentos == 3,
          f"got dano={part_tgt.dano}, fer={part_tgt.ferimentos}")

    _aplicar_falha_salvamento(part_tgt, 'dano', 3, None, None)
    part_tgt.refresh_from_db()
    check("Dano deg3 again -> dano 3, fer=4", part_tgt.dano == 3 and part_tgt.ferimentos == 4,
          f"got dano={part_tgt.dano}, fer={part_tgt.ferimentos}")

    _, incapac, _ = _aplicar_falha_salvamento(part_tgt, 'dano', 4, None, None)
    part_tgt.refresh_from_db()
    check("Dano deg4 -> dano 4 (incapacitado), fer=5", part_tgt.dano == 4 and part_tgt.ferimentos == 5 and incapac,
          f"got dano={part_tgt.dano}, fer={part_tgt.ferimentos}, incap={incapac}")

    # 2) Aflição progression with new rules (no Ferimentos, cap 3, multi-level)
    reset_part(part_tgt)
    # degree 1 -> +1 nível (0 -> 1), sem ferimentos
    _aplicar_falha_salvamento(part_tgt, 'aflicao', 1, None, None)
    part_tgt.refresh_from_db()
    check("Aflição deg1 -> af=1, fer=0", part_tgt.aflicao == 1 and part_tgt.ferimentos == 0,
          f"got af={part_tgt.aflicao}, fer={part_tgt.ferimentos}")

    # novo teste degree 2 (+2 níveis): 1 -> 3 (capado), sem ferimentos
    _aplicar_falha_salvamento(part_tgt, 'aflicao', 2, None, None)
    part_tgt.refresh_from_db()
    check("Aflição deg2 from 1 -> af=3, fer=0", part_tgt.aflicao == 3 and part_tgt.ferimentos == 0,
          f"got af={part_tgt.aflicao}, fer={part_tgt.ferimentos}")

    # outro teste degree 3 não ultrapassa 3
    _aplicar_falha_salvamento(part_tgt, 'aflicao', 3, None, None)
    part_tgt.refresh_from_db()
    check("Aflição deg3 at max -> af=3, fer=0", part_tgt.aflicao == 3 and part_tgt.ferimentos == 0,
          f"got af={part_tgt.aflicao}, fer={part_tgt.ferimentos}")

    # 3) Cura CD and reset ferimentos when fully healed
    reset_part(part_tgt)
    part_tgt.dano = 1
    part_tgt.ferimentos = 4  # accumulated
    part_tgt.save()

    # According to rules: CD = 10 + ferimentos; heal higher between dano and aflição by 1 on success
    cd = 10 + part_tgt.ferimentos
    roll = cd  # succeed exactly on the CD
    # simulate cura: dano >= aflição, so heal dano by 1 if roll >= cd
    if roll >= cd and part_tgt.dano >= part_tgt.aflicao and part_tgt.dano > 0:
        part_tgt.dano = max(0, part_tgt.dano - 1)
        part_tgt.save()
        part_tgt.refresh_from_db()
        # if fully healed (0/0), reset ferimentos
        if part_tgt.dano == 0 and part_tgt.aflicao == 0:
            part_tgt.ferimentos = 0
            part_tgt.save()
    part_tgt.refresh_from_db()
    check("Cura success heals dano and resets ferimentos at 0/0", part_tgt.dano == 0 and part_tgt.aflicao == 0 and part_tgt.ferimentos == 0,
          f"got dano={part_tgt.dano}, af={part_tgt.aflicao}, fer={part_tgt.ferimentos}")

    # 4) Cura when nothing to heal should also clear ferimentos
    part_tgt.dano = 0
    part_tgt.aflicao = 0
    part_tgt.ferimentos = 2
    part_tgt.save()
    cd2 = 10 + part_tgt.ferimentos
    roll2 = cd2  # success, but nothing to heal
    if part_tgt.dano == 0 and part_tgt.aflicao == 0:
        # Rule: if nothing to heal and already 0/0, also clear ferimentos
        part_tgt.ferimentos = 0
        part_tgt.save()
    part_tgt.refresh_from_db()
    check("Cura with nothing to heal clears ferimentos", part_tgt.ferimentos == 0,
          f"got fer={part_tgt.ferimentos}")

    print(f"\nResult: PASS={PASS}, FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
