from celery import shared_task
from django.utils import timezone
from .models import Alerta, Notificacion, Usuario, Clinica
from .motor import correr_motor
import os


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

            canales = set()
            if configuraciones.exists():
                for config in configuraciones:
                    canales.add(config.canal)
            else:
                canales.add('email')

            for canal in canales:
                notif = Notificacion.objects.create(
                    alerta=alerta,
                    usuario=usuario,
                    canal=canal,
                    destinatario=usuario.email,
                    estado='pendiente'
                )

                if canal == 'email':
                    resultado = enviar_email_task.delay(notif.id)

        return f"Notificaciones creadas para alerta {alerta_id}"
    except Alerta.DoesNotExist:
        return f"Alerta {alerta_id} no encontrada"


@shared_task
def enviar_email_task(notificacion_id):
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail

        notif = Notificacion.objects.get(id=notificacion_id)
        alerta = notif.alerta

        severidad_emoji = {
            'baja': '🟢',
            'media': '🟡',
            'alta': '🟠',
            'critica': '🔴'
        }

        emoji = severidad_emoji.get(alerta.severidad, '⚠️')

        mensaje = Mail(
            from_email=os.getenv('SENDGRID_FROM_EMAIL'),
            to_emails=notif.destinatario,
            subject=f"{emoji} Vigía - Alerta {alerta.severidad.upper()}: {alerta.tipo_kpi}",
            html_content=f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background-color: #9B8EC4; padding: 20px; border-radius: 12px 12px 0 0;">
                    <h1 style="color: white; margin: 0; font-size: 24px;">Vigía</h1>
                    <p style="color: #F5F3FA; margin: 5px 0 0 0; font-size: 14px;">Sistema de Alertas Inteligentes</p>
                </div>
                <div style="background-color: #ffffff; padding: 24px; border: 1px solid #C4B5E8; border-top: none;">
                    <div style="background-color: #F5F3FA; border-left: 4px solid #9B8EC4; padding: 12px 16px; border-radius: 4px; margin-bottom: 20px;">
                        <p style="margin: 0; font-size: 12px; color: #8B89A0; text-transform: uppercase; letter-spacing: 1px;">Severidad</p>
                        <p style="margin: 4px 0 0 0; font-size: 18px; font-weight: bold; color: #2D2B3D;">{emoji} {alerta.severidad.upper()}</p>
                    </div>
                    <h2 style="color: #2D2B3D; font-size: 18px; margin: 0 0 12px 0;">{alerta.tipo_kpi.replace('_', ' ').title()}</h2>
                    <p style="color: #2D2B3D; font-size: 15px; line-height: 1.6;">{alerta.mensaje}</p>
                    <div style="background-color: #F5F3FA; border-radius: 8px; padding: 16px; margin: 20px 0;">
                        <p style="margin: 0 0 8px 0; font-size: 12px; color: #8B89A0; text-transform: uppercase; letter-spacing: 1px;">💡 Recomendación</p>
                        <p style="margin: 0; color: #2D2B3D; font-size: 14px; line-height: 1.6;">{alerta.recomendacion}</p>
                    </div>
                    <div style="display: flex; gap: 16px; margin-top: 8px;">
                        <div style="flex: 1; text-align: center; background-color: #F5F3FA; padding: 12px; border-radius: 8px;">
                            <p style="margin: 0; font-size: 11px; color: #8B89A0;">Valor Detectado</p>
                            <p style="margin: 4px 0 0 0; font-size: 20px; font-weight: bold; color: #E8A0C4;">{alerta.valor_detectado}</p>
                        </div>
                        <div style="flex: 1; text-align: center; background-color: #F5F3FA; padding: 12px; border-radius: 8px;">
                            <p style="margin: 0; font-size: 11px; color: #8B89A0;">Valor Esperado</p>
                            <p style="margin: 4px 0 0 0; font-size: 20px; font-weight: bold; color: #A0C4B5;">{alerta.valor_esperado}</p>
                        </div>
                        <div style="flex: 1; text-align: center; background-color: #F5F3FA; padding: 12px; border-radius: 8px;">
                            <p style="margin: 0; font-size: 11px; color: #8B89A0;">Desviación</p>
                            <p style="margin: 4px 0 0 0; font-size: 20px; font-weight: bold; color: #9B8EC4;">{alerta.desviacion}%</p>
                        </div>
                    </div>
                </div>
                <div style="background-color: #F5F3FA; padding: 12px 20px; border-radius: 0 0 12px 12px; text-align: center;">
                    <p style="margin: 0; font-size: 12px; color: #8B89A0;">Vigía — Sistema de Alertas Inteligentes para Clínicas</p>
                </div>
            </div>
            """
        )

        sg = SendGridAPIClient(os.getenv('SENDGRID_API_KEY'))
        response = sg.send(mensaje)

        notif.estado = 'enviada'
        notif.enviada_en = timezone.now()
        notif.save()

        return f"Email enviado a {notif.destinatario} - Status: {response.status_code}"

    except Exception as e:
        try:
            notif = Notificacion.objects.get(id=notificacion_id)
            notif.estado = 'fallida'
            notif.save()
        except:
            pass
        return f"Error enviando email: {e}"


@shared_task
def ejecutar_motor_todas_clinicas():
    clinicas = Clinica.objects.filter(activa=True)
    for clinica in clinicas:
        ejecutar_motor_task.delay(clinica.id)
    return f"Motor ejecutado para {clinicas.count()} clínicas"

@shared_task
def generar_datos_falsos_task():
    from .generador import generar_datos_todas_clinicas
    resultado = generar_datos_todas_clinicas()
    return resultado

@shared_task
def generar_datos_clinica_task(clinica_id):
    from .generador import generar_datos_clinica
    generar_datos_clinica(clinica_id)
    return f"Datos generados para clínica {clinica_id}"