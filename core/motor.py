import statistics
from django.utils import timezone
from datetime import timedelta
from .models import Cita, RegistroKPI, Alerta, Clinica

def calcular_tasa_cancelacion(clinica_id):
    hoy = timezone.now().date()
    citas_hoy = Cita.objects.filter(clinica_id=clinica_id, fecha_hora_agendada__date=hoy)
    total = citas_hoy.count()
    if total == 0:
        return 0
    canceladas = citas_hoy.filter(estado='cancelada').count()
    return round((canceladas / total) * 100, 2)

def calcular_tasa_noshow(clinica_id):
    hoy = timezone.now().date()
    citas_hoy = Cita.objects.filter(clinica_id=clinica_id, fecha_hora_agendada__date=hoy)
    total = citas_hoy.count()
    if total == 0:
        return 0
    noshow = citas_hoy.filter(estado='no_show').count()
    return round((noshow / total) * 100, 2)

def calcular_ingresos_dia(clinica_id):
    hoy = timezone.now().date()
    citas_hoy = Cita.objects.filter(
        clinica_id=clinica_id,
        fecha_hora_agendada__date=hoy,
        estado='completada'
    )
    total = sum(c.ingreso_generado for c in citas_hoy)
    return float(total)

def calcular_ocupacion_medico(clinica_id, medico_id, slots_disponibles=8):
    hoy = timezone.now().date()
    citas = Cita.objects.filter(
        clinica_id=clinica_id,
        medico_id=medico_id,
        fecha_hora_agendada__date=hoy
    ).exclude(estado='cancelada')
    ocupadas = citas.count()
    return round((ocupadas / slots_disponibles) * 100, 2)

def obtener_historico(clinica_id, tipo_kpi, dias=30):
    desde = timezone.now() - timedelta(days=dias)
    registros = RegistroKPI.objects.filter(
        clinica_id=clinica_id,
        tipo=tipo_kpi,
        fecha_hora__gte=desde
    ).values_list('valor', flat=True)
    return list(registros)

def detectar_anomalia(valor_actual, historico, umbral=20):
    if len(historico) < 5:
        return False, 0, 0
    promedio = statistics.mean(historico)
    if promedio == 0:
        return False, 0, 0
    desviacion = abs((valor_actual - promedio) / promedio) * 100
    es_anomalia = desviacion >= umbral
    return es_anomalia, round(promedio, 2), round(desviacion, 2)

def determinar_severidad(desviacion):
    if desviacion >= 60:
        return 'critica'
    elif desviacion >= 40:
        return 'alta'
    elif desviacion >= 20:
        return 'media'
    return 'baja'

def generar_mensaje(tipo_kpi, valor_actual, valor_esperado, desviacion, clinica_nombre):
    mensajes = {
        'tasa_cancelacion': f"La tasa de cancelación de {clinica_nombre} es {valor_actual}%, cuando lo normal es {valor_esperado}%. Desviación de {desviacion}%.",
        'tasa_noshow': f"La tasa de no-show de {clinica_nombre} es {valor_actual}%, cuando lo normal es {valor_esperado}%. Desviación de {desviacion}%.",
        'ingresos_dia': f"Los ingresos del día en {clinica_nombre} son ${valor_actual}, cuando lo normal es ${valor_esperado}. Desviación de {desviacion}%.",
        'ocupacion_agenda': f"La ocupación de agenda en {clinica_nombre} es {valor_actual}%, cuando lo normal es {valor_esperado}%. Desviación de {desviacion}%.",
    }
    return mensajes.get(tipo_kpi, f"El KPI {tipo_kpi} tiene una desviación de {desviacion}% respecto al promedio histórico.")

def correr_motor(clinica_id):
    try:
        clinica = Clinica.objects.get(id=clinica_id)
    except Clinica.DoesNotExist:
        return

    kpis_a_evaluar = [
        ('tasa_cancelacion', calcular_tasa_cancelacion(clinica_id)),
        ('tasa_noshow', calcular_tasa_noshow(clinica_id)),
        ('ingresos_dia', calcular_ingresos_dia(clinica_id)),
    ]

    for tipo_kpi, valor_actual in kpis_a_evaluar:
        RegistroKPI.objects.create(
            clinica_id=clinica_id,
            tipo=tipo_kpi,
            valor=valor_actual,
            periodo='dia'
        )

        historico = obtener_historico(clinica_id, tipo_kpi)
        es_anomalia, valor_esperado, desviacion = detectar_anomalia(valor_actual, historico)

        if es_anomalia:
            severidad = determinar_severidad(desviacion)
            mensaje = generar_mensaje(tipo_kpi, valor_actual, valor_esperado, desviacion, clinica.nombre)

            Alerta.objects.create(
                clinica_id=clinica_id,
                tipo_kpi=tipo_kpi,
                valor_detectado=valor_actual,
                valor_esperado=valor_esperado,
                desviacion=desviacion,
                severidad=severidad,
                mensaje=mensaje,
                recomendacion='Revisar con el equipo administrativo.',
                estado='activa'
            )