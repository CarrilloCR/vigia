from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ClinicaViewSet, MedicoViewSet, PacienteViewSet,
    CitaViewSet, RegistroKPIViewSet, AlertaViewSet,
    ConfiguracionAlertaViewSet
)

router = DefaultRouter()
router.register(r'clinicas', ClinicaViewSet)
router.register(r'medicos', MedicoViewSet)
router.register(r'pacientes', PacienteViewSet)
router.register(r'citas', CitaViewSet)
router.register(r'kpis', RegistroKPIViewSet)
router.register(r'alertas', AlertaViewSet)
router.register(r'configuraciones', ConfiguracionAlertaViewSet)

urlpatterns = [
    path('', include(router.urls)),
]