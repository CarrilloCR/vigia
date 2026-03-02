from django.contrib import admin
from .models import Clinica, Medico, Paciente, Cita, RegistroKPI, Alerta, ConfiguracionAlerta

@admin.register(Clinica)
class ClinicaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'email', 'plan', 'activa', 'creada_en']
    list_filter = ['plan', 'activa']
    search_fields = ['nombre', 'email']

@admin.register(Medico)
class MedicoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'apellido', 'especialidad', 'clinica', 'activo']
    list_filter = ['especialidad', 'activo', 'clinica']
    search_fields = ['nombre', 'apellido']

@admin.register(Paciente)
class PacienteAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'apellido', 'clinica', 'telefono', 'primera_visita']
    list_filter = ['clinica']
    search_fields = ['nombre', 'apellido', 'email']

@admin.register(Cita)
class CitaAdmin(admin.ModelAdmin):
    list_display = ['paciente', 'medico', 'clinica', 'fecha_hora_agendada', 'estado', 'ingreso_generado']
    list_filter = ['estado', 'clinica', 'medico']
    search_fields = ['paciente__nombre', 'medico__nombre']

@admin.register(RegistroKPI)
class RegistroKPIAdmin(admin.ModelAdmin):
    list_display = ['tipo', 'clinica', 'medico', 'valor', 'periodo', 'fecha_hora']
    list_filter = ['tipo', 'periodo', 'clinica']

@admin.register(Alerta)
class AlertaAdmin(admin.ModelAdmin):
    list_display = ['tipo_kpi', 'clinica', 'severidad', 'estado', 'creada_en']
    list_filter = ['severidad', 'estado', 'clinica']
    search_fields = ['tipo_kpi', 'mensaje']

@admin.register(ConfiguracionAlerta)
class ConfiguracionAlertaAdmin(admin.ModelAdmin):
    list_display = ['clinica', 'tipo_kpi', 'canal', 'umbral_sensibilidad', 'activa']
    list_filter = ['canal', 'activa']