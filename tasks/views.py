# tasks/views.py
import os
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.shortcuts import render, redirect
from django.db import connection, IntegrityError
from django.http import HttpResponse
from datetime import datetime

# Reclutamiento
from django.shortcuts import render

def MenuPrincipal(request):
    return render(request, 'menu_principal.html')
def get_next_id(table_name, id_column):
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT COALESCE(MAX({id_column}), 0) + 1 FROM {table_name}")
        next_id = cursor.fetchone()[0]
    return next_id
def get_next_id2(table_name, id_column):
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT {id_column} FROM {table_name} ORDER BY {id_column} DESC LIMIT 1")
        last_id = cursor.fetchone()
        if last_id:
            last_id = last_id[0]
            next_id = str(int(last_id) + 1).zfill(len(last_id))
        else:
            next_id = '00000001'  # Comienza con '00000001' si no hay registros
    return next_id

def home(request):
    return render(request, 'home.html') 

def success_view(request):
    return render(request, 'success.html')

def listar_postulantes(request):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT c.ID_Cand, c.Nombre_Cand, c.Apell_Cand, cu.archivo_pdf
            FROM Candidato c
            JOIN Curriculum cu ON c.Id_Curriculum = cu.ID_Curriculum
        """)
        rows = cursor.fetchall()

    candidatos = [{'id_cand': row[0], 'nombre_cand': row[1], 'apell_cand': row[2], 'archivo_pdf': row[3]} for row in rows]
    
    return render(request, 'listar_postulantes.html', {'candidatos': candidatos})


import base64
from django.conf import settings
import os

def detalle_postulante(request, id_cand):
    with connection.cursor() as cursor:
        # Obtener los datos del candidato
        cursor.execute("SELECT * FROM Candidato WHERE ID_Cand = %s", [id_cand])
        row = cursor.fetchone()
        if not row:
            return HttpResponse("Candidato no encontrado", status=404)

        candidato = {
            'id_cand': row[0],
            'nombre_cand': row[1],
            'apell_cand': row[2],
            'fecha_nac_cand': row[3],
            'direccion_cand': row[4],
            'correo_cand': row[5],
            'num_telefono': row[6],
            'id_curriculum': row[7]
        }

        # Obtener los datos del curriculum
        cursor.execute("SELECT * FROM Curriculum WHERE ID_Curriculum = %s", [candidato['id_curriculum']])
        row = cursor.fetchone()
        if not row:
            return HttpResponse("Curriculum no encontrado", status=404)

        curriculum = {
            'id_curriculum': row[0],
            'grado_educacion': row[1],
            'archivo_pdf': row[4]
        }

        # Leer el archivo PDF y convertirlo a base64
        pdf_path = os.path.join(settings.MEDIA_ROOT, curriculum['archivo_pdf'])
        with open(pdf_path, 'rb') as pdf_file:
            encoded_pdf = base64.b64encode(pdf_file.read()).decode('utf-8')

        # Obtener las experiencias laborales
        cursor.execute("""
            SELECT EL.Nombre_Lugar, EL.Cargo_Ejercido, EL.Tiempo_Ejercido
            FROM Experiencia_Laboral EL
            JOIN CurriculumXExperiencia CE ON EL.ID_Experiencia = CE.id_experiencia
            WHERE CE.id_curriculum = %s
        """, [curriculum['id_curriculum']])
        experiencias = cursor.fetchall()

        # Obtener los certificados
        cursor.execute("""
            SELECT C.Curso_Certificado, C.Nivel_Certificado
            FROM Certificados C
            JOIN CurriculumXCertificado CC ON C.ID_Certificado = CC.id_certificado
            WHERE CC.id_curriculum = %s
        """, [curriculum['id_curriculum']])
        certificados = cursor.fetchall()

    return render(request, 'detalle_postulante.html', {
        'candidato': candidato,
        'curriculum': curriculum,
        'experiencias': experiencias,
        'certificados': certificados,
        'encoded_pdf': encoded_pdf
    })



import os
from django.core.files.storage import default_storage

def registrar_postulante(request):
    if request.method == 'POST':
        nombre_cand = request.POST['nombre_cand']
        apell_cand = request.POST['apell_cand']
        fecha_nac_cand = request.POST['fecha_nac_cand']
        direccion_cand = request.POST['direccion_cand']
        correo_cand = request.POST['correo_cand']
        num_telefono = request.POST['num_telefono']
        grado_educacion = request.POST['grado_educacion']
        archivo_pdf = request.FILES['archivo_pdf']

        # Obtener listas de experiencias laborales
        nombre_lugar_list = request.POST.getlist('nombre_lugar')
        cargo_ejercido_list = request.POST.getlist('cargo_ejercido')
        tiempo_ejercido_list = request.POST.getlist('tiempo_ejercido')

        # Obtener listas de certificados
        curso_certificado_list = request.POST.getlist('curso_certificado')
        nivel_certificado_list = request.POST.getlist('nivel_certificado')

        # Limitar la longitud del nombre del archivo PDF
        fs = FileSystemStorage()
        filename = fs.save(archivo_pdf.name, archivo_pdf)
        uploaded_file_url = fs.url(filename)
        archivo_pdf_name = archivo_pdf.name
        if len(archivo_pdf_name) > 255:
            archivo_pdf_name = archivo_pdf_name[:255]

        with connection.cursor() as cursor:
            # Insertar experiencias laborales y obtener sus IDs
            experiencia_ids = []
            for nombre_lugar, cargo_ejercido, tiempo_ejercido in zip(nombre_lugar_list, cargo_ejercido_list, tiempo_ejercido_list):
                experiencia_id = get_next_id('Experiencia_Laboral', 'id_experiencia')
                cursor.execute("INSERT INTO Experiencia_Laboral (ID_Experiencia, Nombre_Lugar, Cargo_Ejercido, Tiempo_Ejercido) VALUES (%s, %s, %s, %s)",
                               [experiencia_id, nombre_lugar, cargo_ejercido, tiempo_ejercido])
                experiencia_ids.append(experiencia_id)

            # Insertar certificados y obtener sus IDs
            certificado_ids = []
            for curso_certificado, nivel_certificado in zip(curso_certificado_list, nivel_certificado_list):
                certificado_id = get_next_id('Certificados', 'id_certificado')
                cursor.execute("INSERT INTO Certificados (ID_Certificado, Curso_Certificado, Nivel_Certificado) VALUES (%s, %s, %s)",
                               [certificado_id, curso_certificado, nivel_certificado])
                certificado_ids.append(certificado_id)

            # Verificar si hay experiencias y certificados para el curriculum
            experiencia_id = experiencia_ids[0] if experiencia_ids else None
            certificado_id = certificado_ids[0] if certificado_ids else None

            # Insertar curriculum
            curriculum_id = get_next_id('Curriculum', 'id_curriculum')
            cursor.execute("INSERT INTO Curriculum (ID_Curriculum, Grado_Educacion, ID_Experiencia, ID_Certificado, archivo_pdf) VALUES (%s, %s, %s, %s, %s)", 
                           [curriculum_id, grado_educacion, experiencia_id, certificado_id, archivo_pdf_name])

            # Insertar las relaciones entre curriculum y experiencias laborales
            for experiencia_id in experiencia_ids:
                cursor.execute("INSERT INTO CurriculumXExperiencia (id_curriculum, id_experiencia) VALUES (%s, %s)", 
                               [curriculum_id, experiencia_id])

            # Insertar las relaciones entre curriculum y certificados
            for certificado_id in certificado_ids:
                cursor.execute("INSERT INTO CurriculumXCertificado (id_curriculum, id_certificado) VALUES (%s, %s)", 
                               [curriculum_id, certificado_id])

            # Insertar candidato
            candidato_id = get_next_id('Candidato', 'ID_Cand')
            cursor.execute("INSERT INTO Candidato (ID_Cand, Nombre_Cand, Apell_Cand, Fecha_Nac_Cand, Direccion_Cand, Correo_Cand, Num_Telefono, Id_Curriculum) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                           [candidato_id, nombre_cand, apell_cand, fecha_nac_cand, direccion_cand, correo_cand, num_telefono, curriculum_id])

        return redirect('success')
    else:
        return render(request, 'postulante_form.html')

    
def seleccionar_horario_puesto(request):
    if request.method == 'POST':
        id_solicitud = get_next_id2('Solicitud_Empleo', 'ID_Solicitud')
        id_vacante = request.POST.get('id_vacante')  
        est_solicitud = "Pendiente"
        horario_disponible = request.POST.get('horario_disponible')
        fecha_aplicacion = request.POST.get('fecha_aplicacion')
        id_cand = request.POST.get('id_cand')

        if not id_vacante:
            return render(request, 'seleccion_form.html', {
                'error': 'Debe seleccionar una vacante',
                'vacantes': get_vacantes(),
                'candidatos': get_candidatos()
            })

        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO Solicitud_Empleo (ID_Solicitud, ID_Vacante, Est_Solicitud, Horario_Disponible, Fecha_Aplicacion, ID_Cand) VALUES (%s, %s, %s, %s, %s, %s)",
                [id_solicitud, id_vacante, est_solicitud, horario_disponible, fecha_aplicacion, id_cand]
            )
        return redirect('success')
    else:
        vacantes = get_vacantes()
        candidatos = get_candidatos()
        return render(request, 'seleccion_form.html', {
            'vacantes': vacantes,
            'candidatos': candidatos
        })

def get_vacantes():
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT DISTINCT v.ID_Vac, c.Nombre
            FROM Vacante v
            JOIN Cargo c ON v.ID_Cargo = c.ID_Cargo
            JOIN Solicitud_Empleo se ON v.ID_Vac = se.ID_Vacante
            WHERE se.Est_Solicitud = 'Pendiente' OR se.Est_Solicitud = 'En proceso'
        """)
        return cursor.fetchall()

def get_candidatos():
    with connection.cursor() as cursor:
        cursor.execute("SELECT ID_Cand, Nombre_Cand, Apell_Cand FROM Candidato")
        return cursor.fetchall()

def seleccionar_vacante(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT ID_Cargo, Nombre FROM Cargo")
        cargos = cursor.fetchall()
    
    return render(request, 'seleccionar_vacante.html', {'cargos': cargos})

def preseleccion_candidatos(request):
    if request.method == 'POST':
        cargo_id = request.POST.get('id_cargo', '')
        if 'preseleccionar' in request.POST:
            seleccionados = request.POST.getlist('seleccionados')
            if seleccionados:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "UPDATE Solicitud_Empleo SET Est_Solicitud = 'Preseleccionado' WHERE ID_Solicitud IN %s",
                        [tuple(seleccionados)]
                    )
                return redirect('success')
        else:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT se.ID_solicitud, c.ID_cand, c.Nombre_cand, c.Apell_cand, se.Horario_disponible, se.Est_solicitud
                    FROM Solicitud_Empleo se
                    JOIN Candidato c ON se.ID_cand = c.ID_cand
                    JOIN Vacante v ON se.ID_Vacante = v.ID_Vac
                    WHERE v.ID_Cargo = %s
                    AND (se.Est_solicitud = 'Pendiente' OR se.Est_solicitud = 'En proceso')
                """, [cargo_id])
                candidatos = cursor.fetchall()

            return render(request, 'preseleccion_list.html', {'candidatos': candidatos, 'cargo_id': cargo_id})
    else:
        return redirect('seleccionar_vacante')
  

import datetime 

def seleccion_final(request):
    if request.method == 'POST':
        seleccionados = request.POST.getlist('seleccionados')
        no_seleccionados = request.POST.getlist('no_seleccionados')
        
        if seleccionados or no_seleccionados:
            with connection.cursor() as cursor:
                if seleccionados:
                    for id_solicitud in seleccionados:
                        # Obtener los datos del candidato y de la vacante para la solicitud seleccionada
                        cursor.execute("""
                            SELECT c.ID_Cand, c.Nombre_Cand, c.Apell_Cand, c.Correo_Cand, c.Num_Telefono, c.Direccion_Cand, c.Fecha_Nac_Cand,
                                   v.ID_Departamento, v.ID_Cargo
                            FROM Solicitud_Empleo se
                            JOIN Candidato c ON se.ID_Cand = c.ID_Cand
                            JOIN Vacante v ON se.ID_Vacante = v.ID_Vac
                            WHERE se.ID_Solicitud = %s
                        """, [id_solicitud])
                        candidato = cursor.fetchone()

                        if candidato:
                            id_cand, nombre, apellido, correo, telefono, direccion, fecha_nac, id_departamento, id_cargo = candidato

                            # Insertar el nuevo empleado
                            id_empleado = get_next_id('Empleado', 'ID_Empleado')
                            fecha_ingreso = datetime.date.today()  # Usar la fecha actual como fecha de ingreso
                            cursor.execute("""
                                INSERT INTO Empleado (ID_Empleado, Nombre_Empleado, Apellido_Empleado, Telefono, Direccion, Correo, Fecha_Nacimiento, Cant_Hijos, Estado_Civil, DNI, Fecha_Ingreso, ID_Departamento, ID_Cargo, Contrasena, Estado_laboral)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, 0, 'Soltero', '00000000', %s, %s, %s, '123', 'Activo')
                            """, [id_empleado, nombre, apellido, telefono, direccion, correo, fecha_nac, fecha_ingreso, id_departamento, id_cargo])

                            # Actualizar el estado de la solicitud a "Seleccionado"
                            cursor.execute("""
                                UPDATE Solicitud_Empleo
                                SET Est_Solicitud = 'Seleccionado'
                                WHERE ID_Solicitud = %s
                            """, [id_solicitud])

                if no_seleccionados:
                    cursor.execute(
                        "UPDATE Solicitud_Empleo SET Est_Solicitud = 'No Seleccionado' WHERE ID_Solicitud IN %s",
                        [tuple(no_seleccionados)]
                    )
                    
            return redirect('success')
    else:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT se.ID_solicitud, c.ID_Cand, c.Nombre_Cand, c.Apell_Cand, d.Nombre_Departamento, ca.Nombre
                FROM Solicitud_Empleo se
                JOIN Candidato c ON se.ID_Cand = c.ID_Cand
                JOIN Vacante v ON se.ID_Vacante = v.ID_Vac
                JOIN Departamento d ON v.ID_Departamento = d.ID_Departamento
                JOIN Cargo ca ON v.ID_Cargo = ca.ID_Cargo
                WHERE se.Est_Solicitud = 'Preseleccionado'
            """)
            candidatos = cursor.fetchall()

        return render(request, 'seleccion_final.html', {'candidatos': candidatos})

def listado_seleccionados(request):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT se.ID_solicitud, c.Nombre_Cand, c.Apell_Cand, se.Fecha_Aplicacion, d.Nombre_Departamento, ca.Nombre
            FROM Solicitud_Empleo se
            JOIN Candidato c ON se.ID_Cand = c.ID_Cand
            JOIN Vacante v ON se.ID_Vacante = v.ID_Vac
            JOIN Departamento d ON v.ID_Departamento = d.ID_Departamento
            JOIN Cargo ca ON v.ID_Cargo = ca.ID_Cargo
            WHERE se.Est_Solicitud = 'Seleccionado'
            ORDER BY se.Fecha_Aplicacion DESC
        """)
        seleccionados = cursor.fetchall()

    return render(request, 'listado_seleccionados.html', {'seleccionados': seleccionados})

def crear_vacante(request):
    if request.method == 'POST':
        id_departamento = request.POST.get('id_departamento')
        id_cargo = request.POST.get('id_cargo')
        ubicacion = request.POST.get('ubicacion')
        beneficio = request.POST.get('beneficio')
        salario = request.POST.get('salario')
        horario = request.POST.get('horario')

        anos_exp = request.POST.get('anos_exp')
        conocimientos = request.POST.getlist('conocimientos')
        titulos = request.POST.getlist('titulos')

        try:
            with connection.cursor() as cursor:
                perfil_id = get_next_id('Perfil', 'ID_Perfil')
                cursor.execute(
                    "INSERT INTO Perfil (ID_Perfil, Anos_Exp) VALUES (%s, %s)",
                    [perfil_id, anos_exp]
                )

                for conocimiento in conocimientos:
                    cursor.execute(
                        "SELECT ID_Conocimiento FROM Conocimiento WHERE Nombre = %s",
                        [conocimiento]
                    )
                    conocimiento_id = cursor.fetchone()
                    if conocimiento_id is None:
                        conocimiento_id = get_next_id('Conocimiento', 'ID_Conocimiento')
                        cursor.execute(
                            "INSERT INTO Conocimiento (ID_Conocimiento, Nombre) VALUES (%s, %s)",
                            [conocimiento_id, conocimiento]
                        )
                    else:
                        conocimiento_id = conocimiento_id[0]
                    cursor.execute(
                        "INSERT INTO PerfilConocimiento (ID_Perfil, ID_Conocimiento) VALUES (%s, %s)",
                        [perfil_id, conocimiento_id]
                    )

                for titulo in titulos:
                    cursor.execute(
                        "SELECT ID_Titulo FROM Titulo WHERE Nombre = %s",
                        [titulo]
                    )
                    titulo_id = cursor.fetchone()
                    if titulo_id is None:
                        titulo_id = get_next_id('Titulo', 'ID_Titulo')
                        cursor.execute(
                            "INSERT INTO Titulo (ID_Titulo, Nombre) VALUES (%s, %s)",
                            [titulo_id, titulo]
                        )
                    else:
                        titulo_id = titulo_id[0]
                    cursor.execute(
                        "INSERT INTO PerfilTitulo (ID_Perfil, ID_Titulo) VALUES (%s, %s)",
                        [perfil_id, titulo_id]
                    )

                vacante_id = get_next_id2('Vacante', 'ID_Vac')
                cursor.execute(
                    "INSERT INTO Vacante (ID_Vac, ID_Departamento, ID_Cargo, ID_Perfil, Ubicacion, Beneficio, Salario, Horario) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                    [vacante_id, id_departamento, id_cargo, perfil_id, ubicacion, beneficio, salario, horario]
                )

            return redirect('success')
        except IntegrityError as e:
            return render(request, 'crear_vacante.html', {'error': str(e)})
    else:
        with connection.cursor() as cursor:
            cursor.execute("SELECT ID_Departamento, Nombre_Departamento FROM Departamento")
            departamentos = cursor.fetchall()
            cursor.execute("SELECT ID_Cargo, Nombre FROM Cargo")
            cargos = cursor.fetchall()
            cursor.execute("SELECT DISTINCT Ubicacion FROM Vacante")
            ubicaciones = cursor.fetchall()

        horarios = [
            "Turno Mañana: 9:00 am a 4:00 pm",
            "Turno Tarde: 12:00 pm a 8:00 pm"
        ]

        return render(request, 'crear_vacante.html', {
            'departamentos': departamentos,
            'cargos': cargos,
            'ubicaciones': ubicaciones,
            'horarios': horarios
        })

def listar_vacantes(request):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT v.ID_Vac, v.Ubicacion, v.Beneficio, v.Salario, v.Horario,
                   d.Nombre_Departamento, c.Nombre AS Cargo,
                   p.Anos_Exp, 
                   array_agg(DISTINCT co.Nombre) AS Conocimientos,
                   array_agg(DISTINCT t.Nombre) AS Titulos
            FROM Vacante v
            JOIN Departamento d ON v.ID_Departamento = d.ID_Departamento
            JOIN Cargo c ON v.ID_Cargo = c.ID_Cargo
            JOIN Perfil p ON v.ID_Perfil = p.ID_Perfil
            LEFT JOIN PerfilConocimiento pc ON p.ID_Perfil = pc.ID_Perfil
            LEFT JOIN Conocimiento co ON pc.ID_Conocimiento = co.ID_Conocimiento
            LEFT JOIN PerfilTitulo pt ON p.ID_Perfil = pt.ID_Perfil
            LEFT JOIN Titulo t ON pt.ID_Titulo = t.ID_Titulo
            GROUP BY v.ID_Vac, v.Ubicacion, v.Beneficio, v.Salario, v.Horario,
                     d.Nombre_Departamento, c.Nombre, p.Anos_Exp
            ORDER BY v.ID_Vac;
        """)
        vacantes = cursor.fetchall()

    return render(request, 'listar_vacantes.html', {'vacantes': vacantes})

def programar_entrevista(request):
    if request.method == 'POST':
        id_solicitud = request.POST.get('id_solicitud')
        fecha_eva = request.POST.get('fecha_eva')
        hora_entrevista = request.POST.get('hora_entrevista')
        id_empleado = request.POST.get('id_empleado')

        try:
            with connection.cursor() as cursor:
                entrevista_id = get_next_id('Entrevista', 'ID_Entrevista')
                evaluacion_id = get_next_id('Evaluacion', 'ID_Evaluacion')  # Asumiendo que la evaluación se crea al mismo tiempo
                cursor.execute(
                    "INSERT INTO Evaluacion (ID_Evaluacion, Result_Evaluacion, Duracion_Evaluacion, Estado_Evaluacion) VALUES (%s, %s, %s, %s)",
                    [evaluacion_id, '', 0, 'Pendiente']
                )
                cursor.execute(
                    "INSERT INTO Entrevista (ID_Entrevista, Fecha_Eva, Hora_Entrevista, ID_Solicitud, ID_Empleado, ID_Evaluacion) VALUES (%s, %s, %s, %s, %s, %s)",
                    [entrevista_id, fecha_eva, hora_entrevista, id_solicitud, id_empleado, evaluacion_id]
                )
            return redirect('success')
        except IntegrityError as e:
            return render(request, 'programar_entrevista.html', {'error': str(e)})
    else:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT se.ID_Solicitud, c.Nombre_Cand, c.Apell_Cand
                FROM Solicitud_Empleo se
                JOIN Candidato c ON se.ID_Cand = c.ID_Cand
                WHERE se.Est_Solicitud = 'Preseleccionado'
            """)
            solicitudes = cursor.fetchall()
            cursor.execute("SELECT ID_Empleado, Nombre_Empleado FROM Empleado")
            empleados = cursor.fetchall()

        return render(request, 'programar_entrevista.html', {
            'solicitudes': solicitudes,
            'empleados': empleados
        })
def listar_entrevistas(request):
    estado = request.GET.get('estado', 'Pendiente')  # Default to 'Pendiente'
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT e.ID_Entrevista, e.Fecha_Eva, e.Hora_Entrevista, 
                   se.ID_Solicitud, c.Nombre_Cand, c.Apell_Cand,
                   em.Nombre_Empleado, ev.Estado_Evaluacion
            FROM Entrevista e
            JOIN Solicitud_Empleo se ON e.ID_Solicitud = se.ID_Solicitud
            JOIN Candidato c ON se.ID_Cand = c.ID_Cand
            JOIN Empleado em ON e.ID_Empleado = em.ID_Empleado
            JOIN Evaluacion ev ON e.ID_Evaluacion = ev.ID_Evaluacion
            WHERE ev.Estado_Evaluacion = %s
            ORDER BY e.Fecha_Eva, e.Hora_Entrevista
        """, [estado])
        entrevistas = cursor.fetchall()

    return render(request, 'listar_entrevistas.html', {'entrevistas': entrevistas, 'estado': estado})

def actualizar_evaluacion(request):
    if request.method == 'POST':
        id_entrevista = request.POST['id_entrevista']
        result_evaluacion = request.POST['result_evaluacion']
        duracion_evaluacion = request.POST['duracion_evaluacion']
        estado_evaluacion = request.POST['estado_evaluacion']
        competencias = request.POST.getlist('competencias[]')

        with connection.cursor() as cursor:
            # Actualizar evaluación
            cursor.execute("""
                UPDATE Evaluacion
                SET Result_Evaluacion = %s,
                    Duracion_Evaluacion = %s,
                    Estado_Evaluacion = %s
                WHERE ID_Evaluacion = (
                    SELECT ID_Evaluacion
                    FROM Entrevista
                    WHERE ID_Entrevista = %s
                )
            """, [result_evaluacion, duracion_evaluacion, estado_evaluacion, id_entrevista])

            # Obtener ID de la evaluación
            cursor.execute("""
                SELECT ID_Evaluacion
                FROM Entrevista
                WHERE ID_Entrevista = %s
            """, [id_entrevista])
            id_evaluacion = cursor.fetchone()[0]

            # Eliminar competencias actuales
            cursor.execute("""
                DELETE FROM EvaluacionXCompetencia
                WHERE ID_Evaluacion = %s
            """, [id_evaluacion])

            # Insertar nuevas competencias
            for competencia_id in competencias:
                cursor.execute("""
                    INSERT INTO EvaluacionXCompetencia (ID_Evaluacion, ID_Competencia)
                    VALUES (%s, %s)
                """, [id_evaluacion, competencia_id])

        return redirect('success')
    else:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT e.ID_Entrevista, c.Nombre_Cand, c.Apell_Cand, ev.Result_Evaluacion, ev.Duracion_Evaluacion, ev.Estado_Evaluacion
                FROM Entrevista e
                JOIN Solicitud_Empleo se ON e.ID_Solicitud = se.ID_Solicitud
                JOIN Candidato c ON se.ID_Cand = c.ID_Cand
                JOIN Evaluacion ev ON e.ID_Evaluacion = ev.ID_Evaluacion
                WHERE se.Est_Solicitud = 'Preseleccionado'
            """)
            entrevistas = cursor.fetchall()
            
            cursor.execute("SELECT ID_Competencia, Nombre FROM Competencia")
            competencias = cursor.fetchall()

        return render(request, 'actualizar_evaluacion.html', {'entrevistas': entrevistas, 'competencias': competencias})

def listar_evaluaciones(request):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT ev.ID_Evaluacion, ev.Result_Evaluacion, ev.Duracion_Evaluacion, ev.Estado_Evaluacion,
                   COALESCE(STRING_AGG(c.Nombre, ', '), 'Ninguna') AS Competencias
            FROM Evaluacion ev
            LEFT JOIN EvaluacionXCompetencia ec ON ev.ID_Evaluacion = ec.ID_Evaluacion
            LEFT JOIN Competencia c ON ec.ID_Competencia = c.ID_Competencia
            GROUP BY ev.ID_Evaluacion, ev.Result_Evaluacion, ev.Duracion_Evaluacion, ev.Estado_Evaluacion
            ORDER BY ev.ID_Evaluacion
        """)
        evaluaciones = cursor.fetchall()

    return render(request, 'listar_evaluaciones.html', {'evaluaciones': evaluaciones})

def listar_empleados(request):
    orden = request.GET.get('orden', 'nombre')  # Obtener el parámetro de orden, por defecto 'nombre'
    busqueda = request.GET.get('busqueda', '')  # Obtener el término de búsqueda

    with connection.cursor() as cursor:
        if orden == 'fecha':
            cursor.execute("""
                SELECT ID_Empleado, Nombre_Empleado, Apellido_Empleado, Fecha_Ingreso
                FROM Empleado
                WHERE Nombre_Empleado ILIKE %s OR Apellido_Empleado ILIKE %s
                ORDER BY Fecha_Ingreso DESC
            """, [f'%{busqueda}%', f'%{busqueda}%'])
        else:
            cursor.execute("""
                SELECT ID_Empleado, Nombre_Empleado, Apellido_Empleado, Fecha_Ingreso
                FROM Empleado
                WHERE Nombre_Empleado ILIKE %s OR Apellido_Empleado ILIKE %s
                ORDER BY Nombre_Empleado ASC, Apellido_Empleado ASC
            """, [f'%{busqueda}%', f'%{busqueda}%'])

        empleados = cursor.fetchall()

    return render(request, 'listar_empleados.html', {'empleados': empleados, 'orden': orden, 'busqueda': busqueda})




def modificar_empleado(request, id_empleado):
    if request.method == 'POST':
        nombre_empleado = request.POST['nombre_empleado']
        apellido_empleado = request.POST['apellido_empleado']
        telefono = request.POST['telefono']
        direccion = request.POST['direccion']
        correo = request.POST['correo']
        fecha_nacimiento = request.POST['fecha_nacimiento']
        cant_hijos = request.POST['cant_hijos']
        estado_civil = request.POST['estado_civil']
        dni = request.POST['dni']
        id_departamento = request.POST['id_departamento']
        id_cargo = request.POST['id_cargo']
        estado_laboral = request.POST['estado_laboral']

        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE Empleado
                SET Nombre_Empleado = %s,
                    Apellido_Empleado = %s,
                    Telefono = %s,
                    Direccion = %s,
                    Correo = %s,
                    Fecha_Nacimiento = %s,
                    Cant_Hijos = %s,
                    Estado_Civil = %s,
                    DNI = %s,
                    ID_Departamento = %s,
                    ID_Cargo = %s,
                    Estado_laboral = %s
                WHERE ID_Empleado = %s
            """, [
                nombre_empleado, apellido_empleado, telefono, direccion, correo,
                fecha_nacimiento, cant_hijos, estado_civil, dni, id_departamento, id_cargo, estado_laboral, id_empleado
            ])
        
        return redirect('listar_empleados')

    else:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT ID_Empleado, Nombre_Empleado, Apellido_Empleado, Telefono, Direccion, Correo, Fecha_Nacimiento, Cant_Hijos, Estado_Civil, DNI, ID_Departamento, ID_Cargo, Estado_laboral
                FROM Empleado
                WHERE ID_Empleado = %s
            """, [id_empleado])
            empleado = cursor.fetchone()

            cursor.execute("SELECT ID_Departamento, Nombre_Departamento FROM Departamento")
            departamentos = cursor.fetchall()

            cursor.execute("SELECT ID_Cargo, Nombre FROM Cargo")
            cargos = cursor.fetchall()

        if empleado:
            empleado_data = {
                'id_empleado': empleado[0],
                'nombre_empleado': empleado[1],
                'apellido_empleado': empleado[2],
                'telefono': empleado[3],
                'direccion': empleado[4],
                'correo': empleado[5],
                'fecha_nacimiento': empleado[6].strftime('%Y-%m-%d'),
                'cant_hijos': empleado[7],
                'estado_civil': empleado[8],
                'dni': empleado[9],
                'id_departamento': empleado[10],
                'id_cargo': empleado[11],
                'estado_laboral': empleado[12]
            }

        return render(request, 'modificar_empleado.html', {
            'empleado': empleado_data,
            'departamentos': departamentos,
            'cargos': cargos
        })

# Capacitacion

from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.db import connection
from django.urls import reverse
from datetime import datetime
from django.views.decorators.csrf import csrf_exempt

def tablacargo(request):
    cursor=connection.cursor()
    cursor.execute("select Cargo.Nombre, Cargo.Descripcion from Cargo")
    results=cursor.fetchall()
    return render(request,"signup.html",{'Cargo':results})
      
def departamentos_nombres(request):
    with connection.cursor() as cursor:
        cursor.execute('SELECT nombre_departamento FROM Departamento')
        nombre_deps=cursor.fetchall()
    return render(request,'registro_empleado.html',{"nombre_deps":nombre_deps})

def registrar_empleado(request):
    if request.method=='POST': 
        codigo_encargado = request.POST['codigo_encargado']
        motivo = request.POST['motivo']
        departamento_name = request.POST['ID_Departamento']
        numero_sesiones = request.POST['numero_sesiones']
        fecha_inicio= request.POST['fecha_inicio']
        fecha_fin = request.POST['fecha_fin']

        num=int(numero_sesiones)+1

        try:
            # Create a cursor object
            cursor = connection.cursor()

            # Get the ID of the department based on its name
            cursor.execute("SELECT id_departamento FROM Departamento WHERE nombre_departamento = %s", [departamento_name])
            departamento_result = cursor.fetchone()
        except:
            print("Error inserting data:")                

        query="INSERT INTO Programa_Capacitador (ID_Programa_C,Fecha_Inicio,Fecha_Fin,Motivo,ID_Departamento) VALUES ((SELECT ID_Programa_C FROM Programa_Capacitador ORDER BY ID_Programa_C DESC LIMIT 1)+1,%s, %s, %s, %s)"

        with connection.cursor() as cursor:
            cursor.execute(query,[fecha_inicio,fecha_fin,motivo,departamento_result])
        


        return redirect("registro_sesion/")
    

    return render(request,"registro_empleado.html")

def registrar_sesion(request):
        
    fecha_sesion=request.POST['fecha_sesion']
    hora_sesion=request.POST['hora_sesion']

    query="INSERT INTO Sesion(ID_Sesion,Estado,Fecha,Hora,ID_Programa_C) VALUES((SELECT ID_Sesion FROM Sesion ORDER BY ID_Sesion DESC LIMIT 1)+1,%s,%s,%s,(SELECT ID_Programa_C FROM Programa_Capacitador ORDER BY ID_Programa_C DESC LIMIT 1));"

    estado_default="Pendiente"

    with connection.cursor() as cursor:
        cursor.execute(query,[estado_default,fecha_sesion,hora_sesion]) 
    return render(request,"registro_sesion.html")

def matricular_empleado(request):
    codigo_programa=request.POST['codigo_programa']
    id_empleado=request.POST['cod_empleado']
    estado_default='Matriculado'

    query="INSERT INTO Lista_Matricula(ID_Programa_C,ID_Empleado,Estado_Matricula) VALUES(%s,%s,%s);"

    with connection.cursor() as cursor:
        cursor.execute(query,[codigo_programa,id_empleado,estado_default])
    return render(request,"matricular_empleado.html")

def helloworld1(request):
    return render(request,'signup.html')

def mostrarventana(request):
    return render(request,'registro_empleado.html')

def registro_sesion_ventana(request):
    return render(request,'registro_sesion.html')

def matricula_empleado_ventana(request):
    return render(request, "matricular_empleado.html")

def mostrar_matricula_ventana(request):
    return render(request,'lista_matricula_cap.html')

def muestra_capacitaciones(request):
    cursor=connection.cursor()
    cursor.execute("SELECT p.id_programa_c,	d.Nombre_Departamento,COUNT(DISTINCT s.ID_Sesion) AS Numero_Sesiones,p.Fecha_Inicio AS Fecha_Programa,COUNT(DISTINCT lm.ID_Empleado) AS Total_Empleados,p.Motivo FROM Programa_Capacitador p JOIN Departamento d ON p.ID_Departamento = d.ID_Departamento LEFT JOIN Sesion s ON p.ID_Programa_C = s.ID_Programa_C LEFT JOIN Lista_Matricula lm ON p.ID_Programa_C = lm.ID_Programa_C GROUP BY p.id_programa_c,d.Nombre_Departamento, p.Fecha_Inicio, p.Motivo ORDER BY p.id_programa_c;")
    results=cursor.fetchall()
    return render(request,'muestra_capacitaciones.html',{'solicitudes':results})

def ingresarIdPrograma(request):
    id_programa=request.POST['id_programa']
    return redirect(f'/mostrarMatricula/{id_programa}')

def mostrarMatricula(request,id_programa):
    query="SELECT CONCAT(Empleado.Nombre_Empleado, ' ', Empleado.Apellido_Empleado) AS Nombre_Completo,	Empleado.ID_Empleado,Lista_Matricula.Estado_Matricula FROM Empleado JOIN Lista_Matricula ON Empleado.ID_Empleado= Lista_Matricula.ID_Empleado JOIN Programa_Capacitador ON Lista_Matricula.ID_Programa_C = Programa_Capacitador.ID_Programa_C WHERE Programa_Capacitador.ID_Programa_C = %s;"

    with connection.cursor() as cursor:
        cursor.execute(query,[id_programa])
        result=cursor.fetchall()
    return render(request,"mostrarMatricula.html",{'matricula':result})

def ventana_asistencia(request):
    return render(request,"actualizar_asistencia.html")

def ingresarIdSesion(request):
    id_sesion=request.POST['id_sesion']
    fecha_sesion=request.POST['fecha_sesion']
    codigo_empleado=request.POST['codigo_empleado']
    asistencia=request.POST['asistencia']

    query="UPDATE Empleado_Sesion SET Asistencia = %s WHERE ID_Sesion IN (%s) AND ID_Empleado IN (%s);"

    with connection.cursor() as cursor:
        cursor.execute(query,[asistencia,id_sesion,codigo_empleado])

    return redirect(f'/mostrarAsistencia/{id_sesion}')

def mostrarAsistencia(request,id_sesion):
    query="SELECT CONCAT(Empleado.Nombre_Empleado, ' ', Empleado.Apellido_Empleado) AS Nombre_Completo, Empleado.ID_Empleado, Empleado_Sesion.Asistencia FROM Empleado INNER JOIN Empleado_Sesion ON Empleado.ID_Empleado=Empleado_Sesion.ID_Empleado INNER JOIN Sesion ON Empleado_Sesion.ID_Sesion=Sesion.ID_Sesion WHERE Sesion.ID_Sesion=%s;"

    with connection.cursor() as cursor:
        cursor.execute(query,[id_sesion])
        result=cursor.fetchall()
    
        
    return render(request,"actualizar_asistencia_2.html",{"Sesion":result})

#Cese

from django.shortcuts import render


def login(request):
    if request.method == "POST":
        codigo_empleado = request.POST.get("codigo_empleado")
        password = request.POST.get("password")

        query_verificar_usuario = """
            SELECT id_empleado 
            FROM empleado 
            WHERE id_empleado = %s AND contrasena = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(query_verificar_usuario, [codigo_empleado, password])
            resultado = cursor.fetchone()

        query_verificar_estado = """
            SELECT id_cese
            FROM empleado AS E
            INNER JOIN cese AS C ON C.id_empleado = E.id_empleado
            WHERE C.id_empleado = %s AND E.Estado_laboral='cesado'
        """
        with connection.cursor() as cursor:
            cursor.execute(query_verificar_estado, [codigo_empleado])
            estado = cursor.fetchone()

        query_verificar_cargo = """
            SELECT id_empleado, id_cargo 
            FROM empleado 
            WHERE id_cargo BETWEEN 1 AND 4
        """
        with connection.cursor() as cursor:
            cursor.execute(query_verificar_cargo)
            cargo = cursor.fetchone()

        if resultado:
            if estado:
                request.session['id_cese'] = estado[0]
                return redirect('cese5')
            
            elif cargo:
                request.session['id_supervisor'] = resultado[0]
                return redirect('seleccion')

    return render(request, 'login.html')

def seleccion(request):
    return render(request, 'seleccion.html')

def CeseSeleccion(request):
    return render(request, 'CeseSeleccion.html')

def cese1(request):
    query_nuevo_id_cese = """
        SELECT COALESCE(MAX(id_cese), 0) + 1 
        FROM cese
    """
    with connection.cursor() as cursor:
        cursor.execute(query_nuevo_id_cese)
        id_cese = cursor.fetchone()[0]

    # Guardar id_cese en la sesión
    request.session['id_cese'] = id_cese
    
    id_supervisor = request.session.get('id_supervisor')
    if not id_supervisor:
        return redirect('login')

    resultados_empleados = []
    id_empleado = None

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "buscar":
            apellido_entrante = request.POST.get("buscador_apellido")
            query_detalle_reporte = """
                SELECT E.DNI, E.nombre_empleado AS NOMBRE, E.apellido_empleado AS APELLIDO, D.nombre_departamento, E.id_empleado 
                FROM empleado AS E 
                INNER JOIN departamento AS D ON E.id_departamento = D.id_departamento 
                WHERE E.apellido_empleado LIKE %s
            """
            with connection.cursor() as cursor:
                cursor.execute(query_detalle_reporte, [f'%{apellido_entrante}%'])
                resultados_empleados = cursor.fetchall()

        elif action == "seleccionar_empleado":
            id_empleado = request.POST.get("seleccionar_empleado")
            request.session['id_empleado'] = id_empleado

        elif action == "enviar_cese":
            id_empleado = request.session.get('id_empleado')
            if not id_empleado:
                return redirect('cese1')

            tipo_cese = request.POST.get("tipo_cese")
            motivo_cese = request.POST.get("motivo_cese")
            fecha_cese = request.POST.get("fecha_cese")
            cant_deuda = request.POST.get("cant_deuda", None)  # Deuda opcional

            query_nuevo_id_cese = """
                SELECT COALESCE(MAX(id_cese), 0) + 1 
                FROM cese
            """
            with connection.cursor() as cursor:
                cursor.execute(query_nuevo_id_cese)
                comparar = cursor.fetchone()[0]

            if(comparar == id_cese):

                if motivo_cese:
                    query_insertar_cese = """
                        INSERT INTO cese (id_cese, tipo_cese, motivo_cese, fecha_inicio_cese, id_supervisor, id_empleado) 
                        VALUES (%s, %s, %s, %s, %s, %s);

                        UPDATE empleado
                        SET Estado_laboral = 'cesado'
                        WHERE id_empleado = %s;
                    """
                    with connection.cursor() as cursor:
                        cursor.execute(query_insertar_cese, [id_cese, tipo_cese, motivo_cese, fecha_cese, id_supervisor, id_empleado, id_empleado])
                else:
                    query_insertar_cese = """
                        INSERT INTO cese (id_cese, tipo_cese, motivo_cese, fecha_inicio_cese, id_supervisor, id_empleado) 
                        VALUES (%s, %s, Null, %s, %s, %s);

                        UPDATE empleado
                        SET Estado_laboral = 'cesado'
                        WHERE id_empleado = %s;
                    """
                    with connection.cursor() as cursor:
                        cursor.execute(query_insertar_cese, [id_cese, tipo_cese, fecha_cese, id_supervisor, id_empleado, id_empleado])

                if cant_deuda:
                    query_insertar_deuda = """
                        INSERT INTO beneficios_cese (id_beneficios, id_tipo, monto, id_cese)
                        VALUES (
                            (SELECT COALESCE(MAX(id_beneficios), 0) + 1 FROM beneficios_cese), 
                            5, 
                            -1 * %s, 
                            %s
                        );
                    """
                    with connection.cursor() as cursor:
                        cursor.execute(query_insertar_deuda, [cant_deuda, id_cese])  
            
            else:
                
                query_correccion = """
                    UPDATE empleado
                    SET Estado_laboral = 'activo'
                    WHERE id_empleado = (SELECT id_empleado FROM cese WHERE id_cese=%s);
                """
                with connection.cursor() as cursor:
                    cursor.execute(query_correccion,[id_cese])

                if motivo_cese:
                    query_insertar_cese = """
                        UPDATE cese 
                        SET 
                            tipo_cese = %s, 
                            motivo_cese = %s, 
                            fecha_inicio_cese = %s, 
                            id_supervisor = %s, 
                            id_empleado = %s
                        WHERE id_cese = %s;

                        UPDATE empleado
                        SET Estado_laboral = 'cesado'
                        WHERE id_empleado = %s;
                    """
                    with connection.cursor() as cursor:
                        cursor.execute(query_insertar_cese, [tipo_cese, motivo_cese, fecha_cese, id_supervisor, id_empleado, id_cese, id_empleado])
                else:
                    query_insertar_cese = """
                        UPDATE cese 
                        SET 
                            tipo_cese = %s, 
                            motivo_cese = null, 
                            fecha_inicio_cese = %s, 
                            id_supervisor = %s, 
                            id_empleado = %s
                        WHERE id_cese = %s;

                        UPDATE empleado
                        SET Estado_laboral = 'cesado'
                        WHERE id_empleado = %s;
                    """
                    with connection.cursor() as cursor:
                        cursor.execute(query_insertar_cese, [tipo_cese, fecha_cese, id_supervisor, id_empleado, id_cese, id_empleado])

                if cant_deuda:
                    query_insertar_deuda = """
                        UPDATE beneficios_cese 
                        SET
                            monto = -1 * %s
                        WHERE id_Cese =%s and id_tipo=5
                    """
                    with connection.cursor() as cursor:
                        cursor.execute(query_insertar_deuda, [cant_deuda, id_cese]) 

            return redirect('cese2', id_cese=id_cese)

    return render(request, 'cese1.html', {'empleados': resultados_empleados})

def cese2(request, id_cese):
    query_revisar_empleado = """
        SELECT id_empleado, nombre, departamento, cargo, fecha_cese, tipo_cese, motivo, id_supervisor 
        FROM detalles_cese
        WHERE id_cese = %s
    """
    with connection.cursor() as cursor:
        cursor.execute(query_revisar_empleado, [id_cese])
        resultados_revisar = cursor.fetchall()

    query_montos = """
        SELECT
            SUM(B.monto)
        FROM cese AS C
        INNER JOIN beneficios_cese AS B ON C.id_cese = B.id_cese
        WHERE C.id_cese = %s
    """
    with connection.cursor() as cursor:
        cursor.execute(query_montos, [id_cese])
        resultados_monto = cursor.fetchall()

    return render(request, 'cese2.html', {'revisar': resultados_revisar, 'beneficios': resultados_monto})

def cese3(request):

    id_cese = request.session.get('id_cese')
    if not id_cese:
        return redirect('seleccion')

    if request.method == "POST":
        action = request.POST.get("action")

        if action == 'preguntas_predeterminadas':
            # Primero, insertar el cuestionario si no existe
            query_existe_cuestionario = """
                SELECT id_cuestionario FROM cuestionario_salida WHERE id_cese = %s
            """
            with connection.cursor() as cursor:
                cursor.execute(query_existe_cuestionario, [id_cese])
                existe_cuestionario = cursor.fetchone()

            if not existe_cuestionario:
                query_insertar_cuestionario = """
                    WITH last_cuestionario AS (
                        SELECT COALESCE(MAX(id_cuestionario), 0) + 1 AS id_cuestionario FROM cuestionario_salida
                    )
                    INSERT INTO cuestionario_salida (id_cuestionario, id_cese)
                    VALUES (
                        (SELECT id_cuestionario FROM last_cuestionario),
                        %s
                    )
                    RETURNING id_cuestionario
                """
                with connection.cursor() as cursor:
                    cursor.execute(query_insertar_cuestionario, [id_cese])
                    id_cuestionario = cursor.fetchone()[0]
                    request.session['id_cuestionario'] = id_cuestionario
            else:
                id_cuestionario = existe_cuestionario[0]
                request.session['id_cuestionario'] = id_cuestionario

            # Insertar las preguntas predeterminadas
            query_insertar_preguntas = """
                WITH last_id AS (
                    SELECT COALESCE(MAX(id_pregunta), 0) AS id_pregunta FROM pregunta_salida
                )
                INSERT INTO pregunta_salida (id_pregunta, pregunta_salida, id_cuestionario)
                VALUES
                    ((SELECT id_pregunta FROM last_id) + 1, '¿Cómo describirías tu experiencia en tu empresa?', %s),
                    ((SELECT id_pregunta FROM last_id) + 2, '¿Qué mejorarías en la empresa?', %s),
                    ((SELECT id_pregunta FROM last_id) + 3, '¿Qué no te gusta de tu empresa?', %s)
            """
            with connection.cursor() as cursor:
                cursor.execute(query_insertar_preguntas, [id_cuestionario, id_cuestionario, id_cuestionario])

        elif action == "enviar_pregunta":
            pregunta_nueva = request.POST.get("pregunta_nueva")

            query_existe_cuestionario = """
                SELECT id_cuestionario FROM cuestionario_salida WHERE id_cese = %s
            """
            with connection.cursor() as cursor:
                cursor.execute(query_existe_cuestionario, [id_cese])
                existe_cuestionario = cursor.fetchone()

            if existe_cuestionario:
                id_cuestionario = existe_cuestionario[0]
                request.session['id_cuestionario'] = id_cuestionario

                query_insertar_nueva_pregunta = """
                    WITH last_id AS (
                        SELECT COALESCE(MAX(id_pregunta), 0) AS id_pregunta FROM pregunta_salida
                    )
                    INSERT INTO pregunta_salida (id_pregunta, pregunta_salida, id_cuestionario)
                    VALUES (
                        (SELECT id_pregunta FROM last_id) + 1,
                        %s,
                        %s
                    )
                """
                with connection.cursor() as cursor:
                    cursor.execute(query_insertar_nueva_pregunta, [pregunta_nueva, id_cuestionario])

            else:
                query_insertar_cuestionario = """
                    WITH last_cuestionario AS (
                        SELECT COALESCE(MAX(id_cuestionario), 0) + 1 AS id_cuestionario FROM cuestionario_salida
                    )
                    INSERT INTO cuestionario_salida (id_cuestionario, id_cese)
                    VALUES (
                        (SELECT id_cuestionario FROM last_cuestionario),
                        %s
                    )
                    RETURNING id_cuestionario
                """
                with connection.cursor() as cursor:
                    cursor.execute(query_insertar_cuestionario, [id_cese])
                    id_cuestionario = cursor.fetchone()[0]
                    request.session['id_cuestionario'] = id_cuestionario

                query_insertar_nueva_pregunta = """
                    WITH last_id AS (
                        SELECT COALESCE(MAX(id_pregunta), 0) + 1 AS id_pregunta FROM pregunta_salida
                    )
                    INSERT INTO pregunta_salida (id_pregunta, pregunta_salida, id_cuestionario)
                    VALUES (
                        (SELECT id_pregunta FROM last_id),
                        %s,
                        %s
                    )
                """
                with connection.cursor() as cursor:
                    cursor.execute(query_insertar_nueva_pregunta, [pregunta_nueva, id_cuestionario])

    return render(request, 'cese3.html')

def cese4(request):
    return render(request, 'cese4.html')

def cese8(request):
    resultados_empleados = []
    resultados_revisar = []
    resultados_monto = []
    cuestionario = []

    id_empleado = None

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "buscar":
            apellido_entrante = request.POST.get("buscador_apellido")
            query_detalle_reporte = """
                SELECT E.DNI, E.nombre_empleado AS NOMBRE, E.apellido_empleado AS APELLIDO, D.nombre_departamento, E.id_empleado 
                FROM empleado AS E 
                INNER JOIN departamento AS D ON E.id_departamento = D.id_departamento 
                INNER JOIN cese AS C ON E.id_empleado=C.id_empleado
                WHERE E.apellido_empleado LIKE %s
            """
            with connection.cursor() as cursor:
                cursor.execute(query_detalle_reporte, [f'%{apellido_entrante}%'])
                resultados_empleados = cursor.fetchall()

        elif action == "seleccionar_empleado":
            id_empleado = request.POST.get("seleccionar_empleado")
            request.session['id_empleado'] = id_empleado

            query_revisar_empleado = """
                SELECT id_empleado, nombre, departamento, cargo, fecha_cese, tipo_cese, motivo, id_supervisor 
                FROM detalles_cese
                WHERE id_empleado = %s
            """
            with connection.cursor() as cursor:
                cursor.execute(query_revisar_empleado, [id_empleado])
                resultados_revisar = cursor.fetchall()

            query_montos = """
                SELECT SUM(B.monto) 
                FROM beneficios_cese AS B
                INNER JOIN CESE AS C ON C.id_cese = B.id_cese
                WHERE C.id_empleado = %s
            """
            with connection.cursor() as cursor:
                cursor.execute(query_montos, [id_empleado])
                resultados_monto = cursor.fetchall()

            query_cuestionario = """
                SELECT pregunta_salida, respuesta_salida
                FROM pregunta_salida AS P
                INNER JOIN respuesta_salida AS R ON P.id_pregunta = R.id_pregunta
                INNER JOIN cuestionario_salida AS C ON C.id_cuestionario = P.id_cuestionario
                INNER JOIN cese AS CE ON CE.id_cese = C.id_Cese
                WHERE id_empleado = %s
            """
            with connection.cursor() as cursor:
                cursor.execute(query_cuestionario, [id_empleado])
                cuestionario = cursor.fetchall()

    return render(request, 'cese8.html', {'empleados': resultados_empleados, 'revisar': resultados_revisar, 'beneficios': resultados_monto, 'banco':cuestionario})

def cese5(request):
    return render(request, 'cese5.html')

def cese6(request):
    id_cuestionario = request.session.get('id_cuestionario')
    if not id_cuestionario:
        return redirect('cese3')

    if request.method == "POST" and request.POST.get("action") == "confirmar":
        query_buscar_pregunta = """
            SELECT id_pregunta 
            FROM pregunta_salida
            WHERE id_cuestionario=%s
        """
        with connection.cursor() as cursor:
            cursor.execute(query_buscar_pregunta, [id_cuestionario])
            preguntas_ids = cursor.fetchall()
        
        respuestas = {}
        for index, pregunta in enumerate(preguntas_ids, start=1):
            respuesta = request.POST.get(f'respuesta_{index}')
            if respuesta:
                respuestas[pregunta[0]] = respuesta

        # Insertar respuestas en la base de datos
        query_insertar_respuesta = """
            INSERT INTO respuesta_salida (id_respuesta, id_pregunta, respuesta_salida)
            VALUES ((SELECT COALESCE(MAX(id_respuesta), 0) + 1 FROM respuesta_salida), %s, %s)
        """
        with connection.cursor() as cursor:
            for id_pregunta, respuesta in respuestas.items():
                cursor.execute(query_insertar_respuesta, [id_pregunta, respuesta])
        
        return redirect('cese7')  # Redirigir a una página de confirmación

    query_buscar_pregunta = """
        SELECT pregunta_salida 
        FROM pregunta_salida
        WHERE id_cuestionario=%s
    """
    with connection.cursor() as cursor:
        cursor.execute(query_buscar_pregunta, [id_cuestionario])
        resultados_preguntas = cursor.fetchall()

    return render(request, 'cese6.html', {'preguntas': resultados_preguntas})

def cese7(request):
    return render(request, 'cese7.html')

def cese9(request):
    resultado_detalle = []
    resultado_total = []
    
    if request.method == "POST":
        action = request.POST.get("action")

        if action == "generar_reporte":
            fecha_inicio = request.POST.get("fecha_inicio")
            fecha_fin = request.POST.get("fecha_fin")

            if fecha_fin and fecha_inicio:

                query_detalle_reporte = """
                    SELECT 
                        COUNT(id_cese),tipo_cese
                    FROM detalles_cese
                    WHERE fecha_cese BETWEEN %s AND %s
                    GROUP BY tipo_cese
                """
                with connection.cursor() as cursor:
                    cursor.execute(query_detalle_reporte, [fecha_inicio, fecha_fin])
                    resultado_detalle = cursor.fetchall()

                query_total = """
                    SELECT COUNT(id_cese)
                    FROM detalles_cese
                    WHERE fecha_cese BETWEEN %s AND %s
                """
                with connection.cursor() as cursor:
                    cursor.execute(query_total, [fecha_inicio, fecha_fin])
                    resultado_total = cursor.fetchall()

    return render(request, 'cese9.html', {'detalles': resultado_detalle, 'todo': resultado_total})

# Desempeño

from django.shortcuts import render, redirect
from django.db import connection

# Create your views here.
def baseRevisar(request):
    with connection.cursor() as cursor:
        cursor.execute('SELECT ID_Tipo_Cuestionario, Tipo FROM Tipo_Cuestionario;')
        tiposCuestionario = cursor.fetchall()

    with connection.cursor() as cursor:
        cursor.execute('SELECT Id_Tipo_Respuesta,Tipo from Tipo_Respuesta;')
        tiposRespuesta = cursor.fetchall()

    query="Select Em.Id_Empleado,Em.Apellido_Empleado,Em.Nombre_Empleado, TR.Tipo as Calificacion from Empleado Em inner join Cuestionario_Empleado CE on Em.Id_Empleado=CE.Id_Empleado left join Reporte Re on Re.Id_Cuestionario_Empleado=Ce.Id_Cuestionario_Empleado left join Tipo_Respuesta TR on Re.Calificacion_Empleado=TR.Id_Tipo_Respuesta;"

    with connection.cursor() as cursor:
        cursor.execute(query)
        tablaEmpleados= cursor.fetchall()

    context = {
        "tiposCuestionario": tiposCuestionario,
        "tiposRespuesta": tiposRespuesta,
        "tablaEmpleados": tablaEmpleados
    }

    return render(request,'tablaEmpleados.html',context)


def revisarTipoCuestionario(request,id_tipo_cuestionario):
    with connection.cursor() as cursor:
        cursor.execute('SELECT ID_Tipo_Cuestionario, Tipo FROM Tipo_Cuestionario;')
        tiposCuestionario = cursor.fetchall()

    with connection.cursor() as cursor:
        cursor.execute('SELECT Id_Tipo_Respuesta,Tipo from Tipo_Respuesta;')
        tiposRespuesta = cursor.fetchall()

    query="Select Em.Id_Empleado,Em.Apellido_Empleado,Em.Nombre_Empleado, TR.Tipo as Calficacion from Empleado Em inner join Cuestionario_Empleado CE on Em.Id_Empleado=CE.Id_Empleado inner join Cuestionario CU on CE.ID_Cuestionario=Cu.ID_Cuestionario left join Reporte Re on Re.ID_Cuestionario_Empleado=Ce.ID_Cuestionario_Empleado left join Tipo_Respuesta TR on TR.ID_Tipo_Respuesta=Re.Calificacion_Empleado where Cu.ID_Tipo_Cuestionario=%s;"

    with connection.cursor() as cursor:
        cursor.execute(query,[id_tipo_cuestionario])
        tablaEmpleados= cursor.fetchall()
    
    context = {
        "tiposCuestionario": tiposCuestionario,
        "tiposRespuesta": tiposRespuesta,
        "tablaEmpleados": tablaEmpleados
    }

    return render(request,'tablaTipoCuestionario.html',context)


def revisarApellido(request):
    apellido= request.POST['apellido']

    with connection.cursor() as cursor:
        cursor.execute('SELECT ID_Tipo_Cuestionario, Tipo FROM Tipo_Cuestionario;')
        tiposCuestionario = cursor.fetchall()

    with connection.cursor() as cursor:
        cursor.execute('SELECT Id_Tipo_Respuesta,Tipo from Tipo_Respuesta;')
        tiposRespuesta = cursor.fetchall()

    query="Select Em.Id_Empleado,Em.Apellido_Empleado,Em.Nombre_Empleado, TR.Tipo as Calficacion from Empleado Em inner join Cuestionario_Empleado CE on Em.Id_Empleado=CE.Id_Empleado left join Reporte Re on Re.ID_Cuestionario_Empleado=Ce.ID_Cuestionario_Empleado left join Tipo_Respuesta TR on TR.ID_Tipo_Respuesta=Re.Calificacion_Empleado WHERE Em.Apellido_Empleado=%s;" 

    with connection.cursor() as cursor:
        cursor.execute(query,[apellido])
        tablaApellido= cursor.fetchall() 

    context = {        
        "tiposCuestionario": tiposCuestionario,
        "tiposRespuesta": tiposRespuesta,
        "tablaApellido": tablaApellido
    }


    return render(request,'tablaApellido.html',context)


def revisarCalificacion(request, id_tipo_calificacion):
    with connection.cursor() as cursor:
        cursor.execute('SELECT ID_Tipo_Cuestionario, Tipo FROM Tipo_Cuestionario;')
        tiposCuestionario = cursor.fetchall()

    with connection.cursor() as cursor:
        cursor.execute('SELECT Id_Tipo_Respuesta,Tipo from Tipo_Respuesta;')
        tiposRespuesta = cursor.fetchall()

    query="Select Em.Id_Empleado,Em.Apellido_Empleado,Em.Nombre_Empleado, TR.Tipo as Calficacion from Empleado Em inner join Cuestionario_Empleado CE on Em.Id_Empleado=CE.Id_Empleado left join Reporte Re on Re.Id_Cuestionario_Empleado=CE.Id_Cuestionario_Empleado left join Tipo_Respuesta TR on TR.ID_Tipo_Respuesta=Re.Calificacion_Empleado where calificacion_empleado=%s;" 

    with connection.cursor() as cursor:
        cursor.execute(query,[id_tipo_calificacion])
        tablaCalificacion= cursor.fetchall() 

    context = {        
        "tiposCuestionario": tiposCuestionario,
        "tiposRespuesta": tiposRespuesta,
        "tablaCalificacion": tablaCalificacion
    }


    return render(request,'tablaCalificacion.html',context)


def revisarCalificacionNULL(request):
    with connection.cursor() as cursor:
        cursor.execute('SELECT ID_Tipo_Cuestionario, Tipo FROM Tipo_Cuestionario;')
        tiposCuestionario = cursor.fetchall()

    with connection.cursor() as cursor:
        cursor.execute('SELECT Id_Tipo_Respuesta,Tipo from Tipo_Respuesta;')
        tiposRespuesta = cursor.fetchall()

    query="Select Em.Id_Empleado,Em.Apellido_Empleado,Em.Nombre_Empleado, TR.Tipo as Calficacion from Empleado Em inner join Cuestionario_Empleado CE on Em.Id_Empleado=CE.Id_Empleado left join Reporte Re on Re.Id_Cuestionario_Empleado=CE.Id_Cuestionario_Empleado left join Tipo_Respuesta TR on TR.ID_Tipo_Respuesta=Re.Calificacion_Empleado where calificacion_empleado IS NULL" 

    with connection.cursor() as cursor:
        cursor.execute(query)
        tablaCalificacion= cursor.fetchall() 

    context = {        
        "tiposCuestionario": tiposCuestionario,
        "tiposRespuesta": tiposRespuesta,
        "tablaCalificacion": tablaCalificacion
    }


    return render(request,'tablaCalificacion.html',context)



def mostrarReuniones(request):
    query="SELECT Asunto_Reunion, Fecha_Reunion, Hora_Reunion FROM Reunion;"

    with connection.cursor() as cursor:
        cursor.execute(query)
        reuniones=cursor.fetchall()
    
    context={
        "reuniones":reuniones
    }

    return render(request,'reunionesBase.html',context)

def baseResponder(request):
    with connection.cursor() as cursor:
        cursor.execute('SELECT ID_Tipo_Cuestionario, Tipo FROM Tipo_Cuestionario;')
        tiposCuestionario = cursor.fetchall()
    return render(request,'baseResponder.html',{"tiposCuestionario":tiposCuestionario})

def mostrarPreguntasResponder(request,id_tipo_cuestionario):
    with connection.cursor() as cursor:
        cursor.execute('SELECT ID_Tipo_Cuestionario, Tipo FROM Tipo_Cuestionario;')
        tiposCuestionario = cursor.fetchall()

    query=f"SELECT PC.ID_Pregunta, PC.Enunciado_Pregunta FROM Pregunta_Cuestionario PC INNER JOIN Cuestionario C ON PC.ID_Cuestionario = C.ID_Cuestionario WHERE C.ID_Tipo_Cuestionario = {id_tipo_cuestionario};"

    with connection.cursor() as cursor:
        cursor.execute(query)
        preguntas= cursor.fetchall()

    query=f"SELECT Id_Tipo_Respuesta,Tipo from Tipo_Respuesta;"

    with connection.cursor() as cursor:
        cursor.execute(query)
        tiposRespuesta= cursor.fetchall()

    context = {
        "tiposCuestionario": tiposCuestionario,
        "preguntas": preguntas,
        "id_tipo_cuestionario": id_tipo_cuestionario,
        "tiposRespuesta": tiposRespuesta,
    }

    return render(request,'tablaResponder.html',context)

def enviarRespuestas(request):
    id_empleado = request.POST['id_empleado']
    id_tipo_cuestionario = request.POST['id_tipo_cuestionario']
        
    query="INSERT INTO Cuestionario_Empleado(ID_Cuestionario_Empleado,ID_Empleado,ID_Cuestionario,Fecha_Rellenado,Hora_Rellenado) VALUES (CASE WHEN (SELECT MAX(ID_Cuestionario_Empleado) FROM Cuestionario_Empleado) IS NULL THEN 1 ELSE (SELECT MAX(ID_Cuestionario_Empleado) FROM Cuestionario_Empleado) + 1 END,%s,(Select Id_Cuestionario from Cuestionario where Id_tipo_Cuestionario=%s),Current_Date,Current_Time(0));"
 
    with connection.cursor() as cursor:
        cursor.execute(query, [id_empleado, id_tipo_cuestionario])            

    query= "INSERT INTO Respuesta_Cuestionario(ID_Respuesta,ID_Pregunta,ID_Cuestionario_Empleado,ID_Tipo_Respuesta) VALUES (CASE WHEN (SELECT MAX(ID_Respuesta) FROM Respuesta_Cuestionario) IS NULL THEN 1 ELSE (SELECT MAX(ID_Respuesta) FROM Respuesta_Cuestionario) + 1 END, %s,(Select ID_Cuestionario_Empleado FROM Cuestionario_Empleado where ID_Empleado=%s),%s);"

        
    with connection.cursor() as cursor:
        for key, value in request.POST.items():
            if key.startswith('respuesta_'):
                id_pregunta = key.split('_')[1]
                id_tipo_respuesta = value
                cursor.execute(query, [id_pregunta, id_empleado, id_tipo_respuesta])
        
    return redirect(f'/responder/')


def reporteBase(request,id_empleado):


    with connection.cursor() as cursor:
        cursor.execute('SELECT Id_Tipo_Respuesta,Tipo from Tipo_Respuesta;')
        tiposCalificacion= cursor.fetchall()

    query="SELECT DISTINCT Em.id_empleado, Em.apellido_empleado, Em.nombre_empleado, Ce.ID_Cuestionario_Empleado, TC.Tipo FROM Empleado Em INNER JOIN Cuestionario_Empleado CE ON Em.id_empleado = CE.id_empleado INNER JOIN Cuestionario Cu ON CE.id_cuestionario = Cu.id_cuestionario INNER JOIN Tipo_Cuestionario TC ON Cu.id_tipo_cuestionario = TC.id_tipo_cuestionario where em.id_empleado=%s;"

    with connection.cursor() as cursor:
        cursor.execute(query,[id_empleado])
        datosEmpleado= cursor.fetchall()

    query="SELECT ROW_NUMBER() OVER (ORDER BY PC.ID_Pregunta) AS Nº, PC.Enunciado_Pregunta, TR.Tipo AS Respuesta FROM Empleado Em INNER JOIN Cuestionario_Empleado CE ON Em.id_empleado = CE.id_empleado INNER JOIN Respuesta_Cuestionario RC ON CE.ID_Cuestionario_Empleado = RC.ID_Cuestionario_Empleado INNER JOIN Pregunta_Cuestionario PC ON RC.ID_Pregunta = PC.ID_Pregunta INNER JOIN Tipo_Respuesta TR ON RC.ID_Tipo_Respuesta = TR.ID_Tipo_Respuesta WHERE Em.id_empleado = %s;"

    with connection.cursor() as cursor:
        cursor.execute(query,[id_empleado])
        tablaRespuestas= cursor.fetchall()
 
    context = {
        "tiposCalificacion": tiposCalificacion,
        "datosEmpleado": datosEmpleado,
        "tablaRespuestas": tablaRespuestas,
        'id_empleado':id_empleado
    }

    return render(request,'reportebase.html',context)



def confirmarReporte(request):
    id_empleado = request.POST['id_empleado']
    id_evaluador = request.POST['id_evaluador']
    retroalimentacion = request.POST['retroalimentacion']
    calificacion=request.POST['calificacion']

    query="INSERT INTO Reporte (ID_Reporte, ID_Cuestionario_Empleado, Fecha_Ingreso_Empleado, Calificacion_Empleado) VALUES (CASE WHEN (SELECT MAX(ID_Reporte) FROM Reporte) IS NULL THEN 1 ELSE (SELECT MAX(ID_Reporte) FROM Reporte) + 1 END,(Select ID_Cuestionario_Empleado from Cuestionario_Empleado where Id_Empleado=%s),(Select Fecha_Ingreso from Empleado where ID_empleado=%s),%s);"

    with connection.cursor() as cursor:
        cursor.execute(query,[id_empleado,id_empleado,calificacion])
    
    query="INSERT INTO Retroalimentacion (ID_Retroalimentacion, ID_Reporte, Enunciado_Retroalimentacion, ID_Evaluador, Fecha_Retroalimentacion, Hora_Retroalimentacion) VALUES (CASE WHEN (SELECT MAX(ID_Retroalimentacion) FROM Retroalimentacion) IS NULL THEN 1 ELSE (SELECT MAX(ID_Retroalimentacion) FROM Retroalimentacion) + 1 END, (SELECT Re.ID_Reporte FROM Reporte Re INNER JOIN Cuestionario_Empleado CE ON Re.ID_Cuestionario_Empleado = CE.ID_Cuestionario_Empleado WHERE CE.ID_Empleado = %s LIMIT 1),%s, %s, CURRENT_DATE, CURRENT_TIME(0));"

    with connection.cursor() as cursor:
        cursor.execute(query,[id_empleado,retroalimentacion, id_evaluador])   

    return redirect('/revisar/')



def baseProgramarReunion(request):
    return render(request,'baseProgramarReunion.html')

def botonProgramar(request):
    id_organizador=request.POST['id_organizador']
    asunto=request.POST['asunto']
    fecha=request.POST['fecha']
    hora=request.POST['hora']

    query=" INSERT INTO Reunion (ID_Reunion, ID_Organizador, Asunto_Reunion, Fecha_Reunion, Hora_Reunion) VALUES (CASE WHEN (SELECT MAX(ID_Reunion) FROM Reunion) IS NULL THEN 1 ELSE (SELECT MAX(ID_Reunion) FROM Reunion) + 1 END,%s, %s, %s,%s);"

    with connection.cursor() as cursor:
        cursor.execute(query,[id_organizador,asunto,fecha,hora])

    return redirect('/programarReunion/')

# Create your views here.
def baseMisResultados(request):
    return render(request,'baseMisResultados.html')

def ingresarID(request):
    id_empleado=request.POST['id_empleado']
    return redirect(f'/misResultadosID/{id_empleado}/')

def ingresarDNI(request):
    dni=request.POST['dni']
    return redirect(f'/misResultadosDNI/{dni}/')

def ingresarApellido(request):
    apellido=request.POST['apellido']
    return redirect(f'/misResultadosApellido/{apellido}/')


def mostrarResultadosID(request,id_empleado):
    query="SELECT Em.ID_Empleado, Em.Nombre_Empleado, Em.Apellido_Empleado, Re.Fecha_Ingreso_Empleado, TR.Tipo as Calificacion, Ret.Enunciado_Retroalimentacion FROM Empleado Em INNER JOIN Cuestionario_Empleado CE ON Em.ID_Empleado = CE.ID_Empleado INNER JOIN Reporte Re ON CE.ID_Cuestionario_Empleado = Re.ID_Cuestionario_Empleado INNER JOIN Retroalimentacion Ret ON Re.ID_Reporte = Ret.ID_Reporte INNER JOIN Tipo_Respuesta TR ON TR.ID_Tipo_Respuesta=Re.Calificacion_Empleado WHERE Em.ID_Empleado = %s;"

    with connection.cursor() as cursor:
        cursor.execute(query,[id_empleado])
        resultados=cursor.fetchall()

    context={
        "resultados":resultados
    }

    return render(request,'mostrarResultados.html',context)

def mostrarResultadosDNI(request,dni):
    query="SELECT Em.ID_Empleado, Em.Nombre_Empleado, Em.Apellido_Empleado, Re.Fecha_Ingreso_Empleado, TR.Tipo as Calificacion, Ret.Enunciado_Retroalimentacion FROM Empleado Em INNER JOIN Cuestionario_Empleado CE ON Em.ID_Empleado = CE.ID_Empleado INNER JOIN Reporte Re ON CE.ID_Cuestionario_Empleado = Re.ID_Cuestionario_Empleado INNER JOIN Retroalimentacion Ret ON Re.ID_Reporte = Ret.ID_Reporte INNER JOIN Tipo_Respuesta TR ON TR.ID_Tipo_Respuesta=Re.Calificacion_Empleado WHERE Em.dni = %s;"

    with connection.cursor() as cursor:
        cursor.execute(query,[dni])
        resultados=cursor.fetchall()

    context={
        "resultados":resultados
    }

    return render(request,'mostrarResultados.html',context)


def mostrarTablaApellidos(request,apellido):
    query="Select Em.Apellido_Empleado, Nombre_Empleado, Em.ID_Empleado from Empleado Em inner join Cuestionario_Empleado Cu on Cu.Id_Empleado=Em.Id_Empleado inner join Reporte Re on Re.Id_Cuestionario_Empleado=Cu.Id_Cuestionario_Empleado where Em.apellido_empleado=%s;"

    with connection.cursor() as cursor:
        cursor.execute(query,[apellido])
        empleados=cursor.fetchall()

    context={
        "empleados": empleados
    }

    return render(request,'mostrarTablaApellido.html',context)

def mostrarMenu(request):
    return render(request,'menuBase.html')

def baseEditar(request):
    with connection.cursor() as cursor:
        cursor.execute('SELECT ID_Tipo_Cuestionario, Tipo FROM Tipo_Cuestionario;')
        tiposCuestionario = cursor.fetchall()
    return render(request,'baseEditar.html',{"tiposCuestionario":tiposCuestionario})


def mostrarPreguntasEditar(request,id_tipo_cuestionario):
    with connection.cursor() as cursor:
        cursor.execute('SELECT ID_Tipo_Cuestionario, Tipo FROM Tipo_Cuestionario;')
        tiposCuestionario = cursor.fetchall()

    query=f"SELECT PC.ID_Pregunta, PC.Enunciado_Pregunta FROM Pregunta_Cuestionario PC INNER JOIN Cuestionario C ON PC.ID_Cuestionario = C.ID_Cuestionario WHERE C.ID_Tipo_Cuestionario = {id_tipo_cuestionario};"

    with connection.cursor() as cursor:
        cursor.execute(query)
        preguntas= cursor.fetchall()

    query=f"Select TE.Tipo as Estado_Envio from Cuestionario CU inner join Tipo_Estado TE on CU.Id_Estado_Envio=TE.Id_Tipo_Estado where Id_Tipo_Cuestionario={id_tipo_cuestionario};"

    with connection.cursor() as cursor:
        cursor.execute(query)
        estadoEnvio= cursor.fetchall()

        query=f"Select TE.Tipo as Estado_Aprobación from Cuestionario CU inner join Tipo_Estado TE on CU.Id_Estado_Aprobacion=TE.Id_Tipo_Estado where Id_Tipo_Cuestionario={id_tipo_cuestionario};"

    with connection.cursor() as cursor:
        cursor.execute(query)
        estadoAprobacion= cursor.fetchall()


    context = {
        "tiposCuestionario": tiposCuestionario,
        "preguntas": preguntas,
        "id_tipo_cuestionario": id_tipo_cuestionario,
        "estadoEnvio":estadoEnvio,
        "estadoAprobacion":estadoAprobacion
    }

    return render(request,'tablaPreguntas.html',context)


def agregarPregunta(request):
    id_tipo_cuestionario=request.POST['id_tipo_cuestionario']
    enunciado_pregunta=request.POST['enunciado_pregunta']

    query = "INSERT INTO Pregunta_Cuestionario(ID_Pregunta, ID_Cuestionario, Enunciado_Pregunta) VALUES (CASE WHEN (SELECT MAX(ID_Pregunta) FROM Pregunta_Cuestionario) IS NULL THEN 1 ELSE (SELECT (MAX(ID_Pregunta)) FROM Pregunta_Cuestionario) + 1 END, %s, %s);"
    
    with connection.cursor() as cursor:
            cursor.execute(query, [id_tipo_cuestionario, enunciado_pregunta])
            
    return redirect(f'/editar/{id_tipo_cuestionario}/')


def borrarPregunta(request,id_pregunta):
    id_tipo_cuestionario=request.POST['id_tipo_cuestionario']
    query = "DELETE FROM Pregunta_Cuestionario WHERE ID_Pregunta = %s;"
    
    with connection.cursor() as cursor:
            cursor.execute(query, [id_pregunta])
            
    return redirect(f'/editar/{id_tipo_cuestionario}/')


def enviarGerencia(request):
    id_tipo_cuestionario=request.POST['id_tipo_cuestionario']

    query=f"Update Cuestionario set ID_Estado_Envio=1, Fecha_Envio_Gerencia=Current_Date, Hora_Envio_Gerencia=Current_Time(0), ID_Estado_Aprobacion=5 where Id_Tipo_Cuestionario={id_tipo_cuestionario};"

    with connection.cursor() as cursor:
        cursor.execute(query)

    return redirect(f'/editar/{id_tipo_cuestionario}/') 

def crear(request):
    with connection.cursor() as cursor:
        cursor.execute('SELECT ID_Tipo_Cuestionario, Tipo FROM Tipo_Cuestionario;')
        tiposCuestionario = cursor.fetchall()

    return render(request,'crear.html',{"tiposCuestionario":tiposCuestionario})

def botonCrear(request):
    id_especialista=request.POST['id_especialista']
    id_tipo_cuestionario=request.POST['id_tipo_cuestionario']

    query=f"INSERT INTO Cuestionario(ID_Cuestionario,ID_Especialista_Relaciones_Laborales,ID_Tipo_Cuestionario,Fecha_Creacion,Hora_Creacion,ID_Estado_Envio,Fecha_Envio_Gerencia,Hora_Envio_Gerencia,ID_Gerente,ID_Estado_Aprobacion,Fecha_Revision,Hora_Revision) VALUES (CASE WHEN (SELECT MAX(ID_Cuestionario) FROM Cuestionario) IS NULL THEN 1 ELSE (SELECT MAX(ID_Cuestionario) FROM Cuestionario) + 1 END, {id_especialista},{id_tipo_cuestionario},CURRENT_DATE,CURRENT_TIME(0),2,NULL,NULL,20200001,2,NULL,NULL);"

    with connection.cursor() as cursor:
            cursor.execute(query)

    return redirect('/crear/')

def baseAprobar(request):
    with connection.cursor() as cursor:
        cursor.execute('SELECT ID_Tipo_Cuestionario, Tipo FROM Tipo_Cuestionario;')
        tiposCuestionario = cursor.fetchall()
    return render(request,'baseAprobar.html',{"tiposCuestionario":tiposCuestionario})


def mostrarPreguntasAprobar(request,id_tipo_cuestionario):
    with connection.cursor() as cursor:
        cursor.execute('SELECT ID_Tipo_Cuestionario, Tipo FROM Tipo_Cuestionario;')
        tiposCuestionario = cursor.fetchall()

    query=f"SELECT PC.ID_Pregunta, PC.Enunciado_Pregunta FROM Pregunta_Cuestionario PC INNER JOIN Cuestionario C ON PC.ID_Cuestionario = C.ID_Cuestionario WHERE C.ID_Tipo_Cuestionario = {id_tipo_cuestionario};"

    with connection.cursor() as cursor:
        cursor.execute(query)
        preguntas= cursor.fetchall()

    query=f"Select TE.Tipo as Estado_Envio from Cuestionario CU inner join Tipo_Estado TE on CU.Id_Estado_Envio=TE.Id_Tipo_Estado where Id_Tipo_Cuestionario={id_tipo_cuestionario};"

    with connection.cursor() as cursor:
        cursor.execute(query)
        estadoEnvio= cursor.fetchall()

    query=f"Select TE.Tipo as Estado_Aprobación from Cuestionario CU inner join Tipo_Estado TE on CU.Id_Estado_Aprobacion=TE.Id_Tipo_Estado where Id_Tipo_Cuestionario={id_tipo_cuestionario};"

    with connection.cursor() as cursor:
        cursor.execute(query)
        estadoAprobacion= cursor.fetchall()

    query=f"Select Id_Tipo_Estado,Tipo from Tipo_Estado;"

    with connection.cursor() as cursor:
        cursor.execute(query)
        tiposEstado= cursor.fetchall()



    context = {
        "tiposCuestionario": tiposCuestionario,
        "preguntas": preguntas,
        "id_tipo_cuestionario": id_tipo_cuestionario,
        "estadoEnvio":estadoEnvio,
        "estadoAprobacion":estadoAprobacion,
        "tiposEstado":tiposEstado
    }

    return render(request,'tablasAprobar.html',context)



def enviarAprobacion(request):
    id_tipo_estado=request.POST['id_tipo_estado']
    id_tipo_cuestionario=request.POST['id_tipo_cuestionario']
    query="Update Cuestionario set ID_Estado_Aprobacion=%s,Fecha_Revision=Current_Date,Hora_Revision=Current_Time(0) where Id_Tipo_Cuestionario=%s;"

    with connection.cursor() as cursor:
        cursor.execute(query,[id_tipo_estado,id_tipo_cuestionario])

    return redirect(f'/aprobar/{id_tipo_cuestionario}/')
    
#Edison

from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.db import connection
from django.utils.dateparse import parse_date
from django.urls import reverse

def MostrarFormulario(request):
    if 'show_form' in request.GET:
        with connection.cursor() as cursor:
            cursor.execute("SELECT ID_Departamento, Nombre_Departamento FROM Departamento")
            departamentos = cursor.fetchall()
        return render(request, 'Index2.html', {'departamentos': departamentos})
    else:
        return redirect('/MenuPrincipal')

def empleados_por_departamento(request, departamento_id):
    query = "SELECT ID_Empleado, Nombre_Empleado, Apellido_Empleado FROM Empleado WHERE ID_Departamento = %s"
    with connection.cursor() as cursor:
        cursor.execute(query, [departamento_id])
        empleados = cursor.fetchall()
    return JsonResponse(list(empleados), safe=False)


def Insert(request):
    if request.method == "POST":
        Estado = request.POST['Estado']
        Observacion = request.POST['Observacion']
        Fecha = request.POST['Fecha']
        Hora_entrada = request.POST['Hora_entrada']
        Hora_salida = request.POST['Hora_salida']
        ID_Empleado = request.POST['ID_Empleado']
        query = "INSERT INTO Asistencia (ID_Asistencia, Estado, Observacion, Fecha, Hora_entrada, Hora_salida, ID_Empleado) VALUES ((SELECT COALESCE(MAX(ID_Asistencia), 0) + 1 FROM Asistencia), %s, %s, %s, %s, %s, %s)"
        with connection.cursor() as cursor:
            cursor.execute(query, [Estado, Observacion, Fecha, Hora_entrada, Hora_salida, ID_Empleado])
        messages.success(request, 'Asistencia insertada')
        return redirect('/MenuPrincipal')
    return render(request, 'Index.html')

def solicitar_licencia(request):
    if request.method == 'POST':
        id_empleado = request.POST.get('ID_Empleado')
        motivo = request.POST.get('Motivo')
        fecha_inicio = request.POST.get('Fecha_inicio')
        fecha_fin = request.POST.get('Fecha_fin')
        id_supervisor = request.POST.get('ID_Supervisor')
        tipo = request.POST.get('Tipo')
        estado = 'Pendiente'

        if id_empleado and motivo and fecha_inicio and fecha_fin and id_supervisor and tipo:
            query = """
            INSERT INTO Licencia (ID_Licencia, Tipo, Estado, Fecha_inicio, Fecha_fin, ID_Empleado, ID_Supervisor)
            VALUES ((SELECT COALESCE(MAX(ID_Licencia), 0) + 1 FROM Licencia), %s, %s, %s, %s, %s, %s)
            """
            with connection.cursor() as cursor:
                cursor.execute(query, [tipo, estado, fecha_inicio, fecha_fin, id_empleado, id_supervisor])
            messages.success(request, 'La solicitud de licencia ha sido enviada correctamente.')
            return redirect('/MenuPrincipal')
        else:
            messages.error(request, 'Todos los campos son requeridos.')
    return render(request, 'solicitar_licencia.html')

def aprobar_rechazar_solicitudes(request):
    if request.method == 'POST':
        licencias = request.POST.getlist('licencias')
        accion = request.POST.get('accion')

        if accion == 'aprobar':
            estado_nuevo = 'Aprobado'
        elif accion == 'rechazar':
            estado_nuevo = 'Rechazado'
        else:
            messages.error(request, 'Acción no válida.')
            return redirect('aprobar_rechazar_solicitudes')

        query = '''
        UPDATE Licencia
        SET Estado = %s
        WHERE ID_Licencia = %s
        '''
        
        with connection.cursor() as cursor:
            for licencia_id in licencias:
                cursor.execute(query, [estado_nuevo, licencia_id])

        messages.success(request, 'Licencias actualizadas correctamente.')
        return redirect('aprobar_rechazar_solicitudes')
    else:
        query = '''
        SELECT l.ID_Licencia, l.Tipo, l.Estado, l.Fecha_inicio, l.Fecha_fin, e.Nombre_Empleado, e.Apellido_Empleado
        FROM Licencia l
        JOIN Empleado e ON l.ID_Empleado = e.ID_Empleado
        WHERE l.Estado = 'Pendiente'
        '''
        
        with connection.cursor() as cursor:
            cursor.execute(query)
            licencias = cursor.fetchall()
        
        if licencias:
            return render(request, 'aprobar_rechazar_solicitudes.html', {'licencias': licencias})
        else:
            return render(request, 'aprobar_rechazar_solicitudes.html')
        
def MenuPrincipal(request):
    return render(request, 'Menu2.html')

def generar_reporte_asistencia(request):
    if request.method == 'POST':
        departamento_id = request.POST.get('departamento')
        fecha_inicio = request.POST.get('fecha_inicio')
        fecha_fin = request.POST.get('fecha_fin')
        
        if departamento_id and fecha_inicio and fecha_fin:
            return redirect(reverse('mostrar_reporte', args=[departamento_id, fecha_inicio, fecha_fin]))
    
    with connection.cursor() as cursor:
        cursor.execute("SELECT ID_Departamento, Nombre_Departamento FROM Departamento")
        departamentos = cursor.fetchall()
    return render(request, 'Generar_reporte_asistencia.html', {'departamentos': departamentos})

def mostrar_reporte(request, departamento_id, fecha_inicio, fecha_fin):
    fecha_inicio = parse_date(fecha_inicio)
    fecha_fin = parse_date(fecha_fin)
    
    query = '''
    SELECT a.ID_Asistencia, a.Estado, a.Observacion, a.Fecha, a.Hora_entrada, a.Hora_salida, e.Nombre_Empleado, e.Apellido_Empleado
    FROM Asistencia a
    JOIN Empleado e ON a.ID_Empleado = e.ID_Empleado
    WHERE e.ID_Departamento = %s AND a.Fecha BETWEEN %s AND %s
    '''
    
    with connection.cursor() as cursor:
        cursor.execute(query, [departamento_id, fecha_inicio, fecha_fin])
        asistencias = cursor.fetchall()
    
    if asistencias:
        return render(request, 'Mostrar_reporte.html', {'asistencias': asistencias})
    else:
        messages.info(request, 'No se han registrado asistencias entre esas fechas.')
        return render(request, 'Mostrar_reporte.html')


def solicitar_permiso(request):
    if request.method == 'POST':
        tipo = request.POST.get('tipo')
        motivo = request.POST.get('motivo')
        duracion = request.POST.get('duracion')
        id_empleado = request.POST.get('id_empleado')
        id_supervisor = request.POST.get('id_supervisor')
        estado = 'Pendiente' 
        query = """
        INSERT INTO Permiso (ID_Permiso, Tipo, Motivo, Duracion, Estado, ID_Empleado, ID_Supervisor)
        VALUES ((SELECT COALESCE(MAX(ID_Permiso), 0) + 1 FROM Permiso), %s, %s, %s, %s, %s, %s)
        """
        
        with connection.cursor() as cursor:
            cursor.execute(query, [tipo, motivo, duracion, estado, id_empleado, id_supervisor])
        
        messages.success(request, 'Solicitud de permiso enviada correctamente.')
        return redirect('MenuPrincipal')
    return render(request, 'solicitar_permiso.html')

def aprobar_rechazar_permisos(request):
    if request.method == 'POST':
        permisos = request.POST.getlist('permisos')
        accion = request.POST.get('accion')

        if accion == 'aprobar':
            estado_nuevo = 'Aprobado'
        elif accion == 'rechazar':
            estado_nuevo = 'Rechazado'
        else:
            messages.error(request, 'Acción no válida.')
            return redirect('aprobar_rechazar_permisos')

        query = '''
        UPDATE Permiso
        SET Estado = %s
        WHERE ID_Permiso = %s
        '''
        
        with connection.cursor() as cursor:
            for permiso_id in permisos:
                cursor.execute(query, [estado_nuevo, permiso_id])

        messages.success(request, 'Permisos actualizados correctamente.')
        return redirect('aprobar_rechazar_permisos')
    else:
        query = '''
        SELECT p.ID_Permiso, p.Tipo, p.Estado, p.duracion, e.Nombre_Empleado, e.Apellido_Empleado
        FROM Permiso p
        JOIN Empleado e ON p.ID_Empleado = e.ID_Empleado
        WHERE p.Estado = 'Pendiente'
        '''
        
        with connection.cursor() as cursor:
            cursor.execute(query)
            permisos = cursor.fetchall()
        
        if permisos:
            return render(request, 'aprobar_rechazar_permisos.html', {'permisos': permisos})
        else:
            return render(request, 'aprobar_rechazar_permisos.html')
