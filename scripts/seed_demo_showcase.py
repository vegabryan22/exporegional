from __future__ import annotations

from datetime import date, timedelta

from app import create_app
from app.extensions import db
from app.models.assignment import Assignment
from app.models.campaign import Campaign
from app.models.category import Category
from app.models.judge import Judge
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.section import Section
from app.models.specialty import Specialty
from app.models.workshop import Workshop


JUDGE_PASSWORD = "ExpoDemo2026!"
TARGET_JUDGE_COUNT = 24
PROJECTS_PER_CATEGORY = 30

STEAM_TITLES = [
    "Huerto Inteligente Escolar",
    "Sistema de Riego con Sensores",
    "Clasificador de Residuos con Vision Basica",
    "Estacion Meteorologica del Campus",
    "Alerta de Inundacion para Aulas",
    "Medidor de Calidad del Aire Escolar",
    "Semaforo Peatonal Solar",
    "Control de Iluminacion Eficiente",
    "Monitoreo de Consumo Electrico",
    "Brazo Robot para Material Didactico",
    "Invernadero Automatizado",
    "Purificador Casero de Agua",
    "Detector de Fugas de Gas",
    "Asistente de Reciclaje para Aulas",
    "Alarma de Temperatura para Laboratorio",
    "Dispensador Inteligente de Alcohol",
    "Ruta Segura con Balizas LED",
    "Mini Planta de Compostaje Guiada",
    "Cabina de Secado Solar",
    "Control de Acceso con Tarjeta Escolar",
    "Cargador Solar para Dispositivos",
    "Sistema de Ahorro de Agua en Banos",
    "Bote de Basura con Conteo de Uso",
    "Sensor de Ruido para Biblioteca",
    "Panel de Indicadores Ambientales",
    "Alimentador Programable para Vivero",
    "Robot Seguidor de Linea Escolar",
    "Mochila con Luz de Seguridad",
    "Deteccion de Humedad en Suelos",
    "Kiosco de Informacion Interactivo",
]

ENTREPRENEUR_TITLES = [
    "EcoEmpaque Escolar",
    "Snack Saludable Tico",
    "Agenda Estudiantil Modular",
    "Marca de Velas Artesanales",
    "Uniforme Deportivo Sostenible",
    "Cafe Frio de Autor",
    "Linea de Jabones Botanicos",
    "Servicio de Impresion Academica",
    "Kit de Regalo Institucional",
    "Accesorios con Material Recuperado",
    "Cuadernos Reutilizables",
    "Tienda Digital de Manualidades",
    "Huerta en Casa por Suscripcion",
    "Reposteria Funcional Escolar",
    "Textiles Personalizados para Eventos",
    "Carteras con Lona Reciclada",
    "Estacion de Hidratacion Portatil",
    "Productos para Escritorio Creativo",
    "Linea de Salsas Artesanales",
    "Mermeladas de Frutas Locales",
    "Fotografia Express para Actos",
    "Organizacion de Ferias Tematicas",
    "Bocadillos Nutritivos para Recreo",
    "Articulos Decorativos en Madera",
    "Servicio de Branding Escolar",
    "Papeleria Creativa para Emprendedores",
    "Kits de Ciencia para Ninos",
    "Souvenirs del Colegio",
    "Bebidas Naturales Embotelladas",
    "Tienda Movil de Tecnologia Basica",
]

JUDGE_NAMES = [
    "Ana Morales",
    "Luis Herrera",
    "Sofia Calderon",
    "Diego Vargas",
    "Valeria Rojas",
    "Carlos Mendez",
    "Paola Jimenez",
    "Javier Solis",
    "Gabriela Nunez",
    "Andres Araya",
    "Monica Salazar",
    "Daniel Quesada",
    "Natalia Cordero",
    "Ricardo Campos",
    "Elena Porras",
    "Marcos Urena",
    "Tatiana Leon",
    "Fabian Chaves",
    "Camila Fonseca",
    "Esteban Brenes",
    "Melissa Roldan",
    "Pablo Hidalgo",
    "Irene Zamora",
    "Oscar Alfaro",
]

STEAM_TEAM_PREFIXES = [
    "Tecno",
    "Eco",
    "Innova",
    "Nova",
    "Aula",
    "Circuito",
    "Bio",
    "Robo",
    "Vision",
    "Pulso",
]

ENTREPRENEUR_TEAM_PREFIXES = [
    "Impulso",
    "Origen",
    "Raiz",
    "Brio",
    "Esencia",
    "Nexo",
    "Andar",
    "Viva",
    "Tierra",
    "Punto",
]

FIRST_NAMES = [
    "Mariana",
    "Jose",
    "Daniela",
    "Sebastian",
    "Fernanda",
    "Adrian",
    "Lucia",
    "Mateo",
    "Valentina",
    "Samuel",
    "Allan",
    "Paula",
    "Kevin",
    "Nicole",
    "Bryan",
    "Ashley",
    "Jorge",
    "Noelia",
    "Fabio",
    "Andrea",
]

LAST_NAMES = [
    "Vega",
    "Mora",
    "Sanchez",
    "Ramirez",
    "Castro",
    "Perez",
    "Lopez",
    "Cruz",
    "Gonzalez",
    "Navarro",
    "Murillo",
    "Rojas",
    "Alvarado",
    "Campos",
    "Bonilla",
    "Arce",
    "Madrigal",
    "Solano",
    "Valverde",
    "Chacon",
]


def _pick(sequence, index):
    return sequence[index % len(sequence)]


def _build_person(seed: int) -> tuple[str, str]:
    first = _pick(FIRST_NAMES, seed)
    last = _pick(LAST_NAMES, seed * 3 + 1)
    return f"{first} {last}", f"{first.lower()}.{last.lower()}{seed}@demo.expotecnica.local"


def _ensure_judges() -> list[Judge]:
    judges = (
        Judge.query.filter(Judge.role == Judge.ROLE_JUDGE, Judge.is_active_user.is_(True))
        .order_by(Judge.id.asc())
        .all()
    )
    if len(judges) >= TARGET_JUDGE_COUNT:
        return judges[:TARGET_JUDGE_COUNT]

    missing = TARGET_JUDGE_COUNT - len(judges)
    for index in range(missing):
        slot = len(judges) + index
        full_name = _pick(JUDGE_NAMES, slot)
        email = f"juez.demo.{slot + 1:02d}@expotecnica.local"
        existing = Judge.query.filter_by(email=email).first()
        if existing:
            continue
        judge = Judge(
            full_name=full_name,
            email=email,
            role=Judge.ROLE_JUDGE,
            is_admin=False,
            is_active_user=True,
            must_change_password=False,
            department="",
            job_title="Juez invitado",
            phone=f"7000{slot + 1:04d}",
        )
        judge.set_password(JUDGE_PASSWORD)
        db.session.add(judge)

    db.session.commit()
    return (
        Judge.query.filter(Judge.role == Judge.ROLE_JUDGE, Judge.is_active_user.is_(True))
        .order_by(Judge.id.asc())
        .limit(TARGET_JUDGE_COUNT)
        .all()
    )


def _active_campaign() -> Campaign:
    campaign = Campaign.query.filter_by(is_active=True).order_by(Campaign.start_date.desc()).first()
    if campaign:
        return campaign
    return Campaign.query.order_by(Campaign.start_date.desc(), Campaign.id.desc()).first()


def _academic_catalog():
    steam_sections = [
        section
        for section in Section.query.filter_by(is_active=True).all()
        if section.level and section.level.code in {"7", "8", "9"}
    ]
    entrepreneur_sections = [
        section
        for section in Section.query.filter_by(is_active=True).all()
        if section.level and section.level.code in {"10", "11", "12"}
    ]
    specialties = Specialty.query.filter_by(is_active=True).order_by(Specialty.sort_order.asc(), Specialty.name.asc()).all()
    workshops = Workshop.query.filter_by(is_active=True).order_by(Workshop.sort_order.asc(), Workshop.name.asc()).all()
    return steam_sections, entrepreneur_sections, specialties, workshops


def _ensure_project(title: str, category_code: str, index: int, campaign: Campaign, section: Section, focus_name: str, specialty_id: int | None, workshop_id: int | None) -> Project:
    existing = Project.query.filter_by(title=title).first()
    if existing:
        return existing

    team_prefixes = STEAM_TEAM_PREFIXES if category_code == "steam" else ENTREPRENEUR_TEAM_PREFIXES
    team_name = f"{_pick(team_prefixes, index)} {focus_name}".strip()
    representative_name, representative_email = _build_person(index * 5 + 1)
    advisor_name, advisor_email = _build_person(index * 5 + 2)
    registration_date = date.today() - timedelta(days=(index % 45))

    project = Project(
        registration_date=registration_date,
        title=title,
        team_name=team_name,
        representative_name=representative_name,
        representative_email=representative_email,
        representative_phone=f"6000{index + 1:04d}",
        institution_name="CTP Roberto Gamboa Valverde",
        grade_level=section.level.code if section.level else "",
        specialty=focus_name,
        section_id=section.id,
        specialty_id=specialty_id,
        workshop_id=workshop_id,
        campaign_id=campaign.id if campaign else None,
        advisor_name=advisor_name,
        advisor_identity=f"AD{index + 1:06d}",
        advisor_email=advisor_email,
        advisor_phone=f"7100{index + 1:04d}",
        category=category_code,
        description=(
            f"{title} es un proyecto demostrativo orientado a resolver una necesidad real del entorno estudiantil "
            f"mediante una propuesta de categoria {category_code}."
        ),
        project_objective=f"Desarrollar y validar la propuesta {title.lower()} con enfoque aplicable al contexto institucional.",
        expected_impact="Fortalecer la innovacion, el trabajo colaborativo y la presentacion tecnica del estudiantado.",
        required_resources="Conexion a corriente, internet, mesa de exhibicion y material de apoyo visual.",
        requirements_summary="corriente, internet",
        requirements_other="",
        is_active=True,
        logistics_status="pendiente_revision",
        logistics_notes="Proyecto de demostracion generado automaticamente para pruebas.",
        logistics_document_ok=False,
        logistics_logo_ok=False,
        logistics_photos_ok=False,
        consent_terms=True,
    )
    db.session.add(project)
    db.session.flush()

    member_count = 3 if index % 4 else 2
    for member_number in range(1, member_count + 1):
        member_name, member_email = _build_person(index * 10 + member_number)
        db.session.add(
            ProjectMember(
                project_id=project.id,
                student_number=member_number,
                full_name=member_name,
                identity_number=f"ST{index + 1:04d}{member_number}",
                gender="femenino" if (index + member_number) % 2 == 0 else "masculino",
                specialty=focus_name,
                section_name=section.name,
                has_dining_scholarship=member_number == 1 and index % 5 == 0,
                participates_in_english=(index + member_number) % 3 == 0,
                phone=f"8800{index + 1:04d}{member_number}",
                email=member_email,
            )
        )

    return project


def _assign_three_judges(projects: list[Project], judges: list[Judge]) -> int:
    created = 0
    total_judges = len(judges)
    for index, project in enumerate(projects):
        judge_positions = [index % total_judges, (index + 7) % total_judges, (index + 13) % total_judges]
        used = set()
        for position in judge_positions:
            judge = judges[position]
            if judge.id in used:
                continue
            used.add(judge.id)
            exists = Assignment.query.filter_by(project_id=project.id, judge_id=judge.id).first()
            if exists:
                continue
            db.session.add(Assignment(project_id=project.id, judge_id=judge.id))
            created += 1
    return created


def seed():
    campaign = _active_campaign()
    if not campaign:
        raise RuntimeError("No hay campaña disponible para asociar los proyectos demo.")

    steam_category = Category.query.filter_by(code="steam", is_active=True).first()
    entrepreneur_category = Category.query.filter_by(code="emprendimiento", is_active=True).first()
    if not steam_category or not entrepreneur_category:
        raise RuntimeError("Se requieren las categorias activas 'steam' y 'emprendimiento'.")

    steam_sections, entrepreneur_sections, specialties, workshops = _academic_catalog()
    if not steam_sections or not entrepreneur_sections or not specialties or not workshops:
        raise RuntimeError("Faltan secciones, especialidades o talleres activos para generar la muestra.")

    judges = _ensure_judges()
    projects = []

    for index, title_base in enumerate(STEAM_TITLES[:PROJECTS_PER_CATEGORY], start=1):
        section = steam_sections[(index - 1) % len(steam_sections)]
        workshop = workshops[(index - 1) % len(workshops)]
        title = f"STEAM Demo {index:02d} - {title_base}"
        projects.append(
            _ensure_project(
                title=title,
                category_code=steam_category.code,
                index=index,
                campaign=campaign,
                section=section,
                focus_name=workshop.name,
                specialty_id=None,
                workshop_id=workshop.id,
            )
        )

    for index, title_base in enumerate(ENTREPRENEUR_TITLES[:PROJECTS_PER_CATEGORY], start=1):
        section = entrepreneur_sections[(index - 1) % len(entrepreneur_sections)]
        specialty = specialties[(index - 1) % len(specialties)]
        title = f"Emprendimiento Demo {index:02d} - {title_base}"
        projects.append(
            _ensure_project(
                title=title,
                category_code=entrepreneur_category.code,
                index=100 + index,
                campaign=campaign,
                section=section,
                focus_name=specialty.name,
                specialty_id=specialty.id,
                workshop_id=None,
            )
        )

    assignment_count = _assign_three_judges(projects, judges)
    db.session.commit()

    judge_load = {judge.id: Assignment.query.filter_by(judge_id=judge.id).count() for judge in judges}
    print("Seed completado.")
    print(f"Campana usada: {campaign.name} (ID {campaign.id})")
    print(f"Jueces disponibles para muestra: {len(judges)}")
    print(f"Proyectos demo STEAM: {len([p for p in projects if p.category == 'steam'])}")
    print(f"Proyectos demo Emprendimiento: {len([p for p in projects if p.category == 'emprendimiento'])}")
    print(f"Asignaciones nuevas creadas: {assignment_count}")
    print(f"Minimo de proyectos por juez en la muestra: {min(judge_load.values()) if judge_load else 0}")
    print(f"Contrasena para jueces demo nuevos: {JUDGE_PASSWORD}")


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        seed()
