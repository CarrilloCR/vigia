from celery import shared_task
from django.utils import timezone
from .models import Alerta, Notificacion, Usuario, Clinica
from .motor import correr_motor


@shared_task
def ejecutar_motor_task(clinica_id):
    correr_motor(clinica_id)
    return f"Motor ejecutado para clínica {clinica_id}"


@shared_task
def enviar_notificaciones_task(alerta_id):
    try:
        alerta = Alerta.objects.get(id=alerta_id)
        clinica = alerta.clinica
        usuarios = Usuario.objects.filter(clinica=clinica)

        for usuario in usuarios:
            configuraciones = clinica.configuraciones.filter(
                tipo_kpi=alerta.tipo_kpi,
                activa=True
            )
            for config in configuraciones:
                Notificacion.objects.create(
                    alerta=alerta,
                    usuario=usuario,
                    canal=config.canal,
                    destinatario=usuario.email,
                    estado='pendiente'
                )

        return f"Notificaciones creadas para alerta {alerta_id}"
    except Alerta.DoesNotExist:
        return f"Alerta {alerta_id} no encontrada"


@shared_task
def ejecutar_motor_todas_clinicas():
    clinicas = Clinica.objects.filter(activa=True)
    for clinica in clinicas:
        ejecutar_motor_task.delay(clinica.id)
    return f"Motor ejecutado para {clinicas.count()} clínicas"