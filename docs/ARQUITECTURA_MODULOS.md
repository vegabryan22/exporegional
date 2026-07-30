# Arquitectura de Modulos de ExpoTecnica

## 1. Objetivo

Este documento describe la arquitectura funcional real del sistema ExpoTecnica de forma entendible para QA.

No está pensado como documento de desarrollo profundo. Está pensado para que el equipo de QA pueda responder rápido:

- que modulos existen
- quien usa cada modulo
- que pantallas intervienen
- que entidades afecta cada flujo
- de que otros modulos depende
- donde estan los puntos mas sensibles para pruebas

## 2. Visión general

ExpoTecnica es una aplicación web monolítica construida con Flask y SQLAlchemy.

El sistema se divide en 4 grandes áreas:

1. Área pública
   - Home
   - Listado de proyectos
   - Inscripción de proyectos
2. Área de autenticación
   - Login
   - Cambio de contraseña
   - Logout
3. Área de jueces
   - Panel de proyectos asignados
   - Registro de evaluaciones
4. Área administrativa
   - Configuración, operación, catálogos, evaluaciones, mantenimiento y auditoría

## 3. Capas del sistema

### 3.1 Rutas

Definen la URL y delegan el trabajo a controladores.

- `app/routes/public_routes.py`
- `app/routes/auth_routes.py`
- `app/routes/judge_routes.py`
- `app/routes/admin_routes.py`

### 3.2 Controladores

Resuelven la lógica de negocio principal.

- `app/controllers/project_controller.py`
- `app/controllers/auth_controller.py`
- `app/controllers/evaluation_controller.py`
- `app/controllers/admin_controller.py`

### 3.3 Modelos

Representan la información persistente.

Modelos más importantes:

- `Judge`
- `Project`
- `ProjectMember`
- `Assignment`
- `EvaluationType`
- `RubricCriterion`
- `Evaluation`
- `EvaluationScore`
- `Campaign`
- `Category`
- `Level`
- `Section`
- `Specialty`
- `Workshop`
- `SystemSetting`
- `SystemAuditLog`

### 3.4 Servicios

Encapsulan lógica transversal.

- `app/services/evaluation_service.py`
- `app/services/parameter_service.py`
- `app/services/mail_service.py`
- `app/services/audit_service.py`

### 3.5 Vistas

Renderizan la interfaz.

- `app/templates/public/*`
- `app/templates/auth/*`
- `app/templates/judge/*`
- `app/templates/admin/*`

## 4. Mapa de roles

### 4.1 Visitante

Puede:

- ver home
- ver proyectos activos
- abrir inscripción si hay campaña activa

No puede:

- evaluar
- entrar al panel admin
- ver panel de juez

### 4.2 Juez

Puede:

- iniciar sesión
- cambiar contraseña
- ver proyectos asignados
- evaluar solo proyectos asignados

No puede:

- administrar catalogos
- editar proyectos
- administrar usuarios

### 4.3 Administrador por departamento

Puede entrar al panel admin, pero los módulos visibles dependen de:

- departamento
- matriz de permisos por departamento

Departamentos actuales:

- Logística
- Datos
- Diseño
- QA

### 4.4 Superadministrador

Tiene acceso total a todos los módulos, incluyendo permisos.

## 5. Módulos funcionales

## 5.1 Home público

Ruta:

- `/`

Controlador:

- `project_controller.home_intro()`

Vista:

- `app/templates/public/home_intro.html`

Objetivo:

- presentar la ExpoTecnica
- mostrar identidad visual del colegio y de la expo
- mostrar logos o imágenes de proyectos activos

Entidades consultadas:

- `Project`
- `Category`
- `SystemSetting`

Dependencias:

- solo muestra proyectos activos
- usa `expo_logo_path` para branding del evento

Puntos criticos para QA:

- carga de branding
- proyectos inactivos no deben aparecer
- carrusel no debe romperse si faltan logos reales

## 5.2 Listado público de proyectos

Ruta:

- `/proyectos`

Controlador:

- `project_controller.list_projects()`

Vista:

- `app/templates/public/home_projects.html`

Objetivo:

- mostrar proyectos activos por categoria
- exponer documento del proyecto si existe
- permitir acceso a evaluacion escrita del proyecto

Entidades:

- `Project`
- `ProjectMember`
- `Category`

Dependencias:

- branding del evento
- logo real o placeholder del proyecto
- fotos reales o placeholders por genero

Puntos criticos:

- no mostrar proyectos inactivos
- placeholder visual no debe contarse como logo real
- documento debe abrir solo si existe

## 5.3 Inscripcion de proyectos

Ruta:

- `/inscripcion`

Controlador:

- `project_controller.register_project()`

Vista:

- `app/templates/public/register_project.html`

Objetivo:

- registrar proyectos con formato ExpoTEC-1
- capturar datos del proyecto
- capturar 1 a 3 estudiantes
- guardar documento del proyecto

Entidades:

- `Campaign`
- `Project`
- `ProjectMember`
- `Category`
- `Section`
- `Specialty`
- `Workshop`

Dependencias:

- requiere campaña activa
- usa borrador en sesión
- valida documento permitido

Puntos críticos:

- si no hay campaña activa no debe permitir inscribir
- debe guardar solo estudiantes requeridos
- debe conservar borrador al corregir errores
- debe promover documento temporal a documento final

## 5.4 Login y sesion

Rutas:

- `/auth/login`
- `/auth/cambiar-contrasena`
- `/auth/logout`

Controlador:

- `auth_controller`

Vistas:

- `app/templates/auth/login.html`
- `app/templates/auth/change_password.html`

Objetivo:

- autenticar usuarios
- forzar cambio de contrasena si aplica
- redirigir segun rol

Entidades:

- `Judge`
- `SystemAuditLog`

Puntos criticos:

- credenciales invalidas
- usuario inactivo
- cambio obligatorio de contraseña
- redirección por `next`

## 5.5 Panel de juez

Rutas:

- `/juez/panel`
- `/juez/proyecto/<id>/evaluar`

Controlador:

- `evaluation_controller.dashboard()`
- `evaluation_controller.evaluate()`

Vistas:

- `app/templates/judge/dashboard.html`
- `app/templates/judge/evaluate.html`

Objetivo:

- mostrar proyectos asignados
- mostrar tipos de evaluacion disponibles por proyecto
- registrar una evaluacion por juez, proyecto y tipo

Entidades:

- `Assignment`
- `Project`
- `Evaluation`
- `EvaluationScore`
- `EvaluationType`
- `RubricCriterion`

Dependencias:

- `evaluation_service.get_project_available_evaluation_types`
- `parameter_service.get_active_rubrics_map`

Puntos criticos:

- un juez no debe evaluar proyectos no asignados
- un juez no debe duplicar evaluacion del mismo tipo
- puntajes deben respetar min y max de cada rubrica
- porcentaje final de la evaluacion debe calcularse correctamente

## 5.6 Panel administrativo

Ruta base:

- `/admin/*`

Layout:

- `app/templates/admin/layout.html`

Controlador base:

- `admin_controller._base_context()`

Objetivo:

- construir menu segun permisos
- inyectar catalogos, settings y datos comunes

Dependencias criticas:

- `Judge` actual
- matriz de permisos por departamento
- `SystemSetting`

Puntos criticos:

- el menu debe cambiar por rol y departamento
- el superadmin debe ver todo
- usuarios sin permiso no deben ejecutar acciones ni entrar a vistas

## 5.7 Modulo Resumen

Ruta:

- `/admin/panel`

Vista:

- `app/templates/admin/overview.html`

Objetivo:

- actuar como centro de operaciones
- priorizar pendientes reales

Indicadores actuales:

- proyectos activos
- proyectos sin jueces
- evaluaciones pendientes
- pendientes de revision
- estudiantes sin foto
- proyectos sin logo real
- proyectos sin documento
- logistica incompleta

Puntos criticos:

- debe considerar solo proyectos activos
- logo generico no debe contarse como logo real

## 5.8 Modulo Asignaciones

Ruta:

- `/admin/asignaciones`

Vista:

- `app/templates/admin/assignments.html`

Objetivo:

- asignar jueces a proyectos activos
- reemplazar jueces rapidamente
- crear juez rapido y asignarlo

Entidades:

- `Assignment`
- `Judge`
- `Project`

Puntos criticos:

- no duplicar asignacion del mismo juez en el mismo proyecto
- solo trabajar con proyectos activos
- contador de asignaciones debe responder a proyectos activos

## 5.9 Modulo Usuarios

Ruta:

- `/admin/jueces`

Vista:

- `app/templates/admin/judges.html`

Objetivo:

- administrar usuarios del sistema

Tipos de usuario:

- Juez
- Administrador
- Superadministrador

Reglas importantes:

- Juez no requiere departamento
- usuario administrativo generico requiere departamento
- solo debe existir un usuario generico por departamento

Puntos criticos:

- validacion de correo unico
- activacion e inactivacion
- contrasena manual o temporal

## 5.10 Modulo Permisos

Ruta:

- `/admin/permisos`

Vista:

- `app/templates/admin/permissions.html`

Objetivo:

- definir que modulos puede usar cada departamento administrativo

Dependencias:

- `SystemSetting`
- `Judge.department`
- `Judge.role`

Puntos criticos:

- solo superadmin puede editar
- overview siempre debe permanecer accesible para admins

## 5.11 Modulo Campanas

Ruta:

- `/admin/campanas`

Vista:

- `app/templates/admin/campaigns.html`

Objetivo:

- abrir y cerrar periodos de inscripcion

Entidad:

- `Campaign`

Puntos criticos:

- fechas validas
- solo una campana activa segun reglas de negocio
- la inscripcion publica depende de esto

## 5.12 Modulo Categorias

Ruta:

- `/admin/categorias`

Vista:

- `app/templates/admin/categories.html`

Objetivo:

- administrar categorias visibles
- relacionar categoría con evaluación de Exposición y Documentación

Entidad:

- `Category`

Puntos críticos:

- cada categoría debe tener una rúbrica de exposición y una de documentación
- no se debe mezclar con inglés

## 5.13 Modulo Academico

Ruta:

- `/admin/academico`

Vista:

- `app/templates/admin/academic.html`

Objetivo:

- administrar niveles, secciones, especialidades y talleres

Entidades:

- `Level`
- `Section`
- `Specialty`
- `Workshop`

Puntos criticos:

- no eliminar catalogos con proyectos asociados
- orden y activacion deben reflejarse en la inscripcion

## 5.14 Modulo Rubricas

Ruta:

- `/admin/rubricas`

Vista:

- `app/templates/admin/rubrics.html`

Objetivo:

- administrar tipos de evaluacion
- administrar criterios de rubrica

Conceptos clave:

- `name`: nombre corto
- `description`: descripcion larga

Puntos criticos:

- no recrear defaults eliminados manualmente
- tipos con rubricas no deben eliminarse sin limpiar dependencias
- puntos maximos visibles deben corresponder a la suma de criterios activos

## 5.15 Modulo Proyectos

Ruta:

- `/admin/proyectos`

Vista:

- `app/templates/admin/projects.html`

Objetivo:

- mantener proyectos
- controlar la recepción y revisión logística
- validar documentación, formularios, fotografías e integrantes
- cargar logo real del proyecto
- administrar integrantes y fotos

Entidades:

- `Project`
- `ProjectMember`
- `ProjectMemberChange`

Puntos criticos:

- logo generico es solo visual, no cumplimiento logistico
- foto generica es solo visual, no cumplimiento logistico
- cargas de archivos deben reemplazar correctamente
- los contadores de pendientes enlazan al reporte Excel `/admin/logistica/pendientes/reporte.xlsx`
- cada fila del reporte identifica pendiente, persona afectada, seccion, proyecto y tutor
- el centro `/admin/proyectos/recordatorio` permite envios masivos o por proyecto a estudiantes, tutores o ambas audiencias
- todo envio omite destinatarios sin correo y registra audiencia, proyectos y resultado en la auditoria

## 5.15.1 Modulo Requerimientos

Ruta:

- `/admin/requerimientos`

Vista:

- `app/templates/admin/requirements.html`

Objetivo:

- separar los requerimientos técnicos y de insumos del cierre logístico
- dar seguimiento a electricidad, tomacorrientes, internet, agua y otros recursos
- registrar el estado y las observaciones del responsable

Entidad:

- `Project`

Campos principales:

- `requirements_status`
- `requirements_notes`
- `requirements_current_ok`
- `requirements_outlets_ok`
- `requirements_internet_ok`
- `requirements_water_ok`
- `requirements_other_ok`
- `requirements_resources_ok`

Puntos críticos:

- el módulo utiliza un permiso independiente
- Logística no recibe este permiso automáticamente
- un requerimiento pendiente no impide completar la revisión logística
- un proyecto con recursos solicitados no puede marcarse como `no_aplica`
- el estado `completo` exige que todos los recursos solicitados estén atendidos

## 5.16 Modulo Evaluaciones

Ruta:

- `/admin/evaluaciones`

Vista:

- `app/templates/admin/evaluations.html`

Objetivo:

- seguimiento del estado de evaluaciones
- ranking de ingles
- resultado por categoria
- avance por proyecto

Dependencias:

- `evaluation_service.build_admin_evaluation_overview`

Puntos criticos:

- solo considerar proyectos activos
- exposicion y documentacion deben identificarse correctamente
- nota final se basa en aportes de las rubricas principales

## 5.17 Modulo SMTP

Ruta:

- `/admin/smtp`

Objetivo:

- configurar correo saliente y probar envio

Dependencias:

- `mail_service`
- `SystemSetting`

Puntos criticos:

- guardar host, puerto y credenciales
- diferenciar TLS y SSL

## 5.18 Modulo Institucion

Ruta:

- `/admin/institucion`

Objetivo:

- mantener datos institucionales
- cargar logo del colegio
- cargar logo de ExpoTecnica

Dependencias:

- `SystemSetting`

Puntos criticos:

- no mezclar logo del colegio con logo de la expo
- branding debe reflejarse en home, formulario y login

## 5.19 Modulo Mantenimiento

Ruta:

- `/admin/mantenimiento`

Objetivo:

- habilitar o deshabilitar modo mantenimiento publico
- definir mensaje e imagen

Dependencias:

- `SystemSetting`

Puntos criticos:

- admins deben poder seguir entrando
- visitantes deben ver pantalla de mantenimiento

## 5.20 Modulo Bitacora

Ruta:

- `/admin/bitacora`

Objetivo:

- consultar trazabilidad de eventos

Entidad:

- `SystemAuditLog`

Puntos criticos:

- login, logout y acciones administrativas deben quedar registradas

## 6. Entidades centrales

## 6.1 Project

Es la entidad central del negocio.

Se conecta con:

- `ProjectMember`
- `Assignment`
- `Evaluation`
- `Campaign`
- `Section`
- `Specialty`
- `Workshop`

## 6.2 Judge

Es la entidad central de usuarios.

Se conecta con:

- login
- roles
- permisos admin
- asignaciones
- evaluaciones

## 6.3 EvaluationType y RubricCriterion

Definen la estructura de evaluacion del sistema.

Se conectan con:

- categorias
- panel de juez
- resumen de evaluaciones

## 7. Flujos principales

## 7.1 Flujo de inscripcion

1. Admin activa campana
2. Visitante entra a inscripcion
3. Sistema valida campana activa
4. Usuario llena formulario y adjunta documento
5. Sistema crea `Project`
6. Sistema crea `ProjectMember`

## 7.2 Flujo de asignacion y evaluacion

1. Admin crea o selecciona jueces
2. Admin asigna jueces a proyectos
3. Juez entra a su panel
4. Juez abre tipo de evaluacion disponible
5. Sistema valida asignacion y no duplicidad
6. Sistema registra `Evaluation` y `EvaluationScore`

## 7.3 Flujo de cierre administrativo

1. Logística revisa documentación, formularios, fotografías, integrantes y asignación de jueces
2. El responsable de requerimientos atiende por separado electricidad, tomacorrientes, internet, agua e insumos
3. Ambos responsables registran sus observaciones y estados sin bloquearse mutuamente
4. Admin consulta el estado de evaluaciones
5. Sistema calcula avance, ranking y nota final

## 8. Puntos de mayor riesgo para QA

- permisos por rol y por departamento
- campanas activas vs inscripcion publica
- consistencia entre categoria y tipos de evaluacion
- no duplicidad de evaluaciones
- calculo de nota final
- diferencia entre placeholder visual y evidencia real cargada
- independencia entre cumplimiento logístico y requerimientos técnicos
- filtros por proyectos activos
- cargas y reemplazo de archivos

## 9. Documento complementario para QA

El plan detallado de pruebas esta en:

- `docs/MODELO_PRUEBAS_QA.md`
