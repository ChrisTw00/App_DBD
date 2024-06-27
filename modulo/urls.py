from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from tasks import views

urlpatterns = [
    path('admin/', admin.site.urls),

    # Employee Management
    path('registro_empleado/', views.mostrarventana),
    path('registrar_empleado/', views.registrar_empleado),
    path('registrar_empleado/registro_sesion/', views.registro_sesion_ventana),
    path('registrar_sesion/', views.registrar_sesion),
    path('matricula_empleado/', views.matricula_empleado_ventana),
    path('matricular_empleado/', views.matricular_empleado),
    path('lista_matricula/', views.mostrar_matricula_ventana),
    path('listar_matricula/<codigo_programa>/', views.mostrar_matricula_ventana),
    path('muestra_capacitaciones/', views.muestra_capacitaciones),
    path('ingresarIdPrograma/', views.ingresarIdPrograma),
    path('mostrarMatricula/<id_programa>/', views.mostrarMatricula),
    path('actualizar_asistencia/', views.ventana_asistencia),
    path('ingresarIdSesion/', views.ingresarIdSesion),
    path('mostrarAsistencia/<id_sesion>/', views.mostrarAsistencia),
    
    # Redereccionar Capacitación

    path('capacitacion/', views.tablacargo, name="menuJulio"),

    # Employee Termination
    path('', views.login, name='login'),
    path('seleccion/', views.seleccion, name='seleccion'),
    path('cese1/', views.cese1, name='cese1'),
    path('cese2/<int:id_cese>/', views.cese2, name='cese2'),
    path('cese3/', views.cese3, name='cese3'),
    path('cese4/', views.cese4, name='cese4'),
    path('cese5/', views.cese5, name='cese5'),
    path('cese6/', views.cese6, name='cese6'),
    path('cese7/', views.cese7, name='cese7'),

    # Performance Review
    path('aprobar/', views.baseAprobar),
    path('aprobar/<id_tipo_cuestionario>/', views.mostrarPreguntas),
    path('enviarAprobacion/', views.enviarAprobacion),
    path('crear/', views.crear),
    path('botonCrear/', views.botonCrear),
    path('editar/', views.baseEditar),
    path('editar/<int:id_tipo_cuestionario>/', views.mostrarPreguntas),
    path('agregarPregunta/', views.agregarPregunta),
    path('borrarPregunta/<int:id_pregunta>/', views.borrarPregunta),
    path('enviarGerencia/', views.enviarGerencia),
    path('menuDesempeño/', views.mostrarMenu, name="menuTineo"),
    path('misResultados/', views.baseMisResultados),
    path('ingresarID/', views.ingresarID),
    path('ingresarDNI/', views.ingresarDNI),
    path('ingresarApellido/', views.ingresarApellido),
    path('misResultadosDNI/<dni>/', views.mostrarResultadosDNI),
    path('misResultadosID/<id_empleado>/', views.mostrarResultadosID),
    path('misResultadosApellido/<apellido>/', views.mostrarTablaApellidos),
    path('programarReunion/', views.baseProgramarReunion),
    path('botonProgramar/', views.botonProgramar),
    path('reporte/<id_empleado>/', views.reporteBase),
    path('confirmarReporte/', views.confirmarReporte),
    path('responder/', views.baseResponder),
    path('responder/<id_tipo_cuestionario>/', views.mostrarPreguntas),
    path('enviarRespuestas/', views.enviarRespuestas),
    path('reunionesPendientes/', views.mostrarReuniones),
    path('revisar/', views.baseRevisar),
    path('revisar/apellido/', views.revisarApellido),
    path('revisar/<id_tipo_cuestionario>/', views.revisarTipoCuestionario),
    path('responder/calificacion/NULL/', views.revisarCalificacionNULL),
    path('responder/calificacion/<id_tipo_calificacion>/', views.revisarCalificacion),

    # Recruitment
    path('MenuReclutamiento/', views.home, name='home'),
    path('registrar/', views.registrar_postulante, name='registrar_postulante'),
    path('success/', views.success_view, name='success'),
    path('postulantes/', views.listar_postulantes, name='listar_postulantes'),
    path('postulantes/<int:id_cand>/', views.detalle_postulante, name='detalle_postulante'),
    path('seleccionar/', views.seleccionar_horario_puesto, name='seleccionar_horario_puesto'),
    path('seleccionar_vacante/', views.seleccionar_vacante, name='seleccionar_vacante'),
    path('preseleccion/', views.preseleccion_candidatos, name='preseleccion_candidatos'),
    path('seleccion_final/', views.seleccion_final, name='seleccion_final'),
    path('crear_vacante/', views.crear_vacante, name='crear_vacante'),
    path('listar_vacantes/', views.listar_vacantes, name='listar_vacantes'),
    path('programar_entrevista/', views.programar_entrevista, name='programar_entrevista'),
    path('listar_entrevistas/', views.listar_entrevistas, name='listar_entrevistas'),
    path('actualizar_evaluacion/', views.actualizar_evaluacion, name='actualizar_evaluacion'),
    path('listado_seleccionados/', views.listado_seleccionados, name='listado_seleccionados'),
    path('listar_evaluaciones/', views.listar_evaluaciones, name='listar_evaluaciones'),
    # Edison
    path('MenuPrincipal', views.MenuPrincipal, name='MenuPrincipal'),    
    path('InsertarAsistencia/', views.Insert),
    path('empleados_por_departamento/<int:departamento_id>/', views.empleados_por_departamento, name='empleados_por_departamento'),
    path('SolicitarLicencia/', views.solicitar_licencia, name='solicitar_licencia'),
    path('SolicitarPermiso/', views.solicitar_permiso, name='solicitar_permiso'),
    path('AceptarRechazarSolicitudes/', views.aprobar_rechazar_solicitudes, name='aprobar_rechazar_solicitudes'),
    path('GenerarReporteAsistencia/', views.generar_reporte_asistencia, name='Generar_reporte_asistencia'),
    path('MostrarReporte/<int:departamento_id>/<str:fecha_inicio>/<str:fecha_fin>/', views.mostrar_reporte, name='mostrar_reporte'),
    path('aprobar_rechazar_permisos/', views.aprobar_rechazar_permisos, name='aprobar_rechazar_permisos'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
