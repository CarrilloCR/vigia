from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.utils import timezone
from .models import (
    Clinica, Sede, Usuario, Medico, Paciente, Cita, Encuesta,
    RegistroKPI, Alerta, Notificacion, FeedbackAlerta,
    ConfiguracionAlerta, IntegracionExterna, SyncLog, PlanFacturacion
)
from .serializers import (
    ClinicaSerializer, SedeSerializer, UsuarioSerializer,
    MedicoSerializer, PacienteSerializer, CitaSerializer,
    EncuestaSerializer, RegistroKPISerializer, AlertaSerializer,
    NotificacionSerializer, FeedbackAlertaSerializer,
    ConfiguracionAlertaSerializer, IntegracionExternaSerializer,
    SyncLogSerializer, PlanFacturacionSerializer
)
from .motor import correr_motor


class ClinicaViewSet(viewsets.ModelViewSet):
    queryset = Clinica.objects.all()
    serializer_class = ClinicaSerializer


class SedeViewSet(viewsets.ModelViewSet):
    queryset = Sede.objects.all()
    serializer_class = SedeSerializer

    def get_queryset(self):
        queryset = Sede.objects.all()
        clinica_id = self.request.query_params.get('clinica')
        if clinica_id:
            queryset = queryset.filter(clinica_id=clinica_id)
        return queryset


class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = Usuario.objects.all()
    serializer_class = UsuarioSerializer

    def get_queryset(self):
        queryset = Usuario.objects.all()
        clinica_id = self.request.query_params.get('clinica')
        if clinica_id:
            queryset = queryset.filter(clinica_id=clinica_id)
        return queryset


class MedicoViewSet(viewsets.ModelViewSet):
    queryset = Medico.objects.all()
    serializer_class = MedicoSerializer

    def get_queryset(self):
        queryset = Medico.objects.all()
        clinica_id = self.request.query_params.get('clinica')
        sede_id = self.request.query_params.get('sede')
        if clinica_id:
            queryset = queryset.filter(clinica_id=clinica_id)
        if sede_id:
            queryset = queryset.filter(sede_id=sede_id)
        return queryset


class PacienteViewSet(viewsets.ModelViewSet):
    queryset = Paciente.objects.all()
    serializer_class = PacienteSerializer

    def get_queryset(self):
        queryset = Paciente.objects.all()
        clinica_id = self.request.query_params.get('clinica')
        if clinica_id:
            queryset = queryset.filter(clinica_id=clinica_id)
        return queryset


class CitaViewSet(viewsets.ModelViewSet):
    queryset = Cita.objects.all()
    serializer_class = CitaSerializer

    def get_queryset(self):
        queryset = Cita.objects.all()
        clinica_id = self.request.query_params.get('clinica')
        medico_id = self.request.query_params.get('medico')
        sede_id = self.request.query_params.get('sede')
        estado = self.request.query_params.get('estado')
        if clinica_id:
            queryset = queryset.filter(clinica_id=clinica_id)
        if medico_id:
            queryset = queryset.filter(medico_id=medico_id)
        if sede_id:
            queryset = queryset.filter(sede_id=sede_id)
        if estado:
            queryset = queryset.filter(estado=estado)
        return queryset


class EncuestaViewSet(viewsets.ModelViewSet):
    queryset = Encuesta.objects.all()
    serializer_class = EncuestaSerializer


class RegistroKPIViewSet(viewsets.ModelViewSet):
    queryset = RegistroKPI.objects.all()
    serializer_class = RegistroKPISerializer

    def get_queryset(self):
        queryset = RegistroKPI.objects.all()
        clinica_id = self.request.query_params.get('clinica')
        medico_id = self.request.query_params.get('medico')
        tipo = self.request.query_params.get('tipo')
        if clinica_id:
            queryset = queryset.filter(clinica_id=clinica_id)
        if medico_id:
            queryset = queryset.filter(medico_id=medico_id)
        if tipo:
            queryset = queryset.filter(tipo=tipo)
        return queryset


class AlertaViewSet(viewsets.ModelViewSet):
    queryset = Alerta.objects.all()
    serializer_class = AlertaSerializer

    def get_queryset(self):
        queryset = Alerta.objects.all()
        clinica_id = self.request.query_params.get('clinica')
        estado = self.request.query_params.get('estado')
        severidad = self.request.query_params.get('severidad')
        medico_id = self.request.query_params.get('medico')
        if clinica_id:
            queryset = queryset.filter(clinica_id=clinica_id)
        if estado:
            queryset = queryset.filter(estado=estado)
        if severidad:
            queryset = queryset.filter(severidad=severidad)
        if medico_id:
            queryset = queryset.filter(medico_id=medico_id)
        return queryset.order_by('-creada_en')

    from rest_framework.decorators import action

    @action(detail=True, methods=['post'])
    def marcar_revisada(self, request, pk=None):
        alerta = self.get_object()
        alerta.estado = 'revisada'
        alerta.revisada_en = timezone.now()
        alerta.save()
        return Response({'status': 'alerta marcada como revisada'})

    @action(detail=True, methods=['post'])
    def marcar_resuelta(self, request, pk=None):
        alerta = self.get_object()
        alerta.estado = 'resuelta'
        alerta.revisada_en = timezone.now()
        alerta.save()
        return Response({'status': 'alerta marcada como resuelta'})


class NotificacionViewSet(viewsets.ModelViewSet):
    queryset = Notificacion.objects.all()
    serializer_class = NotificacionSerializer

    def get_queryset(self):
        queryset = Notificacion.objects.all()
        alerta_id = self.request.query_params.get('alerta')
        usuario_id = self.request.query_params.get('usuario')
        if alerta_id:
            queryset = queryset.filter(alerta_id=alerta_id)
        if usuario_id:
            queryset = queryset.filter(usuario_id=usuario_id)
        return queryset


class FeedbackAlertaViewSet(viewsets.ModelViewSet):
    queryset = FeedbackAlerta.objects.all()
    serializer_class = FeedbackAlertaSerializer

    def get_queryset(self):
        queryset = FeedbackAlerta.objects.all()
        alerta_id = self.request.query_params.get('alerta')
        if alerta_id:
            queryset = queryset.filter(alerta_id=alerta_id)
        return queryset


class ConfiguracionAlertaViewSet(viewsets.ModelViewSet):
    queryset = ConfiguracionAlerta.objects.all()
    serializer_class = ConfiguracionAlertaSerializer

    def get_queryset(self):
        queryset = ConfiguracionAlerta.objects.all()
        clinica_id = self.request.query_params.get('clinica')
        if clinica_id:
            queryset = queryset.filter(clinica_id=clinica_id)
        return queryset


class IntegracionExternaViewSet(viewsets.ModelViewSet):
    queryset = IntegracionExterna.objects.all()
    serializer_class = IntegracionExternaSerializer

    def get_queryset(self):
        queryset = IntegracionExterna.objects.all()
        clinica_id = self.request.query_params.get('clinica')
        if clinica_id:
            queryset = queryset.filter(clinica_id=clinica_id)
        return queryset


class SyncLogViewSet(viewsets.ModelViewSet):
    queryset = SyncLog.objects.all()
    serializer_class = SyncLogSerializer

    def get_queryset(self):
        queryset = SyncLog.objects.all()
        integracion_id = self.request.query_params.get('integracion')
        if integracion_id:
            queryset = queryset.filter(integracion_id=integracion_id)
        return queryset


class PlanFacturacionViewSet(viewsets.ModelViewSet):
    queryset = PlanFacturacion.objects.all()
    serializer_class = PlanFacturacionSerializer

    def get_queryset(self):
        queryset = PlanFacturacion.objects.all()
        clinica_id = self.request.query_params.get('clinica')
        if clinica_id:
            queryset = queryset.filter(clinica_id=clinica_id)
        return queryset


@api_view(['POST'])
@permission_classes([AllowAny])
def ejecutar_motor(request):
    clinica_id = request.data.get('clinica_id')
    if not clinica_id:
        return Response({'error': 'clinica_id es requerido'}, status=status.HTTP_400_BAD_REQUEST)
    correr_motor(clinica_id)
    return Response({'status': 'motor ejecutado correctamente'})