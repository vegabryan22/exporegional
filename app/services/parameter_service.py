import json

from app.models.category import Category
from app.models.evaluation_type import EvaluationType
from app.models.level import Level
from app.models.rubric_criterion import RubricCriterion
from app.models.section import Section
from app.models.specialty import Specialty
from app.models.system_setting import SystemSetting
from app.models.workshop import Workshop


DEFAULT_CATEGORIES = [
    {"code": "steam", "name": "STEAM", "sort_order": 1},
    {"code": "emprendimiento", "name": "Emprendimiento", "sort_order": 2},
]

DEFAULT_LEVELS = [
    {"code": "7", "name": "Septimo", "sort_order": 7},
    {"code": "8", "name": "Octavo", "sort_order": 8},
    {"code": "9", "name": "Noveno", "sort_order": 9},
    {"code": "10", "name": "Decimo", "sort_order": 10},
    {"code": "11", "name": "Undecimo", "sort_order": 11},
    {"code": "12", "name": "Duodecimo", "sort_order": 12},
]

DEFAULT_SECTIONS = [
    {"level_code": "7", "name": "7-1", "sort_order": 1},
    {"level_code": "8", "name": "8-1", "sort_order": 1},
    {"level_code": "9", "name": "9-1", "sort_order": 1},
    {"level_code": "10", "name": "10-1", "sort_order": 1},
    {"level_code": "11", "name": "11-1", "sort_order": 1},
    {"level_code": "12", "name": "12-1", "sort_order": 1},
]

DEFAULT_SPECIALTIES = [
    {"name": "Especialidad 1", "sort_order": 1},
    {"name": "Especialidad 2", "sort_order": 2},
]

DEFAULT_WORKSHOPS = [
    {"name": "Taller 1", "sort_order": 1},
    {"name": "Taller 2", "sort_order": 2},
]

DEFAULT_EVALUATION_TYPES = [
    {"code": "escrito", "name": "Escrito", "description": "Escrito", "sort_order": 1},
    {"code": "exposicion", "name": "Exposicion", "description": "Exposicion", "sort_order": 2},
    {"code": "steam_exposicion", "name": "Exposicion STEAM", "description": "Evaluacion de la Exposicion del Proyecto (Desafio STEAM)", "sort_order": 3, "scale_labels": json.dumps({3: "Logrado", 2: "Parcialmente logrado", 1: "No logrado", 0: "Ausente"})},
    {"code": "modelo_negocio_exposicion", "name": "Exposicion modelo de negocios", "description": "Evaluacion de la Exposicion del Modelo de Negocios", "sort_order": 4, "scale_labels": json.dumps({3: "Logrado", 2: "Parcialmente logrado", 1: "No logrado", 0: "Ausente"})},
    {"code": "steam_informe_bitacora", "name": "Documentacion STEAM", "description": "Evaluacion del Informe Escrito y Bitacora del Proyecto (Desafio STEAM)", "sort_order": 5, "scale_labels": json.dumps({3: "Logrado", 2: "Parcialmente logrado", 1: "No logrado", 0: "Ausente"})},
    {"code": "modelo_negocio_documento", "name": "Documento modelo de negocios", "description": "Evaluacion del Documento Escrito del Modelo de Negocios", "sort_order": 6, "scale_labels": json.dumps({3: "Logrado", 2: "Parcialmente logrado", 1: "No logrado", 0: "Ausente"})},
    {"code": "plan_negocio_documento", "name": "Documento plan de negocios", "description": "Evaluacion del Documento Escrito del Plan de Negocios", "sort_order": 7, "scale_labels": json.dumps({3: "Logrado", 2: "Parcialmente logrado", 1: "No logrado", 0: "Ausente"})},
    {"code": "english_project_performance", "name": "Exposicion en ingles", "description": "Assessment Rubric for English Project Performance", "sort_order": 8, "scale_labels": json.dumps({5: "Exceptional", 4: "Very Good", 3: "Average", 2: "Below Average", 1: "Unsatisfactory"})},
]

DEFAULT_RUBRICS = {
    "escrito": [
        {"name": "Dominio del tema", "min_score": 1, "max_score": 25, "sort_order": 1},
        {"name": "Metodologia", "min_score": 1, "max_score": 25, "sort_order": 2},
        {"name": "Innovacion", "min_score": 1, "max_score": 25, "sort_order": 3},
        {"name": "Impacto", "min_score": 1, "max_score": 25, "sort_order": 4},
    ],
    "exposicion": [
        {"name": "Claridad", "min_score": 1, "max_score": 25, "sort_order": 1},
        {"name": "Contenido", "min_score": 1, "max_score": 25, "sort_order": 2},
        {"name": "Argumentacion", "min_score": 1, "max_score": 25, "sort_order": 3},
        {"name": "Presentacion", "min_score": 1, "max_score": 25, "sort_order": 4},
    ],
    "steam_exposicion": [
        {"section_name": "I. Identificacion y formulacion del problema", "section_sort_order": 1, "name": "Define el problema de forma precisa.", "min_score": 0, "max_score": 3, "sort_order": 1},
        {"section_name": "I. Identificacion y formulacion del problema", "section_sort_order": 1, "name": "Plantea alternativas de solucion que contemplen conceptos teoricos practicos atinentes al problema.", "min_score": 0, "max_score": 3, "sort_order": 2},
        {"section_name": "I. Identificacion y formulacion del problema", "section_sort_order": 1, "name": "Propone objetivos vinculados con la busqueda de soluciones al problema planteado.", "min_score": 0, "max_score": 3, "sort_order": 3},
        {"section_name": "I. Identificacion y formulacion del problema", "section_sort_order": 1, "name": "Evidencia el impacto del proyecto a nivel social, cientifico o tecnologico, tanto a corto como largo plazo.", "min_score": 0, "max_score": 3, "sort_order": 4},
        {"section_name": "I. Identificacion y formulacion del problema", "section_sort_order": 1, "name": "Demuestra capacidad para expresar ideas con seguridad y defender el proyecto planteado.", "min_score": 0, "max_score": 3, "sort_order": 5},
        {"section_name": "II. Investigacion y desarrollo", "section_sort_order": 2, "name": "Demuestra en su elaboracion una linea de investigacion y desarrollo coherente y clara.", "min_score": 0, "max_score": 3, "sort_order": 6},
        {"section_name": "II. Investigacion y desarrollo", "section_sort_order": 2, "name": "Argumenta, desde la implementacion del proyecto, el analisis e interpretacion de los datos recopilados.", "min_score": 0, "max_score": 3, "sort_order": 7},
        {"section_name": "II. Investigacion y desarrollo", "section_sort_order": 2, "name": "Evidencia la gestion de recursos y busqueda de apoyo para la elaboracion del proyecto.", "min_score": 0, "max_score": 3, "sort_order": 8},
        {"section_name": "II. Investigacion y desarrollo", "section_sort_order": 2, "name": "Demuestra originalidad y autoria propia del proyecto expuesto.", "min_score": 0, "max_score": 3, "sort_order": 9},
        {"section_name": "II. Investigacion y desarrollo", "section_sort_order": 2, "name": "Aplica la normativa vigente en el contexto del proyecto.", "min_score": 0, "max_score": 3, "sort_order": 10},
        {"section_name": "II. Investigacion y desarrollo", "section_sort_order": 2, "name": "Se evidencia la factibilidad e implementacion comercial o industrial del proyecto, a futuro.", "min_score": 0, "max_score": 3, "sort_order": 11},
        {"section_name": "III. Prototipo", "section_sort_order": 3, "name": "Presenta una linea de trabajo de investigacion y desarrollo coherente y clara.", "min_score": 0, "max_score": 3, "sort_order": 12},
        {"section_name": "III. Prototipo", "section_sort_order": 3, "name": "Da respuesta a la necesidad u objetivos planteados.", "min_score": 0, "max_score": 3, "sort_order": 13},
        {"section_name": "III. Prototipo", "section_sort_order": 3, "name": "Evidencia el uso optimo de los recursos disponibles para su construccion.", "min_score": 0, "max_score": 3, "sort_order": 14},
        {"section_name": "III. Prototipo", "section_sort_order": 3, "name": "Demuestra precision tecnica en la elaboracion y funcionamiento del prototipo.", "min_score": 0, "max_score": 3, "sort_order": 15},
        {"section_name": "III. Prototipo", "section_sort_order": 3, "name": "Respeta las normativas de seguridad y otras vigentes en su construccion y desempeno.", "min_score": 0, "max_score": 3, "sort_order": 16},
        {"section_name": "III. Prototipo", "section_sort_order": 3, "name": "Muestra actualidad tecnologica en el campo de trabajo seleccionado.", "min_score": 0, "max_score": 3, "sort_order": 17},
        {"section_name": "III. Prototipo", "section_sort_order": 3, "name": "Evidencia el funcionamiento correcto segun la solucion planteada en el proyecto.", "min_score": 0, "max_score": 3, "sort_order": 18},
        {"section_name": "III. Prototipo", "section_sort_order": 3, "name": "Demuestra creatividad e innovacion al crear el prototipo.", "min_score": 0, "max_score": 3, "sort_order": 19},
        {"section_name": "IV. Exposicion del proyecto", "section_sort_order": 4, "name": "Evidencia apropiacion y dominio del tema del proyecto.", "min_score": 0, "max_score": 3, "sort_order": 20},
        {"section_name": "IV. Exposicion del proyecto", "section_sort_order": 4, "name": "Demuestra claridad y coherencia en la exposicion del proyecto ante el panel de jueces.", "min_score": 0, "max_score": 3, "sort_order": 21},
        {"section_name": "IV. Exposicion del proyecto", "section_sort_order": 4, "name": "Utiliza lenguaje tecnico acorde con el nivel academico y el campo de desarrollo del proyecto.", "min_score": 0, "max_score": 3, "sort_order": 22},
        {"section_name": "IV. Exposicion del proyecto", "section_sort_order": 4, "name": "Argumenta de forma solida y fundamentada su propuesta de proyecto.", "min_score": 0, "max_score": 3, "sort_order": 23},
        {"section_name": "IV. Exposicion del proyecto", "section_sort_order": 4, "name": "Emplea recursos afines con el tema del proyecto.", "min_score": 0, "max_score": 3, "sort_order": 24},
        {"section_name": "IV. Exposicion del proyecto", "section_sort_order": 4, "name": "Describe la metodologia utilizada para la implementacion, evaluacion y perfeccionamiento de la solucion propuesta.", "min_score": 0, "max_score": 3, "sort_order": 25},
        {"section_name": "IV. Exposicion del proyecto", "section_sort_order": 4, "name": "Presenta resultados consistentes con los objetivos y solucion al problema planteado.", "min_score": 0, "max_score": 3, "sort_order": 26},
        {"section_name": "IV. Exposicion del proyecto", "section_sort_order": 4, "name": "Brinda conclusiones precisas y objetivas basadas en los resultados obtenidos.", "min_score": 0, "max_score": 3, "sort_order": 27},
        {"section_name": "IV. Exposicion del proyecto", "section_sort_order": 4, "name": "Denota colaboracion y comunicacion efectiva del estudiante o integrantes del equipo.", "min_score": 0, "max_score": 3, "sort_order": 28},
        {"section_name": "IV. Exposicion del proyecto", "section_sort_order": 4, "name": "Demuestra capacidad de recibir, analizar y aplicar sugerencias para mejorar el proyecto.", "min_score": 0, "max_score": 3, "sort_order": 29},
        {"section_name": "V. Documentacion del proyecto", "section_sort_order": 5, "name": "Se evidencia congruencia entre lo expuesto y el informe escrito.", "min_score": 0, "max_score": 3, "sort_order": 30},
        {"section_name": "V. Documentacion del proyecto", "section_sort_order": 5, "name": "Evidencia el uso de lenguaje tecnico afin al tema del proyecto.", "min_score": 0, "max_score": 3, "sort_order": 31},
        {"section_name": "V. Documentacion del proyecto", "section_sort_order": 5, "name": "Estipula los procedimientos tecnicos utilizados.", "min_score": 0, "max_score": 3, "sort_order": 32},
        {"section_name": "V. Documentacion del proyecto", "section_sort_order": 5, "name": "La bitacora detalla en forma cronologica los procesos de investigacion.", "min_score": 0, "max_score": 3, "sort_order": 33},
        {"section_name": "V. Documentacion del proyecto", "section_sort_order": 5, "name": "La bitacora detalla en forma cronologica los procesos de implementacion.", "min_score": 0, "max_score": 3, "sort_order": 34},
        {"section_name": "V. Documentacion del proyecto", "section_sort_order": 5, "name": "La bitacora detalla en forma cronologica los procesos de experimentacion.", "min_score": 0, "max_score": 3, "sort_order": 35},
        {"section_name": "V. Documentacion del proyecto", "section_sort_order": 5, "name": "Contiene informacion relevante para la exposicion del proyecto.", "min_score": 0, "max_score": 3, "sort_order": 36},
        {"section_name": "V. Documentacion del proyecto", "section_sort_order": 5, "name": "Utiliza el cartel o recursos audiovisuales como apoyo para la exposicion.", "min_score": 0, "max_score": 3, "sort_order": 37},
    ],
    "modelo_negocio_exposicion": [
        {"section_name": "Evaluacion de la Exposicion del Modelo de Negocios", "section_sort_order": 1, "name": "Define de forma precisa la operacion basica de la potencial empresa.", "min_score": 0, "max_score": 3, "sort_order": 1},
        {"section_name": "Evaluacion de la Exposicion del Modelo de Negocios", "section_sort_order": 1, "name": "Plantea las alternativas de solucion que la empresa brindara al problema o necesidad detectada.", "min_score": 0, "max_score": 3, "sort_order": 2},
        {"section_name": "Evaluacion de la Exposicion del Modelo de Negocios", "section_sort_order": 1, "name": "Describe los productos o servicios ofrecidos que brindan valor a los clientes.", "min_score": 0, "max_score": 3, "sort_order": 3},
        {"section_name": "Evaluacion de la Exposicion del Modelo de Negocios", "section_sort_order": 1, "name": "Evidencia el impacto de la potencial empresa desde diversos ambitos, tanto a corto como a largo plazo.", "min_score": 0, "max_score": 3, "sort_order": 4},
        {"section_name": "Evaluacion de la Exposicion del Modelo de Negocios", "section_sort_order": 1, "name": "Argumenta las diferencias que ofrece la potencial empresa con la competencia.", "min_score": 0, "max_score": 3, "sort_order": 5},
        {"section_name": "Evaluacion de la Exposicion del Modelo de Negocios", "section_sort_order": 1, "name": "Demuestra un buen entendimiento del mercado, la competencia y aspectos financieros.", "min_score": 0, "max_score": 3, "sort_order": 6},
        {"section_name": "Evaluacion de la Exposicion del Modelo de Negocios", "section_sort_order": 1, "name": "Argumenta con solidez que hace unico al negocio y por que constituye una buena oportunidad.", "min_score": 0, "max_score": 3, "sort_order": 7},
        {"section_name": "Evaluacion de la Exposicion del Modelo de Negocios", "section_sort_order": 1, "name": "Demuestra gestion de los recursos de forma sostenible y responsable.", "min_score": 0, "max_score": 3, "sort_order": 8},
        {"section_name": "Evaluacion de la Exposicion del Modelo de Negocios", "section_sort_order": 1, "name": "Demuestra claridad y coherencia en la exposicion del plan de negocios ante el panel de jueces.", "min_score": 0, "max_score": 3, "sort_order": 9},
        {"section_name": "Evaluacion de la Exposicion del Modelo de Negocios", "section_sort_order": 1, "name": "Utiliza lenguaje tecnico acorde con el nivel academico y el campo del negocio.", "min_score": 0, "max_score": 3, "sort_order": 10},
        {"section_name": "Evaluacion de la Exposicion del Modelo de Negocios", "section_sort_order": 1, "name": "Evidencia capacidad de comunicacion oral y dominio de la propuesta de valor.", "min_score": 0, "max_score": 3, "sort_order": 11},
        {"section_name": "Evaluacion de la Exposicion del Modelo de Negocios", "section_sort_order": 1, "name": "Define los canales mediante los cuales hara llegar a los clientes la propuesta de valor.", "min_score": 0, "max_score": 3, "sort_order": 12},
        {"section_name": "Evaluacion de la Exposicion del Modelo de Negocios", "section_sort_order": 1, "name": "Caracteriza el segmento de clientes (necesidades, comportamientos y atributos).", "min_score": 0, "max_score": 3, "sort_order": 13},
        {"section_name": "Evaluacion de la Exposicion del Modelo de Negocios", "section_sort_order": 1, "name": "Expone una propuesta innovadora y creativa con respecto al mercado.", "min_score": 0, "max_score": 3, "sort_order": 14},
        {"section_name": "Evaluacion de la Exposicion del Modelo de Negocios", "section_sort_order": 1, "name": "Describe las demandas del segmento de clientes y el seguimiento para asegurar la calidad de los bienes o servicios ofrecidos.", "min_score": 0, "max_score": 3, "sort_order": 15},
        {"section_name": "Evaluacion de la Exposicion del Modelo de Negocios", "section_sort_order": 1, "name": "Expone las fuentes de ingresos y estructura de costos.", "min_score": 0, "max_score": 3, "sort_order": 16},
        {"section_name": "Evaluacion de la Exposicion del Modelo de Negocios", "section_sort_order": 1, "name": "Explica los canales utilizados para dar a conocer su modelo de negocios.", "min_score": 0, "max_score": 3, "sort_order": 17},
        {"section_name": "Evaluacion de la Exposicion del Modelo de Negocios", "section_sort_order": 1, "name": "Describe las alianzas estrategicas de su propuesta de valor.", "min_score": 0, "max_score": 3, "sort_order": 18},
    ],
    "steam_informe_bitacora": [
        {"section_name": "I. Introduccion", "section_sort_order": 1, "name": "Delimita los antecedentes del problema o necesidad por solventar.", "min_score": 0, "max_score": 3, "sort_order": 1},
        {"section_name": "I. Introduccion", "section_sort_order": 1, "name": "Evidencia claridad en la definicion del problema.", "min_score": 0, "max_score": 3, "sort_order": 2},
        {"section_name": "I. Introduccion", "section_sort_order": 1, "name": "Fundamenta la relevancia o utilidad potencial del proyecto.", "min_score": 0, "max_score": 3, "sort_order": 3},
        {"section_name": "I. Introduccion", "section_sort_order": 1, "name": "Define los criterios tecnicos utilizados para la solucion del problema.", "min_score": 0, "max_score": 3, "sort_order": 4},
        {"section_name": "I. Introduccion", "section_sort_order": 1, "name": "Evidencia la viabilidad del proyecto.", "min_score": 0, "max_score": 3, "sort_order": 5},
        {"section_name": "II. Marco teorico", "section_sort_order": 2, "name": "Emplea variedad de fuentes de informacion confiables para sustentar el proyecto.", "min_score": 0, "max_score": 3, "sort_order": 6},
        {"section_name": "II. Marco teorico", "section_sort_order": 2, "name": "Incluye citas bibliograficas relevantes, de forma critica dentro del texto, que documentan la investigacion y desarrollo del proyecto.", "min_score": 0, "max_score": 3, "sort_order": 7},
        {"section_name": "II. Marco teorico", "section_sort_order": 2, "name": "Emplea fuentes bibliograficas actualizadas, segun el tema abordado en el proyecto.", "min_score": 0, "max_score": 3, "sort_order": 8},
        {"section_name": "II. Marco teorico", "section_sort_order": 2, "name": "Define terminos o conceptos relevantes para la investigacion y desarrollo del proyecto.", "min_score": 0, "max_score": 3, "sort_order": 9},
        {"section_name": "II. Marco teorico", "section_sort_order": 2, "name": "Sintetiza la informacion existente del tema en estudio.", "min_score": 0, "max_score": 3, "sort_order": 10},
        {"section_name": "II. Marco teorico", "section_sort_order": 2, "name": "Evidencia la organizacion logica de la informacion recopilada.", "min_score": 0, "max_score": 3, "sort_order": 11},
        {"section_name": "III. Objetivos", "section_sort_order": 3, "name": "Presenta el objetivo general y al menos dos objetivos especificos.", "min_score": 0, "max_score": 3, "sort_order": 12},
        {"section_name": "III. Objetivos", "section_sort_order": 3, "name": "Se plantean de forma clara, precisa y segun estructura requerida.", "min_score": 0, "max_score": 3, "sort_order": 13},
        {"section_name": "III. Objetivos", "section_sort_order": 3, "name": "Evidencia relacion con la propuesta de solucion planteada.", "min_score": 0, "max_score": 3, "sort_order": 14},
        {"section_name": "IV. Metodologia", "section_sort_order": 4, "name": "Presenta las etapas del proyecto en el cronograma.", "min_score": 0, "max_score": 3, "sort_order": 15},
        {"section_name": "IV. Metodologia", "section_sort_order": 4, "name": "Cumple con las etapas establecidas en el cronograma.", "min_score": 0, "max_score": 3, "sort_order": 16},
        {"section_name": "IV. Metodologia", "section_sort_order": 4, "name": "Describe paso a paso los procedimientos y tecnicas utilizadas para la investigacion y desarrollo.", "min_score": 0, "max_score": 3, "sort_order": 17},
        {"section_name": "IV. Metodologia", "section_sort_order": 4, "name": "Describe los recursos utilizados para la implementacion del proyecto.", "min_score": 0, "max_score": 3, "sort_order": 18},
        {"section_name": "IV. Metodologia", "section_sort_order": 4, "name": "Evidencia procesos de mejora continua durante la investigacion y desarrollo del proyecto.", "min_score": 0, "max_score": 3, "sort_order": 19},
        {"section_name": "IV. Metodologia", "section_sort_order": 4, "name": "Evidencia el desarrollo de ideas novedosas o la aplicacion creativa de conocimientos.", "min_score": 0, "max_score": 3, "sort_order": 20},
        {"section_name": "IV. Metodologia", "section_sort_order": 4, "name": "Fundamenta los calculos requeridos para las demostraciones.", "min_score": 0, "max_score": 3, "sort_order": 21},
        {"section_name": "IV. Metodologia", "section_sort_order": 4, "name": "Incluye disenos y esquemas claros en relacion con el desarrollo del prototipo.", "min_score": 0, "max_score": 3, "sort_order": 22},
        {"section_name": "V. Discusion de los resultados y conclusiones", "section_sort_order": 5, "name": "Muestra concordancia entre los resultados obtenidos y los objetivos planteados.", "min_score": 0, "max_score": 3, "sort_order": 23},
        {"section_name": "V. Discusion de los resultados y conclusiones", "section_sort_order": 5, "name": "Presenta los datos mediante tablas, diagramas, figuras, graficos, entre otros.", "min_score": 0, "max_score": 3, "sort_order": 24},
        {"section_name": "V. Discusion de los resultados y conclusiones", "section_sort_order": 5, "name": "Evidencia la interpretacion de los resultados desde una vision analitica y reflexiva.", "min_score": 0, "max_score": 3, "sort_order": 25},
        {"section_name": "V. Discusión de los resultados y conclusiones", "section_sort_order": 5, "name": "Demuestra resultados aplicables y útiles en la vida real.", "min_score": 0, "max_score": 3, "sort_order": 26},
        {"section_name": "V. Discusion de los resultados y conclusiones", "section_sort_order": 5, "name": "Presenta coherencia entre los disenos y esquemas con respecto al prototipo desarrollado.", "min_score": 0, "max_score": 3, "sort_order": 27},
        {"section_name": "V. Discusion de los resultados y conclusiones", "section_sort_order": 5, "name": "Plantea conclusiones relevantes en relacion con los objetivos trazados, analisis de datos y prototipado.", "min_score": 0, "max_score": 3, "sort_order": 28},
        {"section_name": "V. Discusion de los resultados y conclusiones", "section_sort_order": 5, "name": "Concluye sobre el impacto ambiental, social o economico de la implementacion del proyecto.", "min_score": 0, "max_score": 3, "sort_order": 29},
        {"section_name": "VI. Estructura y formato del proyecto", "section_sort_order": 6, "name": "Presenta una organizacion clara y logica, en congruencia con la estructura dada en los lineamientos.", "min_score": 0, "max_score": 3, "sort_order": 30},
        {"section_name": "VI. Estructura y formato del proyecto", "section_sort_order": 6, "name": "Presenta el documento en formato de doble columna (IEEE, articulo de revista).", "min_score": 0, "max_score": 3, "sort_order": 31},
        {"section_name": "VI. Estructura y formato del proyecto", "section_sort_order": 6, "name": "Presenta el listado de referencias citadas en el documento, segun formato APA vigente.", "min_score": 0, "max_score": 3, "sort_order": 32},
        {"section_name": "VII. Bitacora", "section_sort_order": 7, "name": "Evidencia el proceso de investigacion y desarrollo realizado.", "min_score": 0, "max_score": 3, "sort_order": 33},
        {"section_name": "VII. Bitacora", "section_sort_order": 7, "name": "Cumple con el formato solicitado, segun los lineamientos de la ExpoTECNICA.", "min_score": 0, "max_score": 3, "sort_order": 34},
        {"section_name": "VII. Bitacora", "section_sort_order": 7, "name": "Presenta relacion con el informe escrito.", "min_score": 0, "max_score": 3, "sort_order": 35},
    ],
    "modelo_negocio_documento": [
        {"section_name": "Evaluacion del Documento Escrito del Modelo de Negocios", "section_sort_order": 1, "name": "Describe de forma clara y precisa los antecedentes que fundamentan la propuesta de valor.", "min_score": 0, "max_score": 3, "sort_order": 1},
        {"section_name": "Evaluacion del Documento Escrito del Modelo de Negocios", "section_sort_order": 1, "name": "Explica con solidez que hace unico al negocio y por que es atractivo.", "min_score": 0, "max_score": 3, "sort_order": 2},
        {"section_name": "Evaluacion del Documento Escrito del Modelo de Negocios", "section_sort_order": 1, "name": "Describe las actividades clave que la empresa implementa para ofrecer una propuesta de valor.", "min_score": 0, "max_score": 3, "sort_order": 3},
        {"section_name": "Evaluacion del Documento Escrito del Modelo de Negocios", "section_sort_order": 1, "name": "Describe de forma detallada el producto o servicio propuesto que brinda valor a los clientes.", "min_score": 0, "max_score": 3, "sort_order": 4},
        {"section_name": "Evaluacion del Documento Escrito del Modelo de Negocios", "section_sort_order": 1, "name": "Detalla como los productos o servicios ofrecidos se diferencian de la competencia.", "min_score": 0, "max_score": 3, "sort_order": 5},
        {"section_name": "Evaluacion del Documento Escrito del Modelo de Negocios", "section_sort_order": 1, "name": "Emplea lenguaje tecnico acorde con el nivel academico y el campo del negocio.", "min_score": 0, "max_score": 3, "sort_order": 6},
        {"section_name": "Evaluacion del Documento Escrito del Modelo de Negocios", "section_sort_order": 1, "name": "Define los canales mediante los cuales hara llegar a los clientes la propuesta de valor.", "min_score": 0, "max_score": 3, "sort_order": 7},
        {"section_name": "Evaluacion del Documento Escrito del Modelo de Negocios", "section_sort_order": 1, "name": "Caracteriza ampliamente el segmento de clientes (necesidades, comportamientos y atributos).", "min_score": 0, "max_score": 3, "sort_order": 8},
        {"section_name": "Evaluacion del Documento Escrito del Modelo de Negocios", "section_sort_order": 1, "name": "Presenta los elementos diferenciadores que facilitan la decision de compra del cliente.", "min_score": 0, "max_score": 3, "sort_order": 9},
        {"section_name": "Evaluacion del Documento Escrito del Modelo de Negocios", "section_sort_order": 1, "name": "Describe las demandas del segmento de clientes y el seguimiento para asegurar la calidad de los bienes o servicios ofrecidos.", "min_score": 0, "max_score": 3, "sort_order": 10},
        {"section_name": "Evaluacion del Documento Escrito del Modelo de Negocios", "section_sort_order": 1, "name": "Presenta las estrategias para el acercamiento al cliente, ya sea durante el proceso de atencion o de servicio.", "min_score": 0, "max_score": 3, "sort_order": 11},
        {"section_name": "Evaluacion del Documento Escrito del Modelo de Negocios", "section_sort_order": 1, "name": "Presenta datos sobre clientes, tendencias y oportunidades.", "min_score": 0, "max_score": 3, "sort_order": 12},
        {"section_name": "Evaluacion del Documento Escrito del Modelo de Negocios", "section_sort_order": 1, "name": "Incluye estrategias de promocion, precios, distribucion y posicionamiento.", "min_score": 0, "max_score": 3, "sort_order": 13},
        {"section_name": "Evaluacion del Documento Escrito del Modelo de Negocios", "section_sort_order": 1, "name": "Presenta la estructura de costos, gastos e ingresos.", "min_score": 0, "max_score": 3, "sort_order": 14},
        {"section_name": "Evaluacion del Documento Escrito del Modelo de Negocios", "section_sort_order": 1, "name": "Incluye los canales para la distribucion del producto hasta el cliente y su promocion, incorporando el uso de nuevas tecnologias.", "min_score": 0, "max_score": 3, "sort_order": 15},
        {"section_name": "Evaluacion del Documento Escrito del Modelo de Negocios", "section_sort_order": 1, "name": "Detalla las alianzas estrategicas y aportes a su propuesta de valor.", "min_score": 0, "max_score": 3, "sort_order": 16},
        {"section_name": "Evaluacion del Documento Escrito del Modelo de Negocios", "section_sort_order": 1, "name": "Presenta una organizacion clara y logica del documento, en congruencia con la estructura dada en los lineamientos.", "min_score": 0, "max_score": 3, "sort_order": 17},
        {"section_name": "Evaluacion del Documento Escrito del Modelo de Negocios", "section_sort_order": 1, "name": "Presenta el listado de referencias citadas en el documento, segun formato APA vigente.", "min_score": 0, "max_score": 3, "sort_order": 18},
        {"section_name": "Evaluacion del Documento Escrito del Modelo de Negocios", "section_sort_order": 1, "name": "Cumple con el formato establecido.", "min_score": 0, "max_score": 3, "sort_order": 19},
        {"section_name": "Evaluacion del Documento Escrito del Modelo de Negocios", "section_sort_order": 1, "name": "Justifica de forma solida la viabilidad y pertinencia del negocio.", "min_score": 0, "max_score": 3, "sort_order": 20},
        {"section_name": "Evaluacion del Documento Escrito del Modelo de Negocios", "section_sort_order": 1, "name": "Identifica la situacion de mercado, sociedad o industria que se aborda en la propuesta de negocio.", "min_score": 0, "max_score": 3, "sort_order": 21},
        {"section_name": "Evaluacion del Documento Escrito del Modelo de Negocios", "section_sort_order": 1, "name": "Argumenta la necesidad o problema que resuelve la propuesta de negocio.", "min_score": 0, "max_score": 3, "sort_order": 22},
        {"section_name": "Evaluacion del Documento Escrito del Modelo de Negocios", "section_sort_order": 1, "name": "Determina aspectos sociales, economicos, tecnologicos o ambientales que resuelve la propuesta de negocio.", "min_score": 0, "max_score": 3, "sort_order": 23},
        {"section_name": "Evaluacion del Documento Escrito del Modelo de Negocios", "section_sort_order": 1, "name": "Plantea los objetivos del negocio enfatizando en su viabilidad, escalabilidad y sostenibilidad.", "min_score": 0, "max_score": 3, "sort_order": 24},
    ],
    "plan_negocio_documento": [
        {"section_name": "Evaluacion del Documento Escrito del Plan de Negocios", "section_sort_order": 1, "name": "Explica con solidez que hace unico al negocio y por que es atractivo.", "min_score": 0, "max_score": 3, "sort_order": 1},
        {"section_name": "Evaluacion del Documento Escrito del Plan de Negocios", "section_sort_order": 1, "name": "Describe las actividades clave que la empresa implementa para ofrecer una propuesta de valor.", "min_score": 0, "max_score": 3, "sort_order": 2},
        {"section_name": "Evaluacion del Documento Escrito del Plan de Negocios", "section_sort_order": 1, "name": "Evidencia la identificacion de los equipos y recursos necesarios para llevar a cabo las operaciones de la empresa.", "min_score": 0, "max_score": 3, "sort_order": 3},
        {"section_name": "Evaluacion del Documento Escrito del Plan de Negocios", "section_sort_order": 1, "name": "Describe de forma detallada el producto o servicio propuesto que brinda valor a los clientes.", "min_score": 0, "max_score": 3, "sort_order": 4},
        {"section_name": "Evaluacion del Documento Escrito del Plan de Negocios", "section_sort_order": 1, "name": "Detalla como los productos o servicios ofrecidos se diferencian de la competencia.", "min_score": 0, "max_score": 3, "sort_order": 5},
        {"section_name": "Evaluacion del Documento Escrito del Plan de Negocios", "section_sort_order": 1, "name": "Emplea lenguaje tecnico acorde con el nivel academico y el campo del negocio.", "min_score": 0, "max_score": 3, "sort_order": 6},
        {"section_name": "Evaluacion del Documento Escrito del Plan de Negocios", "section_sort_order": 1, "name": "Define los canales mediante los cuales hara llegar a los clientes la propuesta de valor.", "min_score": 0, "max_score": 3, "sort_order": 7},
        {"section_name": "Evaluacion del Documento Escrito del Plan de Negocios", "section_sort_order": 1, "name": "Caracteriza ampliamente el segmento de clientes (necesidades, comportamientos y atributos).", "min_score": 0, "max_score": 3, "sort_order": 8},
        {"section_name": "Evaluacion del Documento Escrito del Plan de Negocios", "section_sort_order": 1, "name": "Presenta los elementos diferenciadores que facilitan la decision de compra del cliente.", "min_score": 0, "max_score": 3, "sort_order": 9},
        {"section_name": "Evaluacion del Documento Escrito del Plan de Negocios", "section_sort_order": 1, "name": "Describe las demandas del segmento de clientes y el seguimiento para asegurar la calidad de los bienes o servicios ofrecidos.", "min_score": 0, "max_score": 3, "sort_order": 10},
        {"section_name": "Evaluacion del Documento Escrito del Plan de Negocios", "section_sort_order": 1, "name": "Presenta las estrategias para el acercamiento al cliente, ya sea durante el proceso de atencion o de servicio.", "min_score": 0, "max_score": 3, "sort_order": 11},
        {"section_name": "Evaluacion del Documento Escrito del Plan de Negocios", "section_sort_order": 1, "name": "Presenta datos sobre clientes, tendencias y oportunidades.", "min_score": 0, "max_score": 3, "sort_order": 12},
        {"section_name": "Evaluacion del Documento Escrito del Plan de Negocios", "section_sort_order": 1, "name": "Incluye los canales para la distribucion del producto hasta el cliente y su promocion, incorporando el uso de nuevas tecnologias.", "min_score": 0, "max_score": 3, "sort_order": 13},
        {"section_name": "Evaluacion del Documento Escrito del Plan de Negocios", "section_sort_order": 1, "name": "Presenta la estructura de costos, gastos e ingresos.", "min_score": 0, "max_score": 3, "sort_order": 14},
        {"section_name": "Evaluacion del Documento Escrito del Plan de Negocios", "section_sort_order": 1, "name": "Incluye los canales para la distribucion del producto hasta el cliente y su promocion, incorporando el uso de nuevas tecnologias.", "min_score": 0, "max_score": 3, "sort_order": 15},
        {"section_name": "Evaluacion del Documento Escrito del Plan de Negocios", "section_sort_order": 1, "name": "Determina el mercado meta y su alineacion con la propuesta de valor del negocio.", "min_score": 0, "max_score": 3, "sort_order": 16},
        {"section_name": "Evaluacion del Documento Escrito del Plan de Negocios", "section_sort_order": 1, "name": "Presenta el modelo de negocio integrando los nueve modulos basicos que definen la operacion de la empresa, segun lo expuesto en la fase institucional.", "min_score": 0, "max_score": 3, "sort_order": 17},
        {"section_name": "Evaluacion del Documento Escrito del Plan de Negocios", "section_sort_order": 1, "name": "Presenta el analisis de la viabilidad financiera incluyendo ingresos, costos, gastos y utilidades esperadas.", "min_score": 0, "max_score": 3, "sort_order": 18},
        {"section_name": "Evaluacion del Documento Escrito del Plan de Negocios", "section_sort_order": 1, "name": "Presenta el analisis de las fuentes de financiamiento y su impacto en la permanencia del negocio.", "min_score": 0, "max_score": 3, "sort_order": 19},
        {"section_name": "Evaluacion del Documento Escrito del Plan de Negocios", "section_sort_order": 1, "name": "Evidencia una relacion realista entre las proyecciones e indicadores financieros.", "min_score": 0, "max_score": 3, "sort_order": 20},
        {"section_name": "Evaluacion del Documento Escrito del Plan de Negocios", "section_sort_order": 1, "name": "Evidencia cumplimiento de la normativa vigente en apego a la forma juridica, organizacional y seguridad social.", "min_score": 0, "max_score": 3, "sort_order": 21},
        {"section_name": "Evaluacion del Documento Escrito del Plan de Negocios", "section_sort_order": 1, "name": "Detalla las alianzas estrategicas y aportes a su propuesta de valor.", "min_score": 0, "max_score": 3, "sort_order": 22},
        {"section_name": "Evaluacion del Documento Escrito del Plan de Negocios", "section_sort_order": 1, "name": "Presenta una organizacion clara y logica del documento, en congruencia con la estructura dada en los lineamientos.", "min_score": 0, "max_score": 3, "sort_order": 23},
        {"section_name": "Evaluacion del Documento Escrito del Plan de Negocios", "section_sort_order": 1, "name": "Presenta el listado de referencias citadas en el documento, segun formato APA vigente.", "min_score": 0, "max_score": 3, "sort_order": 24},
        {"section_name": "Evaluacion del Documento Escrito del Plan de Negocios", "section_sort_order": 1, "name": "Cumple con el formato establecido.", "min_score": 0, "max_score": 3, "sort_order": 25},
        {"section_name": "Evaluacion del Documento Escrito del Plan de Negocios", "section_sort_order": 1, "name": "Justifica de forma solida la viabilidad y pertinencia del negocio.", "min_score": 0, "max_score": 3, "sort_order": 26},
        {"section_name": "Evaluacion del Documento Escrito del Plan de Negocios", "section_sort_order": 1, "name": "Identifica la situacion de mercado, sociedad o industria que se aborda en la propuesta de negocio.", "min_score": 0, "max_score": 3, "sort_order": 27},
        {"section_name": "Evaluacion del Documento Escrito del Plan de Negocios", "section_sort_order": 1, "name": "Argumenta la necesidad o problema que resuelve la propuesta de negocio.", "min_score": 0, "max_score": 3, "sort_order": 28},
    ],
    "english_project_performance": [
        {"section_name": "Use of Language", "section_sort_order": 1, "name": "Organization of Ideas", "min_score": 1, "max_score": 5, "sort_order": 1},
        {"section_name": "Use of Language", "section_sort_order": 1, "name": "Vocabulary", "min_score": 1, "max_score": 5, "sort_order": 2},
        {"section_name": "Use of Language", "section_sort_order": 1, "name": "Sentence Structure and Grammar", "min_score": 1, "max_score": 5, "sort_order": 3},
        {"section_name": "Use of Language", "section_sort_order": 1, "name": "Pronunciation", "min_score": 1, "max_score": 5, "sort_order": 4},
        {"section_name": "Use of Language", "section_sort_order": 1, "name": "Content", "min_score": 1, "max_score": 5, "sort_order": 5},
        {"section_name": "Use of Language", "section_sort_order": 1, "name": "Conclusion", "min_score": 1, "max_score": 5, "sort_order": 6},
        {"section_name": "Delivery", "section_sort_order": 2, "name": "Verbal", "min_score": 1, "max_score": 5, "sort_order": 7},
        {"section_name": "Delivery", "section_sort_order": 2, "name": "Nonverbal", "min_score": 1, "max_score": 5, "sort_order": 8},
    ],
}

EVALUATION_DEFAULTS_SEEDED_KEY = "evaluation_defaults_seeded"
EVALUATION_DESCRIPTIONS_MIGRATED_KEY = "evaluation_descriptions_migrated"


def bootstrap_defaults(db):
    created = False

    if Category.query.count() == 0:
        for row in DEFAULT_CATEGORIES:
            db.session.add(Category(**row))
        created = True

    if Level.query.count() == 0:
        for row in DEFAULT_LEVELS:
            db.session.add(Level(**row))
        created = True

    evaluation_defaults_seeded = SystemSetting.get_value(EVALUATION_DEFAULTS_SEEDED_KEY, "")
    should_seed_evaluation_defaults = evaluation_defaults_seeded != "1"

    if should_seed_evaluation_defaults:
        if EvaluationType.query.count() == 0:
            for row in DEFAULT_EVALUATION_TYPES:
                db.session.add(EvaluationType(**row))
            created = True
            db.session.flush()

            for type_code, rubric_rows in DEFAULT_RUBRICS.items():
                eval_type = EvaluationType.query.filter_by(code=type_code).first()
                if not eval_type:
                    continue
                for rubric in rubric_rows:
                    db.session.add(RubricCriterion(evaluation_type_id=eval_type.id, **rubric))
                created = True
        else:
            for row in DEFAULT_EVALUATION_TYPES:
                existing_type = EvaluationType.query.filter_by(code=row["code"]).first()
                if existing_type:
                    if row.get("scale_labels") and not existing_type.scale_labels:
                        existing_type.scale_labels = row["scale_labels"]
                        created = True
                    if not existing_type.description:
                        existing_type.description = row.get("description") or existing_type.name
                        created = True
            db.session.flush()

        SystemSetting.set_value(EVALUATION_DEFAULTS_SEEDED_KEY, "1")
        created = True
    else:
        db.session.flush()

    for row in DEFAULT_SECTIONS:
        level = Level.query.filter_by(code=row["level_code"]).first()
        if not level:
            continue
        exists = Section.query.filter_by(level_id=level.id, name=row["name"]).first()
        if exists:
            continue
        db.session.add(
            Section(level_id=level.id, name=row["name"], sort_order=row["sort_order"], is_active=True)
        )
        created = True

    if Specialty.query.count() == 0:
        for row in DEFAULT_SPECIALTIES:
            db.session.add(Specialty(**row))
        created = True

    if Workshop.query.count() == 0:
        for row in DEFAULT_WORKSHOPS:
            db.session.add(Workshop(**row))
        created = True

    default_settings = {
        "school_name": "CTP Roberto Gamboa Valverde",
        "school_address": "Direccion institucional no configurada",
        "school_phone": "+506 0000-0000",
        "school_email": "direccion@ctprgv.edu",
        "school_logo_path": "",
        "expo_logo_path": "",
        EVALUATION_DEFAULTS_SEEDED_KEY: "1",
        EVALUATION_DESCRIPTIONS_MIGRATED_KEY: "1",
        "maintenance_enabled": "0",
        "maintenance_message": "Estamos cargando informacion de proyectos. Vuelve pronto.",
        "maintenance_image_path": "",
    }
    for key, value in default_settings.items():
        if SystemSetting.get_value(key) is None:
            SystemSetting.set_value(key, value)
            created = True

    evaluation_descriptions_migrated = SystemSetting.get_value(EVALUATION_DESCRIPTIONS_MIGRATED_KEY, "")
    if evaluation_descriptions_migrated != "1":
        for row in DEFAULT_EVALUATION_TYPES:
            existing_type = EvaluationType.query.filter_by(code=row["code"]).first()
            if not existing_type:
                continue
            if not existing_type.description:
                existing_type.description = existing_type.name
                created = True
            existing_type.name = row["name"]
            if row.get("description"):
                existing_type.description = row["description"]
            created = True
        SystemSetting.set_value(EVALUATION_DESCRIPTIONS_MIGRATED_KEY, "1")
        created = True

    if created:
        db.session.commit()


def get_active_categories():
    return Category.query.filter_by(is_active=True).order_by(Category.sort_order.asc(), Category.name.asc()).all()


def get_active_evaluation_types():
    return (
        EvaluationType.query.filter_by(is_active=True)
        .order_by(EvaluationType.sort_order.asc(), EvaluationType.name.asc())
        .all()
    )


def get_active_rubrics_map():
    mapping = {}
    for evaluation_type in get_active_evaluation_types():
        criteria = (
            RubricCriterion.query.filter_by(evaluation_type_id=evaluation_type.id, is_active=True)
            .order_by(
                RubricCriterion.section_sort_order.asc(),
                RubricCriterion.sort_order.asc(),
                RubricCriterion.id.asc(),
            )
            .all()
        )
        mapping[evaluation_type.code] = criteria
    return mapping
