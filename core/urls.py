from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    ClinicaViewSet, SedeViewSet, UsuarioViewSet,
    MedicoViewSet, PacienteViewSet, CitaViewSet,
    EncuestaViewSet, RegistroKPIViewSet, AlertaViewSet,
    NotificacionViewSet, FeedbackAlertaViewSet,
    ConfiguracionAlertaViewSet, IntegracionExternaViewSet, EmailNotificacionViewSet,
    SyncLogViewSet, PlanFacturacionViewSet, ejecutar_motor, generar_datos, importar_csv
)
from .auth import register, login, logout, me, cambiar_password

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
router.register(r'emails-notificacion', EmailNotificacionViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('motor/ejecutar/', ejecutar_motor, name='ejecutar_motor'),
    path('generador/ejecutar/', generar_datos, name='generar_datos'),
    path('integraciones/importar_csv/', importar_csv, name='importar_csv'),
    # Auth
    path('auth/register/', register, name='register'),
    path('auth/login/', login, name='login'),
    path('auth/logout/', logout, name='logout'),
    path('auth/me/', me, name='me'),
    path('auth/cambiar-password/', cambiar_password, name='cambiar_password'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]