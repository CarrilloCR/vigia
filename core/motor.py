import statistics
import anthropic
import os
from django.utils import timezone
from datetime import timedelta
from .models import Cita, RegistroKPI, Alerta, Clinica, Encuesta
from .deteccion import detectar_anomalia_ensemble

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

def calcular_ticket_promedio(clinica_id):
    hoy = timezone.now().date()
    citas_hoy = Cita.objects.filter(
        clinica_id=clinica_id,
        fecha_hora_agendada__date=hoy,
        estado='completada'
    )
    total = citas_hoy.count()
    if total == 0:
        return 0
    ingresos = sum(c.ingreso_generado for c in citas_hoy)
    return round(float(ingresos) / total, 2)

def calcular_ocupacion_medico(clinica_id, medico_id, slots_disponibles=8):
    hoy = timezone.now().date()
    citas = Cita.objects.filter(
        clinica_id=clinica_id,
        medico_id=medico_id,
        fecha_hora_agendada__date=hoy
    ).exclude(estado='cancelada')
    ocupadas = citas.count()
    return round((ocupadas / slots_disponibles) * 100, 2)

def calcular_pacientes_nuevos(clinica_id):
    hoy = timezone.now().date()
    citas_hoy = Cita.objects.filter(
        clinica_id=clinica_id,
        fecha_hora_agendada__date=hoy,
        estado='completada'
    )
    total = citas_hoy.count()
    if total == 0:
        return 0
    nuevos = citas_hoy.filter(paciente__primera_visita=hoy).count()
    return round((nuevos / total) * 100, 2)

def calcular_retencion_90(clinica_id):
    hoy = timezone.now().date()
    hace_90 = hoy - timedelta(days=90)
    pacientes_hace_90 = Cita.objects.filter(
        clinica_id=clinica_id,
        fecha_hora_agendada__date=hace_90,
        estado='completada'
    ).values_list('paciente_id', flat=True)
    total = len(pacientes_hace_90)
    if total == 0:
        return 0
    regresaron = Cita.objects.filter(
        clinica_id=clinica_id,
        paciente_id__in=pacientes_hace_90,
        fecha_hora_agendada__date__gt=hace_90,
        estado='completada'
    ).values('paciente_id').distinct().count()
    return round((regresaron / total) * 100, 2)

def calcular_nps(clinica_id):
    desde = timezone.now() - timedelta(days=30)
    encuestas = Encuesta.objects.filter(
        cita__clinica_id=clinica_id,
        respondida_en__gte=desde
    )
    total = encuestas.count()
    if total == 0:
        return 0
    promotores = encuestas.filter(puntuacion__gte=9).count()
    detractores = encuestas.filter(puntuacion__lte=6).count()
    return round(((promotores - detractores) / total) * 100, 2)

def calcular_citas_reagendadas(clinica_id):
    hoy = timezone.now().date()
    citas_hoy = Cita.objects.filter(clinica_id=clinica_id, fecha_hora_agendada__date=hoy)
    total = citas_hoy.count()
    if total == 0:
        return 0
    reagendadas = citas_hoy.filter(estado='reagendada').count()
    return round((reagendadas / total) * 100, 2)

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
    if desviacion >= 80:
        return 'critica'
    elif desviacion >= 60:
        return 'alta'
    elif desviacion >= 35:
        return 'media'
    return 'baja'

def generar_mensaje(tipo_kpi, valor_actual, valor_esperado, desviacion, clinica_nombre, sede_nombre=None):
    sede_str = f" · Sede {sede_nombre}" if sede_nombre else ""
    mensajes = {
        'tasa_cancelacion': f"La tasa de cancelación de {clinica_nombre}{sede_str} es {valor_actual}%, cuando lo normal es {valor_esperado}%. Desviación de {desviacion}%.",
        'tasa_noshow': f"La tasa de no-show de {clinica_nombre}{sede_str} es {valor_actual}%, cuando lo normal es {valor_esperado}%. Desviación de {desviacion}%.",
        'ingresos_dia': f"Los ingresos del día en {clinica_nombre}{sede_str} son ${valor_actual}, cuando lo normal es ${valor_esperado}. Desviación de {desviacion}%.",
        'ticket_promedio': f"El ticket promedio en {clinica_nombre}{sede_str} es ${valor_actual}, cuando lo normal es ${valor_esperado}. Desviación de {desviacion}%.",
        'ocupacion_agenda': f"La ocupación de agenda en {clinica_nombre}{sede_str} es {valor_actual}%, cuando lo normal es {valor_esperado}%. Desviación de {desviacion}%.",
        'pacientes_nuevos': f"El porcentaje de pacientes nuevos en {clinica_nombre}{sede_str} es {valor_actual}%, cuando lo normal es {valor_esperado}%. Desviación de {desviacion}%.",
        'retencion_90': f"La retención a 90 días en {clinica_nombre}{sede_str} es {valor_actual}%, cuando lo normal es {valor_esperado}%. Desviación de {desviacion}%.",
        'nps': f"El NPS de {clinica_nombre}{sede_str} es {valor_actual}, cuando lo normal es {valor_esperado}. Desviación de {desviacion}%.",
        'citas_reagendadas': f"Las citas reagendadas en {clinica_nombre}{sede_str} son {valor_actual}%, cuando lo normal es {valor_esperado}%. Desviación de {desviacion}%.",
    }
    return mensajes.get(tipo_kpi, f"El KPI {tipo_kpi}{sede_str} tiene una desviación de {desviacion}% respecto al promedio histórico.")

def generar_recomendacion_ia(tipo_kpi, valor_actual, valor_esperado, desviacion, clinica_nombre, severidad):
    try:
        from dotenv import load_dotenv
        from pathlib import Path
        env_path = Path(__file__).resolve().parent.parent / '.env'
        load_dotenv(env_path)

        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            return 'Revisar con el equipo administrativo para identificar la causa y tomar acción correctiva.'

        client = anthropic.Anthropic(api_key=api_key)
        prompt = f"""Eres un sistema de alertas inteligentes para clínicas médicas llamado Vigía.

Se detectó una anomalía en la clínica "{clinica_nombre}":
- KPI afectado: {tipo_kpi}
- Valor actual: {valor_actual}
- Valor esperado (promedio histórico): {valor_esperado}
- Desviación: {desviacion}%
- Severidad: {severidad}

En máximo 2 oraciones cortas y directas:
1. Explica qué puede estar causando esta anomalía
2. Da una recomendación concreta de qué acción tomar

Responde en español, de forma profesional pero simple. Sin bullets ni formato especial."""

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text
    except Exception as e:
        print(f"Error con Claude API: {e}")
        return 'Revisar con el equipo administrativo para identificar la causa y tomar acción correctiva.'

def correr_motor(clinica_id, enviar_notif=False):
    try:
        clinica = Clinica.objects.get(id=clinica_id)
    except Clinica.DoesNotExist:
        return

    kpis = ['tasa_cancelacion', 'tasa_noshow', 'ingresos_dia', 'ticket_promedio',
            'pacientes_nuevos', 'retencion_90', 'nps', 'citas_reagendadas']

    alertas_creadas = []

    for tipo_kpi in kpis:
        ultimo = RegistroKPI.objects.filter(
            clinica_id=clinica_id,
            tipo=tipo_kpi
        ).order_by('-fecha_hora').first()

        if not ultimo:
            continue

        valor_actual = ultimo.valor
        sede = ultimo.sede  # propagate sede from the KPI record to the alert
        sede_nombre = sede.nombre if sede else None

        # Historical values scoped to same sede (for statistical + PyOD)
        historico_qs_base = RegistroKPI.objects.filter(
            clinica_id=clinica_id,
            tipo=tipo_kpi,
            sede=sede,
        )
        historico = list(historico_qs_base.order_by('-fecha_hora')[1:60].values_list('valor', flat=True))

        # Historical values with dates (for Prophet) — exclude the latest record
        historico_fechas_qs = historico_qs_base.exclude(pk=ultimo.pk).order_by('fecha_hora').values_list('fecha_hora', 'valor')
        historico_con_fechas = list(historico_fechas_qs) if historico_fechas_qs.count() >= 14 else None

        es_anomalia, valor_esperado, desviacion, metodo, detalle = detectar_anomalia_ensemble(
            valor_actual, historico, historico_con_fechas
        )

        if es_anomalia:
            severidad = determinar_severidad(desviacion)
            mensaje = generar_mensaje(tipo_kpi, valor_actual, valor_esperado, desviacion, clinica.nombre, sede_nombre)

            if severidad in ['alta', 'critica'] and clinica.claude_activo:
                recomendacion = generar_recomendacion_ia(tipo_kpi, valor_actual, valor_esperado, desviacion, clinica.nombre, severidad)
            else:
                recomendacion = 'Monitorear la situación y revisar si el patrón continúa en las próximas horas.'

            alerta = Alerta.objects.create(
                clinica_id=clinica_id,
                sede=sede,
                tipo_kpi=tipo_kpi,
                valor_detectado=valor_actual,
                valor_esperado=valor_esperado,
                desviacion=desviacion,
                severidad=severidad,
                mensaje=mensaje,
                recomendacion=recomendacion,
                metodo_deteccion=metodo,
                detalle_deteccion=detalle,
                estado='activa'
            )
            alertas_creadas.append(alerta.id)

    # Registrar timestamp del último motor run
    from django.utils import timezone as tz
    clinica.ultimo_motor_en = tz.now()
    clinica.save(update_fields=['ultimo_motor_en'])

    # Enviar UN solo email con todas las alertas del ciclo
    if enviar_notif and alertas_creadas:
        try:
            from .tasks import enviar_notificaciones_agrupadas_task
            enviar_notificaciones_agrupadas_task.delay(clinica_id, alertas_creadas)
        except Exception as e:
            print(f"Error disparando notificaciones: {e}")