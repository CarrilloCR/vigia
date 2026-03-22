from django.contrib import admin
from .models import (
    Clinica, Sede, Usuario, Medico, Paciente, Cita, Encuesta,
    RegistroKPI, Alerta, Notificacion, FeedbackAlerta,
    ConfiguracionAlerta, IntegracionExterna, SyncLog, PlanFacturacion
)

@admin.register(Clinica)
class ClinicaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'email', 'plan', 'activa', 'creada_en']
    list_filter = ['plan', 'activa']
    search_fields = ['nombre', 'email']

@admin.register(Sede)
class SedeAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'clinica', 'telefono', 'activa']
    list_filter = ['activa', 'clinica']
    search_fields = ['nombre']

@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'email', 'clinica', 'rol', 'ultimo_acceso']
    list_filter = ['rol', 'clinica']
    search_fields = ['nombre', 'email']

@admin.register(Medico)
class MedicoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'apellido', 'especialidad', 'clinica', 'sede', 'activo']
    list_filter = ['especialidad', 'activo', 'clinica']
    search_fields = ['nombre', 'apellido']

@admin.register(Paciente)
class PacienteAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'apellido', 'clinica', 'telefono', 'primera_visita']
    list_filter = ['clinica']
    search_fields = ['nombre', 'apellido', 'email']

@admin.register(Cita)
class CitaAdmin(admin.ModelAdmin):
    list_display = ['paciente', 'medico', 'clinica', 'sede', 'fecha_hora_agendada', 'estado', 'ingreso_generado']
    list_filter = ['estado', 'clinica', 'medico']
    search_fields = ['paciente__nombre', 'medico__nombre']

@admin.register(Encuesta)
class EncuestaAdmin(admin.ModelAdmin):
    list_display = ['cita', 'paciente', 'puntuacion', 'respondida_en']
    list_filter = ['puntuacion']

@admin.register(RegistroKPI)
class RegistroKPIAdmin(admin.ModelAdmin):
    list_display = ['tipo', 'clinica', 'sede', 'medico', 'valor', 'periodo', 'fecha_hora']
    list_filter = ['tipo', 'periodo', 'clinica']

@admin.register(Alerta)
class AlertaAdmin(admin.ModelAdmin):
    list_display = ['tipo_kpi', 'clinica', 'severidad', 'estado', 'creada_en']
    list_filter = ['severidad', 'estado', 'clinica']
    search_fields = ['tipo_kpi', 'mensaje']

@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    list_display = ['alerta', 'usuario', 'canal', 'estado', 'enviada_en']
    list_filter = ['canal', 'estado']

@admin.register(FeedbackAlerta)
class FeedbackAlertaAdmin(admin.ModelAdmin):
    list_display = ['alerta', 'usuario', 'fue_util', 'creado_en']
    list_filter = ['fue_util']

@admin.register(ConfiguracionAlerta)
class ConfiguracionAlertaAdmin(admin.ModelAdmin):
    list_display = ['clinica', 'tipo_kpi', 'canal', 'umbral_sensibilidad', 'activa']
    list_filter = ['canal', 'activa']

@admin.register(IntegracionExterna)
class IntegracionExternaAdmin(admin.ModelAdmin):
    list_display = ['clinica', 'tipo', 'nombre', 'estado', 'ultima_sync']
    list_filter = ['tipo', 'estado']

@admin.register(SyncLog)
class SyncLogAdmin(admin.ModelAdmin):
    list_display = ['integracion', 'ejecutado_en', 'registros_importados', 'exitoso']
    list_filter = ['exitoso']

@admin.register(PlanFacturacion)
class PlanFacturacionAdmin(admin.ModelAdmin):
    list_display = ['clinica', 'plan', 'monto', 'moneda', 'estado', 'fecha_renovacion']
    list_filter = ['plan', 'estado']