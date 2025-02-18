import xlsxwriter
import datetime
from evaluacion.models import Evaluacion

def generate_formaciones_report(periodo, file_path='formaciones_report.xlsx'):
    # Create an Excel workbook and add a worksheet
    workbook = xlsxwriter.Workbook(file_path)
    worksheet = workbook.add_worksheet()

    # Define the headers for the report
    headers = [
        "#", "Ficha", "Nombre del Participante", "Cargo", "Gerencia", "Tipo de Personal", 
        "Formacion Sugerida", "Formacion Especifica", "Ente Didactico", 
        "Instructor", "Dur Hrs", "Año", "Fecha Planificada", 
        "Fecha Real", "Prioridad"
    ]
    
    # Write headers to the worksheet
    for col_num, header in enumerate(headers):
        worksheet.write(0, col_num, header)

    # Fetch data from the database
    evaluaciones = Evaluacion.objects.filter(periodo=periodo).order_by(
        'evaluado__user__first_name'
    )
    
    # Write data to the worksheet
    index = 1
    for evaluacion in evaluaciones:
        ficha = evaluacion.evaluado.ficha
        participante = ', '.join(evaluacion.evaluado.user.first_name.rsplit(' ', 2)[::-1]) # TODO: Fix
        cargo = evaluacion.evaluado.cargo.nombre
        gerencia = evaluacion.evaluado.gerencia.nombre
        tipo_personal = evaluacion.evaluado.tipo_personal.nombre
        
        for formacion in evaluacion.formaciones.filter(activo=True):            
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
                index, ficha, participante, cargo, gerencia, tipo_personal,
                formacion_sugerida, formacion_especifica, ente_didactico,
                instructor, duracion_horas, ano, fecha_planificada,
                fecha_real, prioridad
            ]
            
            for col_num, cell_data in enumerate(data):
                worksheet.write(index, col_num, cell_data)
            
            index += 1

    # Close the workbook
    workbook.close()

