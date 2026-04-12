from rest_framework import serializers
from .models import (
    Clinica, Sede, Usuario, Medico, Paciente, Cita, Encuesta,
    RegistroKPI, Alerta, Notificacion, FeedbackAlerta,
    ConfiguracionAlerta, IntegracionExterna, SyncLog, PlanFacturacion, EmailNotificacion,
    SolicitudRol
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
    sede_nombre = serializers.CharField(source='sede.nombre', read_only=True, default=None)

    class Meta:
        model = Usuario
        fields = '__all__'


class MedicoSerializer(serializers.ModelSerializer):
    sede_nombre = serializers.CharField(source='sede.nombre', read_only=True, default=None)

    class Meta:
        model = Medico
        fields = '__all__'


class PacienteSerializer(serializers.ModelSerializer):
    sede_nombre = serializers.CharField(source='sede.nombre', read_only=True, default=None)

    class Meta:
        model = Paciente
        fields = '__all__'


class CitaSerializer(serializers.ModelSerializer):
    paciente_nombre = serializers.SerializerMethodField()
    medico_nombre = serializers.SerializerMethodField()
    sede_nombre = serializers.CharField(source='sede.nombre', read_only=True, default=None)

    class Meta:
        model = Cita
        fields = '__all__'

    def get_paciente_nombre(self, obj):
        return f"{obj.paciente.nombre} {obj.paciente.apellido}" if obj.paciente else ''

    def get_medico_nombre(self, obj):
        return f"Dr. {obj.medico.nombre} {obj.medico.apellido}" if obj.medico else ''


class EncuestaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Encuesta
        fields = '__all__'


class RegistroKPISerializer(serializers.ModelSerializer):
    class Meta:
        model = RegistroKPI
        fields = '__all__'


class AlertaSerializer(serializers.ModelSerializer):
    sede_nombre = serializers.CharField(source='sede.nombre', read_only=True, default=None)

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


class SolicitudRolSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.CharField(source='usuario.nombre', read_only=True)
    usuario_email = serializers.CharField(source='usuario.email', read_only=True)
    clinica_nombre = serializers.CharField(source='usuario.clinica.nombre', read_only=True)
    revisada_por_nombre = serializers.CharField(source='revisada_por.nombre', read_only=True)

    class Meta:
        model = SolicitudRol
        fields = '__all__'
