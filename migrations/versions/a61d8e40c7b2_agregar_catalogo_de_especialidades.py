"""Agregar catálogo normalizado de especialidades técnicas.

Revision ID: a61d8e40c7b2
Revises: f4a7c921de10
Create Date: 2026-09-04
"""

import html
import re
import unicodedata

from alembic import op
import sqlalchemy as sa


revision = "a61d8e40c7b2"
down_revision = "f4a7c921de10"
branch_labels = None
depends_on = None


SPECIALTIES = [
    "Configuración y Soporte de Redes de Comunicación y Sistemas Operativos",
    "Administración, Logística y Distribución",
    "Contabilidad y Control Interno",
    "Contabilidad",
    "Mercadeo",
    "Ciberseguridad",
    "Electrónica Industrial",
    "Dibujo y Modelado de Edificaciones",
    "Contabilidad y Finanzas",
    "Ejecutivo Comercial y Servicio al Cliente",
    "Diseño y Desarrollo Digital",
    "Desarrollo Web",
]


def _key(value):
    value = html.unescape(value or "").strip().rstrip(".,")
    value = "".join(char for char in unicodedata.normalize("NFKD", value) if not unicodedata.combining(char))
    value = re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()
    aliases = {
        "accounting": "contabilidad",
        "administracion logistica y distribucion": "administracion logistica distribucion",
        "administracion logistica distribucion": "administracion logistica distribucion",
        "configuracion y soporte a redes de comunicacion y sistemas operativos": "configuracion soporte redes comunicacion sistemas operativos",
        "configuracion y soporte de redes de comunicacion y sistemas operativos": "configuracion soporte redes comunicacion sistemas operativos",
    }
    return aliases.get(value, value)


def upgrade():
    bind = op.get_bind()
    specialties = sa.table(
        "specialties",
        sa.column("name", sa.String(140)),
        sa.column("sort_order", sa.Integer),
        sa.column("is_active", sa.Boolean),
    )
    rows = bind.execute(sa.select(specialties.c.name, specialties.c.sort_order)).fetchall()
    existing = {_key(row.name) for row in rows}
    next_order = max((row.sort_order or 0 for row in rows), default=0) + 1
    for name in SPECIALTIES:
        if _key(name) in existing:
            continue
        bind.execute(specialties.insert().values(name=name, sort_order=next_order, is_active=True))
        existing.add(_key(name))
        next_order += 1


def downgrade():
    # No se eliminan catálogos que podrían estar referenciados por proyectos.
    pass
