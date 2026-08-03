import json
from datetime import datetime

from app.extensions import db


class Project(db.Model):
    __tablename__ = "projects"
    __table_args__ = (
        db.UniqueConstraint("institution_id", "external_project_id", name="uq_project_institution_external_id"),
    )
    GENERIC_LOGO_PATH = "placeholders/project-logo-generic.svg"

    ORIGIN_INSTITUTIONAL_API = "institutional_api"
    ORIGIN_REGIONAL_MANUAL = "regional_manual"
    VALID_ORIGINS = {ORIGIN_INSTITUTIONAL_API, ORIGIN_REGIONAL_MANUAL}

    STATUS_DRAFT = "draft"
    STATUS_SUBMITTED = "submitted_by_school"
    STATUS_RECEIVED = "received"
    STATUS_UNDER_REVIEW = "under_review"
    STATUS_APPROVED = "approved_for_evaluation"
    STATUS_RETURNED = "returned_for_correction"
    STATUS_EVALUATED = "evaluated"
    STATUS_REGIONAL_WINNER = "regional_winner"
    VALID_REGIONAL_STATUSES = {
        STATUS_DRAFT,
        STATUS_SUBMITTED,
        STATUS_RECEIVED,
        STATUS_UNDER_REVIEW,
        STATUS_APPROVED,
        STATUS_RETURNED,
        STATUS_EVALUATED,
        STATUS_REGIONAL_WINNER,
    }

    id = db.Column(db.Integer, primary_key=True)
    registration_date = db.Column(db.Date, nullable=True)
    title = db.Column(db.String(180), nullable=False)
    team_name = db.Column(db.String(180), nullable=False)
    representative_name = db.Column(db.String(120), nullable=False)
    representative_email = db.Column(db.String(120), nullable=False)
    representative_phone = db.Column(db.String(40), nullable=True)
    institution_name = db.Column(db.String(180), nullable=True)
    institution_id = db.Column(db.Integer, db.ForeignKey("institutions.id", ondelete="RESTRICT"), nullable=True, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True)
    origin = db.Column(db.String(30), nullable=False, default=ORIGIN_REGIONAL_MANUAL, index=True)
    regional_status = db.Column(db.String(40), nullable=False, default=STATUS_DRAFT, index=True)
    external_project_id = db.Column(db.String(120), nullable=True)
    external_source = db.Column(db.String(160), nullable=True)
    source_updated_at = db.Column(db.DateTime, nullable=True)
    received_at = db.Column(db.DateTime, nullable=True)
    submitted_at = db.Column(db.DateTime, nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    approved_by_id = db.Column(db.Integer, db.ForeignKey("judges.id", ondelete="SET NULL"), nullable=True, index=True)
    regional_notes = db.Column(db.Text, nullable=True)
    payload_version = db.Column(db.String(20), nullable=True)
    grade_level = db.Column(db.String(60), nullable=True)
    specialty = db.Column(db.String(120), nullable=True)
    section_id = db.Column(db.Integer, db.ForeignKey("sections.id"), nullable=True, index=True)
    specialty_id = db.Column(db.Integer, db.ForeignKey("specialties.id"), nullable=True, index=True)
    thematic_axis_id = db.Column(db.Integer, db.ForeignKey("thematic_axes.id"), nullable=True, index=True)
    project_type_id = db.Column(db.Integer, db.ForeignKey("project_types.id"), nullable=True, index=True)
    workshop_id = db.Column(db.Integer, db.ForeignKey("workshops.id"), nullable=True, index=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey("campaigns.id"), nullable=True, index=True)
    tutor_id = db.Column(db.Integer, db.ForeignKey("tutors.id"), nullable=True, index=True)
    advisor_name = db.Column(db.String(120), nullable=True)
    advisor_identity = db.Column(db.String(40), nullable=True)
    advisor_birth_date = db.Column(db.Date, nullable=True)
    advisor_gender = db.Column(db.String(20), nullable=True)
    advisor_specialty = db.Column(db.String(140), nullable=True)
    advisor_email = db.Column(db.String(120), nullable=True)
    advisor_phone = db.Column(db.String(40), nullable=True)
    mentor_name = db.Column(db.String(120), nullable=True)
    mentor_identity = db.Column(db.String(40), nullable=True)
    mentor_birth_date = db.Column(db.Date, nullable=True)
    mentor_gender = db.Column(db.String(20), nullable=True)
    mentor_specialty = db.Column(db.String(140), nullable=True)
    mentor_email = db.Column(db.String(120), nullable=True)
    mentor_phone = db.Column(db.String(40), nullable=True)
    category = db.Column(db.String(60), nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    project_objective = db.Column(db.Text, nullable=True)
    expected_impact = db.Column(db.Text, nullable=True)
    required_resources = db.Column(db.Text, nullable=True)
    requirements_items_json = db.Column(db.Text, nullable=True)
    project_start_date = db.Column(db.Date, nullable=True)
    project_end_date = db.Column(db.Date, nullable=True)
    requirements_summary = db.Column(db.Text, nullable=True)
    requirements_other = db.Column(db.String(255), nullable=True)
    requirements_status = db.Column(db.String(40), nullable=False, default="pendiente_revision", index=True)
    requirements_notes = db.Column(db.Text, nullable=True)
    requirements_current_ok = db.Column(db.Boolean, nullable=False, default=False)
    requirements_outlets_ok = db.Column(db.Boolean, nullable=False, default=False)
    requirements_internet_ok = db.Column(db.Boolean, nullable=False, default=False)
    requirements_water_ok = db.Column(db.Boolean, nullable=False, default=False)
    requirements_other_ok = db.Column(db.Boolean, nullable=False, default=False)
    requirements_resources_ok = db.Column(db.Boolean, nullable=False, default=False)
    project_document_path = db.Column(db.String(300), nullable=True)
    project_logo_path = db.Column(db.String(300), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    logistics_status = db.Column(db.String(40), nullable=False, default="pendiente_revision", index=True)
    logistics_notes = db.Column(db.Text, nullable=True)
    logistics_document_ok = db.Column(db.Boolean, nullable=False, default=False)
    logistics_logo_ok = db.Column(db.Boolean, nullable=False, default=False)
    logistics_photos_ok = db.Column(db.Boolean, nullable=False, default=False)
    logistics_registration_form_signed_ok = db.Column(db.Boolean, nullable=False, default=False)
    logistics_student_consents_signed_ok = db.Column(db.Boolean, nullable=False, default=False)
    logistics_cedula_tutor_ok = db.Column(db.Boolean, nullable=False, default=False)
    logistics_requirements_reviewed_ok = db.Column(db.Boolean, nullable=False, default=False)
    consent_terms = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    assignments = db.relationship("Assignment", back_populates="project", cascade="all, delete-orphan")
    evaluations = db.relationship("Evaluation", back_populates="project")
    members = db.relationship("ProjectMember", back_populates="project", cascade="all, delete-orphan")
    member_changes = db.relationship("ProjectMemberChange", back_populates="project", cascade="all, delete-orphan")
    member_edit_requests = db.relationship(
        "ProjectMemberEditRequest",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="ProjectMemberEditRequest.created_at",
    )
    document_revisions = db.relationship(
        "ProjectDocumentRevision",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="ProjectDocumentRevision.created_at",
    )
    section = db.relationship("Section")
    specialty_ref = db.relationship("Specialty")
    thematic_axis = db.relationship("ThematicAxis")
    project_type = db.relationship("ProjectType")
    workshop_ref = db.relationship("Workshop")
    campaign = db.relationship("Campaign", back_populates="projects")
    tutor = db.relationship("Tutor", back_populates="projects")
    institution = db.relationship("Institution", back_populates="projects")
    category_ref = db.relationship("Category", foreign_keys=[category_id])
    approved_by = db.relationship("Judge", foreign_keys=[approved_by_id])
    status_history = db.relationship(
        "ProjectStatusHistory",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="ProjectStatusHistory.created_at",
    )

    @property
    def origin_label(self) -> str:
        return {
            self.ORIGIN_INSTITUTIONAL_API: "Importación institucional",
            self.ORIGIN_REGIONAL_MANUAL: "Inscripción manual regional",
        }.get(self.origin, self.origin)

    @property
    def regional_status_label(self) -> str:
        return {
            self.STATUS_DRAFT: "Borrador",
            self.STATUS_SUBMITTED: "Enviado por colegio",
            self.STATUS_RECEIVED: "Recibido",
            self.STATUS_UNDER_REVIEW: "En revisión",
            self.STATUS_APPROVED: "Aprobado para evaluación",
            self.STATUS_RETURNED: "Devuelto para corrección",
            self.STATUS_EVALUATED: "Evaluado",
            self.STATUS_REGIONAL_WINNER: "Ganador regional",
        }.get(self.regional_status, self.regional_status)

    @property
    def has_real_logo(self) -> bool:
        return bool(self.project_logo_path) and self.project_logo_path != self.GENERIC_LOGO_PATH

    @property
    def display_logo_path(self) -> str:
        return self.project_logo_path if self.has_real_logo else self.GENERIC_LOGO_PATH

    @property
    def requires_english_evaluation(self) -> bool:
        return any(bool(member.participates_in_english) for member in self.members)

    @property
    def english_members(self):
        return [member for member in self.members if bool(member.participates_in_english)]

    @property
    def english_members_count(self) -> int:
        return len(self.english_members)

    @property
    def logistics_requirements_complete(self) -> bool:
        return all(
            [
                bool(self.project_document_path),
                self.logistics_document_ok,
                self.has_real_logo,
                self.logistics_logo_ok,
                self.logistics_photos_ok,
                self.logistics_registration_form_signed_ok,
                self.logistics_student_consents_signed_ok,
            ]
        )

    @property
    def requested_requirement_codes(self) -> set[str]:
        return {
            item.strip().lower()
            for item in (self.requirements_summary or "").split(",")
            if item.strip()
        }

    @property
    def detailed_requirement_items(self) -> list[dict]:
        try:
            raw_items = json.loads(self.requirements_items_json or "[]")
        except (TypeError, ValueError):
            raw_items = []

        items = []
        for index, raw_item in enumerate(raw_items):
            if not isinstance(raw_item, dict):
                continue
            name = str(raw_item.get("name") or "").strip()
            if not name:
                continue
            items.append(
                {
                    "id": str(raw_item.get("id") or f"item-{index + 1}"),
                    "name": name,
                    "quantity": str(raw_item.get("quantity") or "").strip(),
                    "unit": str(raw_item.get("unit") or "").strip(),
                    "notes": str(raw_item.get("notes") or "").strip(),
                    "confirmed": bool(raw_item.get("confirmed")),
                    "legacy": False,
                }
            )

        if not items and (self.required_resources or "").strip():
            items.append(
                {
                    "id": "legacy",
                    "name": (self.required_resources or "").strip(),
                    "quantity": "",
                    "unit": "",
                    "notes": "Información histórica pendiente de desglosar.",
                    "confirmed": bool(self.requirements_resources_ok),
                    "legacy": True,
                }
            )
        return items

    @property
    def requirements_missing_items(self) -> list[str]:
        labels = {
            "corriente": ("Conexión a corriente", self.requirements_current_ok),
            "salidas": ("Salidas eléctricas", self.requirements_outlets_ok),
            "internet": ("Acceso a internet", self.requirements_internet_ok),
            "agua": ("Acceso a agua", self.requirements_water_ok),
            "otros": ("Otros requerimientos", self.requirements_other_ok),
        }
        missing = [
            label
            for code, (label, confirmed) in labels.items()
            if code in self.requested_requirement_codes and not confirmed
        ]
        unconfirmed_items = [item for item in self.detailed_requirement_items if not item["confirmed"]]
        if unconfirmed_items:
            missing.append(
                "Insumos pendientes: " + ", ".join(item["name"] for item in unconfirmed_items)
            )
        return missing

    @property
    def requirements_complete(self) -> bool:
        if self.requirements_status == "no_aplica":
            return not self.requested_requirement_codes and not self.detailed_requirement_items
        return self.requirements_status == "completo" and not self.requirements_missing_items
