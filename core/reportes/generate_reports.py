
import openpyxl
import datetime
from evaluacion.models import Evaluacion
from io import BytesIO
from django.http import HttpResponse

def create_dnf(periodo, file_path='core/reportes/bases/plan-anual-formacion.xlsx'):
    # Load the Excel workbook
    workbook = openpyxl.load_workbook(file_path)

    # Access the first worksheet
    worksheet = workbook.active

    # Write data to the worksheet
    # Fetch data from the database
    evaluaciones = Evaluacion.objects.filter(periodo=periodo).order_by(
        'evaluado__user__first_name'
    )
    
    # Write data to the worksheet
    row = 10
    for evaluacion in evaluaciones:
        for j,formacion in enumerate(evaluacion.formaciones.filter(activo=True), start=1):            
            formacion_sugerida = formacion.necesidad_formacion.upper()
            formacion_especifica = ''
            ente_didactico = ''
            instructor = ''
            duracion_horas = ''
            ano = datetime.datetime.now().year
            fecha_planificada = ''
            fecha_real = ''
            prioridad = formacion.prioridad

            # Write data to the worksheet
            data = [
                j,evaluacion.evaluado.ficha, evaluacion.evaluado.user.get_full_name(), 
                evaluacion.evaluado.cargo.nombre.upper(), evaluacion.evaluado.gerencia.nombre.upper(), 
                evaluacion.evaluado.tipo_personal.nombre.upper(),
                formacion_sugerida, formacion_especifica, ente_didactico,
                instructor, duracion_horas, ano, fecha_planificada,
                fecha_real, prioridad, '', '', '',
                'X' if formacion.competencias.filter(nombre__iexact='CAPACIDADES OPERATIVAS').exists() else '',
                'X' if formacion.competencias.filter(nombre__iexact='CAPACIDADES ANALÍTICAS Y DE SÍNTESIS').exists() else '',
                'X' if formacion.competencias.filter(nombre__iexact='Capacidades de Negociación y Relación').exists() else '',
                'X' if formacion.competencias.filter(nombre__iexact='Capacidades de Gestión').exists() else '',
                'X' if formacion.competencias.filter(nombre__iexact='Desarrollo').exists() else '',
                'X' if formacion.competencias.filter(nombre__iexact='Liderazgo').exists() else '',
                'X' if formacion.competencias.filter(nombre__iexact='Adaptabilidad').exists() else '',
                'X' if formacion.competencias.filter(nombre__iexact='Realización de Tareas').exists() else '',
                'X' if formacion.competencias.filter(nombre__iexact='Producción').exists() else '',
                'X' if formacion.competencias.filter(nombre__iexact='Desarrollo de los demás').exists() else '',
                'X' if formacion.competencias.filter(nombre__iexact='Desarrollo Personal').exists() else '',
                'X' if formacion.competencias.filter(nombre__iexact='Comunicación').exists() else '',
            ]
            
            for col_num, cell_data in enumerate(data, start=1):
                worksheet.cell(row=row, column=col_num, value=cell_data)
            
            row += 1
    
    # Save the workbook to a file
    output = BytesIO()
    workbook.save(output)
    output.seek(0)

    # add the picture in static/img/LogoDeIndesca.svg in A3
    img = openpyxl.drawing.image.Image('static/img/LogoDeIndesca.png')
    img.anchor = 'A3'
    worksheet.add_image(img)
    
    # Return the report as a file response
    return HttpResponse(
        output,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

