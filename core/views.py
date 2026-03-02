from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.utils import timezone
from .models import Clinica, Medico, Paciente, Cita, RegistroKPI, Alerta, ConfiguracionAlerta
from .serializers import (
    ClinicaSerializer, MedicoSerializer, PacienteSerializer,
    CitaSerializer, RegistroKPISerializer, AlertaSerializer,
    ConfiguracionAlertaSerializer
)

class ClinicaViewSet(viewsets.ModelViewSet):
    queryset = Clinica.objects.all()
    serializer_class = ClinicaSerializer

class MedicoViewSet(viewsets.ModelViewSet):
    queryset = Medico.objects.all()
    serializer_class = MedicoSerializer

    def get_queryset(self):
        queryset = Medico.objects.all()
        clinica_id = self.request.query_params.get('clinica')
        if clinica_id:
            queryset = queryset.filter(clinica_id=clinica_id)
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
        estado = self.request.query_params.get('estado')
        if clinica_id:
            queryset = queryset.filter(clinica_id=clinica_id)
        if medico_id:
            queryset = queryset.filter(medico_id=medico_id)
        if estado:
            queryset = queryset.filter(estado=estado)
        return queryset

class RegistroKPIViewSet(viewsets.ModelViewSet):
    queryset = RegistroKPI.objects.all()
    serializer_class = RegistroKPISerializer

    def get_queryset(self):
        queryset = RegistroKPI.objects.all()
        clinica_id = self.request.query_params.get('clinica')
        tipo = self.request.query_params.get('tipo')
        if clinica_id:
            queryset = queryset.filter(clinica_id=clinica_id)
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
        if clinica_id:
            queryset = queryset.filter(clinica_id=clinica_id)
        if estado:
            queryset = queryset.filter(estado=estado)
        if severidad:
            queryset = queryset.filter(severidad=severidad)
        return queryset.order_by('-creada_en')

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

class ConfiguracionAlertaViewSet(viewsets.ModelViewSet):
    queryset = ConfiguracionAlerta.objects.all()
    serializer_class = ConfiguracionAlertaSerializer

    def get_queryset(self):
        queryset = ConfiguracionAlerta.objects.all()
        clinica_id = self.request.query_params.get('clinica')
        if clinica_id:
            queryset = queryset.filter(clinica_id=clinica_id)
        return queryset

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from .motor import correr_motor

@api_view(['POST'])
@permission_classes([AllowAny])
def ejecutar_motor(request):
    clinica_id = request.data.get('clinica_id')
    if not clinica_id:
        return Response({'error': 'clinica_id es requerido'}, status=status.HTTP_400_BAD_REQUEST)
    correr_motor(clinica_id)
    return Response({'status': 'motor ejecutado correctamente'})