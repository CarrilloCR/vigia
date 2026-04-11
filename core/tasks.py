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
def enviar_notificaciones_agrupadas_task(clinica_id, alerta_ids):
    """Envía un solo email con todas las alertas generadas en el análisis."""
    try:
        clinica = Clinica.objects.get(id=clinica_id)
        alertas = Alerta.objects.filter(id__in=alerta_ids)

        if not alertas.exists():
            return "Sin alertas para notificar"

        emails_destino = set()

        # Emails de usuarios de la clínica
        usuarios = Usuario.objects.filter(clinica=clinica)
        for u in usuarios:
            if u.email:
                emails_destino.add(u.email)

        # Emails adicionales del modelo EmailNotificacion
        try:
            from .models import EmailNotificacion
            emails_extra = EmailNotificacion.objects.filter(clinica=clinica, activo=True)
            for e in emails_extra:
                emails_destino.add(e.email)
        except Exception:
            pass

        if not emails_destino:
            return "Sin emails destino configurados"

        # Una sola notificación por email
        for email in emails_destino:
            notif = Notificacion.objects.create(
                alerta=alertas.first(),
                usuario=usuarios.first() if usuarios.exists() else None,
                canal='email',
                destinatario=email,
                estado='pendiente'
            )
            enviar_email_agrupado_task.delay(notif.id, list(alerta_ids), email)

        return f"Notificación agrupada enviada a {len(emails_destino)} destinatarios"

    except Exception as e:
        return f"Error: {e}"


@shared_task
def enviar_email_agrupado_task(notificacion_id, alerta_ids, destinatario):
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail
        from dotenv import load_dotenv
        from pathlib import Path
        env_path = Path(__file__).resolve().parent.parent / '.env'
        load_dotenv(env_path)

        alertas = Alerta.objects.filter(id__in=alerta_ids).order_by('-severidad')

        severidad_color = {
            'baja':    '#A0C4B5',
            'media':   '#C4B5E8',
            'alta':    '#9B8EC4',
            'critica': '#E8A0C4',
        }
        severidad_emoji = {
            'baja': '🟢', 'media': '🟡', 'alta': '🟠', 'critica': '🔴'
        }

        criticas = alertas.filter(severidad='critica').count()
        altas = alertas.filter(severidad='alta').count()
        total = alertas.count()

        if criticas > 0:
            subject_emoji = '🔴'
            subject_sev = 'CRÍTICO'
        elif altas > 0:
            subject_emoji = '🟠'
            subject_sev = 'ALTO'
        else:
            subject_emoji = '🟡'
            subject_sev = 'MEDIO'

        alertas_html = ''
        for alerta in alertas:
            color = severidad_color.get(alerta.severidad, '#9B8EC4')
            emoji = severidad_emoji.get(alerta.severidad, '⚠️')
            alertas_html += f"""
            <div style="border-left: 4px solid {color}; padding: 16px; margin-bottom: 16px; background: #F9F7FF; border-radius: 0 8px 8px 0;">
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                    <span style="font-size: 16px;">{emoji}</span>
                    <span style="font-size: 11px; font-weight: bold; color: {color}; text-transform: uppercase; letter-spacing: 1px;">{alerta.severidad}</span>
                    <span style="font-size: 14px; font-weight: bold; color: #2D2B3D; margin-left: 4px;">{alerta.tipo_kpi.replace('_', ' ').title()}</span>
                </div>
                <p style="margin: 0 0 8px 0; color: #2D2B3D; font-size: 14px; line-height: 1.5;">{alerta.mensaje}</p>
                <div style="display: flex; gap: 12px; margin-bottom: 8px;">
                    <span style="font-size: 12px; color: #8B89A0;">Valor: <strong style="color: #E8A0C4;">{alerta.valor_detectado}</strong></span>
                    <span style="font-size: 12px; color: #8B89A0;">Esperado: <strong style="color: #A0C4B5;">{alerta.valor_esperado}</strong></span>
                    <span style="font-size: 12px; color: #8B89A0;">Desviación: <strong style="color: #9B8EC4;">{alerta.desviacion}%</strong></span>
                </div>
                {f'<p style="margin: 8px 0 0 0; font-size: 13px; color: #6B6880; font-style: italic;">💡 {alerta.recomendacion}</p>' if alerta.recomendacion else ''}
            </div>
            """

        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 640px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #9B8EC4, #7C6FBF); padding: 24px; border-radius: 12px 12px 0 0;">
                <h1 style="color: white; margin: 0; font-size: 26px;">Vigía</h1>
                <p style="color: #F5F3FA; margin: 4px 0 0 0; font-size: 13px;">Sistema de Alertas Inteligentes para Clínicas</p>
            </div>
            <div style="background: white; padding: 24px; border: 1px solid #E0D9F5; border-top: none;">
                <div style="background: #F5F3FA; border-radius: 10px; padding: 16px; margin-bottom: 24px; text-align: center;">
                    <p style="margin: 0; font-size: 13px; color: #8B89A0;">Resumen del análisis</p>
                    <div style="display: flex; justify-content: center; gap: 24px; margin-top: 12px;">
                        <div>
                            <p style="margin: 0; font-size: 28px; font-weight: bold; color: #9B8EC4;">{total}</p>
                            <p style="margin: 0; font-size: 11px; color: #8B89A0;">Total alertas</p>
                        </div>
                        <div>
                            <p style="margin: 0; font-size: 28px; font-weight: bold; color: #E8A0C4;">{criticas}</p>
                            <p style="margin: 0; font-size: 11px; color: #8B89A0;">Críticas</p>
                        </div>
                        <div>
                            <p style="margin: 0; font-size: 28px; font-weight: bold; color: #9B8EC4;">{altas}</p>
                            <p style="margin: 0; font-size: 11px; color: #8B89A0;">Altas</p>
                        </div>
                    </div>
                </div>
                <h2 style="color: #2D2B3D; font-size: 16px; margin: 0 0 16px 0;">Detalle de alertas</h2>
                {alertas_html}
            </div>
            <div style="background: #F5F3FA; padding: 14px 20px; border-radius: 0 0 12px 12px; text-align: center;">
                <p style="margin: 0; font-size: 11px; color: #8B89A0;">
                    Vigía — {timezone.now().strftime('%d/%m/%Y %H:%M')} · Este email fue generado automáticamente
                </p>
            </div>
        </div>
        """

        mensaje = Mail(
            from_email=os.getenv('SENDGRID_FROM_EMAIL'),
            to_emails=destinatario,
            subject=f"{subject_emoji} Vigía — {total} alertas detectadas ({subject_sev})",
            html_content=html_content
        )

        sg = SendGridAPIClient(os.getenv('SENDGRID_API_KEY'))
        response = sg.send(mensaje)

        try:
            notif = Notificacion.objects.get(id=notificacion_id)
            notif.estado = 'enviada'
            notif.enviada_en = timezone.now()
            notif.save()
        except Exception:
            pass

        return f"Email agrupado enviado a {destinatario} - {total} alertas - Status: {response.status_code}"

    except Exception as e:
        try:
            notif = Notificacion.objects.get(id=notificacion_id)
            notif.estado = 'fallida'
            notif.save()
        except Exception:
            pass
        return f"Error enviando email agrupado: {e}"


@shared_task
def enviar_notificaciones_task(alerta_id):
    """Mantener compatibilidad — redirige a la versión agrupada."""
    try:
        alerta = Alerta.objects.get(id=alerta_id)
        enviar_notificaciones_agrupadas_task.delay(alerta.clinica_id, [alerta_id])
        return f"Notificación enviada para alerta {alerta_id}"
    except Exception as e:
        return f"Error: {e}"


@shared_task
def ejecutar_motor_todas_clinicas():
    clinicas = Clinica.objects.filter(activa=True)
    for clinica in clinicas:
        ejecutar_motor_task.delay(clinica.id)
    return f"Motor ejecutado para {clinicas.count()} clínicas"


@shared_task
def verificar_y_correr_motor_automatico():
    """Celery Beat lo llama cada hora. Solo corre el motor en clínicas
    con motor_automatico=True y donde ya pasó el intervalo configurado."""
    from django.utils import timezone
    from datetime import timedelta

    clinicas = Clinica.objects.filter(activa=True, motor_automatico=True)
    disparadas = 0
    for clinica in clinicas:
        intervalo = timedelta(hours=clinica.motor_intervalo_horas)
        ya_paso = (
            clinica.ultimo_motor_en is None
            or (timezone.now() - clinica.ultimo_motor_en) >= intervalo
        )
        if ya_paso:
            ejecutar_motor_task.delay(clinica.id)
            disparadas += 1

    return f"Motor automático: {disparadas}/{clinicas.count()} clínicas disparadas"


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


@shared_task
def limpiar_alertas_viejas_task(dias=7):
    """Marca como resueltas las alertas activas más viejas que `dias` días."""
    from django.utils import timezone
    from datetime import timedelta
    limite = timezone.now() - timedelta(days=dias)
    count = Alerta.objects.filter(
        estado='activa',
        creada_en__lt=limite
    ).update(estado='resuelta', revisada_en=timezone.now())
    return f"Limpieza: {count} alertas marcadas como resueltas"


@shared_task
def enviar_whatsapp_task(notificacion_id, alerta_ids, destinatario):
    """Envía mensaje WhatsApp vía Twilio con resumen de alertas."""
    try:
        from twilio.rest import Client
        from dotenv import load_dotenv
        from pathlib import Path
        env_path = Path(__file__).resolve().parent.parent / '.env'
        load_dotenv(env_path)

        account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        auth_token  = os.getenv('TWILIO_AUTH_TOKEN')
        from_number = os.getenv('TWILIO_FROM_NUMBER')  # format: whatsapp:+14155238886

        if not all([account_sid, auth_token, from_number]):
            return "Twilio no configurado — faltan variables de entorno"

        alertas = Alerta.objects.filter(id__in=alerta_ids).order_by('-severidad')
        total   = alertas.count()
        criticas = alertas.filter(severidad='critica').count()
        altas    = alertas.filter(severidad='alta').count()

        # Texto compacto para WhatsApp
        emoji_map = {'critica': '🔴', 'alta': '🟠', 'media': '🟡', 'baja': '🟢'}
        lineas = []
        for a in alertas[:5]:  # máximo 5 en el mensaje
            emoji = emoji_map.get(a.severidad, '⚠️')
            kpi = a.tipo_kpi.replace('_', ' ').title()
            lineas.append(f"{emoji} *{kpi}*: {a.valor_detectado} (esperado {a.valor_esperado})")

        body = (
            f"🏥 *Vigía — Alerta{'s' if total > 1 else ''}*\n"
            f"{total} anomalía{'s' if total > 1 else ''} detectada{'s' if total > 1 else ''}"
            + (f" · {criticas} crítica{'s' if criticas > 1 else ''}" if criticas else "")
            + (f" · {altas} alta{'s' if altas > 1 else ''}" if altas else "")
            + "\n\n"
            + "\n".join(lineas)
            + (f"\n_...y {total - 5} más_" if total > 5 else "")
            + "\n\n_Vigía · Sistema de Alertas_"
        )

        client = Client(account_sid, auth_token)
        client.messages.create(
            body=body,
            from_=from_number,
            to=f"whatsapp:{destinatario}"
        )

        try:
            notif = Notificacion.objects.get(id=notificacion_id)
            notif.estado = 'enviada'
            notif.enviada_en = timezone.now()
            notif.save()
        except Exception:
            pass

        return f"WhatsApp enviado a {destinatario} — {total} alertas"

    except Exception as e:
        try:
            notif = Notificacion.objects.get(id=notificacion_id)
            notif.estado = 'fallida'
            notif.save()
        except Exception:
            pass
        return f"Error enviando WhatsApp: {e}"