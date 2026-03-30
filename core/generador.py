import random
import statistics
from django.utils import timezone
from datetime import timedelta
from .models import Clinica, Medico, Paciente, Cita, RegistroKPI


def generar_cita_aleatoria(clinica):
    medicos = Medico.objects.filter(clinica=clinica, activo=True)
    pacientes = Paciente.objects.filter(clinica=clinica)

    if not medicos.exists() or not pacientes.exists():
        return None

    medico = random.choice(list(medicos))
    paciente = random.choice(list(pacientes))

    estado = random.choices(
        ['completada', 'cancelada', 'no_show', 'reagendada'],
        weights=[65, 20, 10, 5]
    )[0]

    ingreso = round(random.uniform(20, 150), 2) if estado == 'completada' else 0
    ahora = timezone.now()
    fecha = ahora + timedelta(hours=random.randint(-3, 0))

    return Cita.objects.create(
        clinica=clinica,
        medico=medico,
        paciente=paciente,
        fecha_hora_agendada=fecha,
        fecha_hora_real=fecha if estado == 'completada' else None,
        estado=estado,
        ingreso_generado=ingreso,
    )


def generar_kpis_variados(clinica_id):
    base = {
        'tasa_cancelacion':  (5, 25),
        'tasa_noshow':       (2, 15),
        'ingresos_dia':      (200, 800),
        'ticket_promedio':   (30, 120),
        'pacientes_nuevos':  (10, 40),
        'retencion_90':      (60, 95),
        'nps':               (20, 80),
        'citas_reagendadas': (2, 15),
    }

    for tipo, (minv, maxv) in base.items():
        recientes = list(RegistroKPI.objects.filter(
            clinica_id=clinica_id,
            tipo=tipo,
        ).order_by('-fecha_hora').values_list('valor', flat=True)[:20])

        if len(recientes) >= 5:
            promedio = statistics.mean(recientes)
            rand = random.random()

            if rand < 0.50:
                # Normal — sin anomalía
                valor = round(promedio * random.uniform(0.85, 1.15), 2)
            elif rand < 0.65:
                # Baja — 20-40% desviación
                if random.random() < 0.5:
                    valor = round(promedio * random.uniform(0.60, 0.80), 2)
                else:
                    valor = round(promedio * random.uniform(1.20, 1.40), 2)
            elif rand < 0.78:
                # Media — 40-60% desviación
                if random.random() < 0.5:
                    valor = round(promedio * random.uniform(0.40, 0.60), 2)
                else:
                    valor = round(promedio * random.uniform(1.40, 1.60), 2)
            elif rand < 0.89:
                # Alta — 60-80% desviación
                if random.random() < 0.5:
                    valor = round(promedio * random.uniform(0.20, 0.40), 2)
                else:
                    valor = round(promedio * random.uniform(1.60, 1.80), 2)
            else:
                # Crítica — >80% desviación
                if random.random() < 0.5:
                    valor = round(promedio * random.uniform(0.05, 0.15), 2)
                else:
                    valor = round(promedio * random.uniform(1.85, 2.50), 2)

            valor = max(0.1, valor)
        else:
            valor = round(random.uniform(minv, maxv), 2)

        RegistroKPI.objects.create(
            clinica_id=clinica_id,
            tipo=tipo,
            valor=valor,
            periodo='dia'
        )


def generar_datos_clinica(clinica_id):
    try:
        clinica = Clinica.objects.get(id=clinica_id)
    except Clinica.DoesNotExist:
        return

    for _ in range(random.randint(3, 8)):
        generar_cita_aleatoria(clinica)

    generar_kpis_variados(clinica_id)


def generar_datos_todas_clinicas():
    clinicas = Clinica.objects.filter(activa=True)
    for clinica in clinicas:
        generar_datos_clinica(clinica.id)
    return f"Datos generados para {clinicas.count()} clínicas"