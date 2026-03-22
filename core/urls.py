from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ClinicaViewSet, SedeViewSet, UsuarioViewSet,
    MedicoViewSet, PacienteViewSet, CitaViewSet,
    EncuestaViewSet, RegistroKPIViewSet, AlertaViewSet,
    NotificacionViewSet, FeedbackAlertaViewSet,
    ConfiguracionAlertaViewSet, IntegracionExternaViewSet,
    SyncLogViewSet, PlanFacturacionViewSet, ejecutar_motor
)

router = DefaultRouter()
router.register(r'clinicas', ClinicaViewSet)
router.register(r'sedes', SedeViewSet)
router.register(r'usuarios', UsuarioViewSet)
router.register(r'medicos', MedicoViewSet)
router.register(r'pacientes', PacienteViewSet)
router.register(r'citas', CitaViewSet)
router.register(r'encuestas', EncuestaViewSet)
router.register(r'kpis', RegistroKPIViewSet)
router.register(r'alertas', AlertaViewSet)
router.register(r'notificaciones', NotificacionViewSet)
router.register(r'feedbacks', FeedbackAlertaViewSet)
router.register(r'configuraciones', ConfiguracionAlertaViewSet)
router.register(r'integraciones', IntegracionExternaViewSet)
router.register(r'synclogs', SyncLogViewSet)
router.register(r'planes', PlanFacturacionViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('motor/ejecutar/', ejecutar_motor, name='ejecutar_motor'),
]