from rest_framework import serializers
from .models import (
    Clinica, Sede, Usuario, Medico, Paciente, Cita, Encuesta,
    RegistroKPI, Alerta, Notificacion, FeedbackAlerta,
    ConfiguracionAlerta, IntegracionExterna, SyncLog, PlanFacturacion, EmailNotificacion
)

class ClinicaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Clinica
        fields = '__all__'

class SedeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sede
        fields = '__all__'

class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = '__all__'

class MedicoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Medico
        fields = '__all__'

class PacienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Paciente
        fields = '__all__'

class CitaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cita
        fields = '__all__'

class EncuestaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Encuesta
        fields = '__all__'

class RegistroKPISerializer(serializers.ModelSerializer):
    class Meta:
        model = RegistroKPI
        fields = '__all__'

class AlertaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Alerta
        fields = '__all__'

class NotificacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notificacion
        fields = '__all__'

class FeedbackAlertaSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeedbackAlerta
        fields = '__all__'

class ConfiguracionAlertaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfiguracionAlerta
        fields = '__all__'

class IntegracionExternaSerializer(serializers.ModelSerializer):
    class Meta:
        model = IntegracionExterna
        fields = '__all__'

class SyncLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = SyncLog
        fields = '__all__'

class PlanFacturacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlanFacturacion
        fields = '__all__'

class EmailNotificacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailNotificacion
        fields = '__all__'