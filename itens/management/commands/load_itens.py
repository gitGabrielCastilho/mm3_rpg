import json
import re
import random
from django.core.management.base import BaseCommand
from itens.models import Item

TYPE_BASE_MAP = {
    "M": "Melee Weapon",
    "R": "Ranged Weapon",
    "LA": "Light Armor",
    "MA": "Medium Armor",
    "HA": "Heavy Armor",
    "S": "Shield",
    "A": "Ammunition",
    "RD": "Rod",
    "WD": "Wondrous Item",
    "TG": "Trade Good",
    "G": "Adventuring Gear",
    "$G": "Generic Variant",
    "$A": "Generic Variant",
    "$C": "Generic Variant",
    "GS": "Gaming Set",
    "T": "Tool",
    "AT": "Artisan's Tools",
    "INS": "Instrument",
    "SCF": "Spellcasting Focus",
    "SC": "Scroll",
    "P": "Poison",
    "FD": "Food/Drink",
    "EXP": "Explosive",
    "RG": "Ring",
    "TAH": "Tack and Harness",
    "MNT": "Mount",
    "VEH": "Vehicle",
    "SHP": "Ship",
    "AIR": "Air Vehicle",
    "TB": "Tinker’s Tool (Bundle)",
    "SPC": "Space Vehicle",
    "IDG": "Idol/Relic",
    "OTH": "Other",
}

RARIDADE_MAP = {
    'artifact': 'Artifact',
    'common': 'Common',
    'legendary': 'Legendary',
    'none': 'Unknown',
    'rare': 'Rare',
    'uncommon': 'Uncommon',
    'unknown': 'Unknown',
    'unknown (magic)': 'Unknown (Magic)',
    'varies': 'Varies',
    'very rare': 'Very Rare',
}

def clean_entry(text):
    return re.sub(r'\{@[a-zA-Z0-9]+ ([^|}]+)[^}]*\}', r'\1', text)


def process_entries(obj):
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == 'entries' and isinstance(value, list):
                obj[key] = [clean_entry(entry) if isinstance(entry, str) else process_entries(entry) for entry in value]
            elif key == 'entry' and isinstance(value, str):
                obj[key] = clean_entry(value)
            else:
                process_entries(value)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            if isinstance(item, str):
                obj[i] = clean_entry(item)
            else:
                process_entries(item)
    return obj


def calcular_valor(rarity):
    rarity = (rarity or "").lower()
    if rarity == "common":
        return random.randint(2, 12) * 5
    elif rarity == "uncommon":
        return random.randint(2, 12) * 250
    elif rarity == "rare":
        return random.randint(2, 12) * 2500 + 5000
    elif rarity == "very rare":
        return random.randint(2, 12) * 8000 + 40000
    elif rarity == "legendary":
        return random.randint(2, 12) * 12500 + 150000
    elif rarity == "artifact":
        return (random.randint(2, 12) + 6) * 75000 + 3000000
    else:
        return 0


def build_display_type(it):
    raw_type = it.get("type")
    if not raw_type:
        return None
    if isinstance(raw_type, list):
        raw_type = "|".join(raw_type)
    base, *_ = raw_type.split("|", 1)
    if base in {"M", "R"}:
        weapon_cat = it.get("weaponCategory")
        parts = []
        if weapon_cat:
            parts.append(f"{weapon_cat} Weapon")
        parts.append("Melee Weapon" if base == "M" else "Ranged Weapon")
        return ", ".join(parts)
    return TYPE_BASE_MAP.get(base, TYPE_BASE_MAP.get(raw_type, raw_type))


def mapear_raridade(raridade):
    return RARIDADE_MAP.get((raridade or '').lower(), raridade or '')


def tratar_entries(entries):
    if isinstance(entries, list):
        return "\n".join(str(e) for e in entries)
    return str(entries) if entries else ""


class Command(BaseCommand):
    help = "Carrega/atualiza a tabela de Itens a partir de items.json com limpeza de texto. Idempotente."

    def add_arguments(self, parser):
        parser.add_argument('--path', type=str, default='items.json', help='Caminho para items.json')

    def handle(self, *args, **options):
        path = options['path']
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        data_tratado = process_entries(data)

        # também grava items_tratado.json (útil para depuração)
        with open('items_tratado.json', 'w', encoding='utf-8') as f:
            json.dump(data_tratado, f, ensure_ascii=False, indent=2)

        created, updated = 0, 0
        for it in data_tratado.get('item', []):
            preco = calcular_valor(it.get('rarity', ''))
            tipo_legivel = build_display_type(it) or 'Other'
            raridade_legivel = mapear_raridade(it.get('rarity', '')) or 'Unknown'
            descricao = tratar_entries(it.get('entries', ''))

            obj, was_created = Item.objects.update_or_create(
                nome=it.get('name', ''),
                defaults={
                    'tipo': tipo_legivel,
                    'raridade': raridade_legivel,
                    'descricao': descricao,
                    'preco': preco,
                    'sala': None,
                }
            )
            if was_created:
                created += 1
            else:
                updated += 1
        self.stdout.write(self.style.SUCCESS(
            f"Itens processados com sucesso. Criados: {created}, Atualizados: {updated}."
        ))
