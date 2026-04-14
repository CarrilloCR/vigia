from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta
from .models import (
    Clinica, Sede, Usuario, Medico, Paciente, Cita, Encuesta,
    RegistroKPI, Alerta, Notificacion, FeedbackAlerta,
    ConfiguracionAlerta, IntegracionExterna, SyncLog, PlanFacturacion, EmailNotificacion,
    SolicitudRol
)
from .serializers import (
    ClinicaSerializer, SedeSerializer, UsuarioSerializer,
    MedicoSerializer, PacienteSerializer, CitaSerializer,
    EncuestaSerializer, RegistroKPISerializer, AlertaSerializer,
    NotificacionSerializer, FeedbackAlertaSerializer,
    ConfiguracionAlertaSerializer, IntegracionExternaSerializer,
    SyncLogSerializer, PlanFacturacionSerializer, EmailNotificacionSerializer,
    SolicitudRolSerializer
)
from .motor import correr_motor


# ─── Helper: sede-scope filtering ────────────────────────────────────────────

def _get_usuario(request):
    """Resolve the Vigía Usuario from the JWT-authenticated Django user."""
    if request.user and request.user.is_authenticated:
        try:
            return Usuario.objects.get(email=request.user.email)
        except Usuario.DoesNotExist:
            pass
    return None


def apply_sede_scope(request, queryset, sede_field='sede_id'):
    """
    Gerentes are locked to their sede.
    Medicos: locked to their sede (from usuario or from their Medico profile).
    Otherwise honour the ?sede= query param if present.
    """
    usuario = _get_usuario(request)
    if usuario and usuario.rol == 'gerente' and usuario.sede_id:
        return queryset.filter(**{sede_field: usuario.sede_id})
    if usuario and usuario.rol == 'medico':
        # Prefer sede from usuario profile; fall back to Medico profile sede
        sede_id = usuario.sede_id
        if not sede_id:
            medico = usuario.medico_perfil.filter(activo=True).first()
            if medico and medico.sede_id:
                sede_id = medico.sede_id
        if sede_id:
            return queryset.filter(**{sede_field: sede_id})
        # Medico with no sede: no sede restriction (see all clinic data)
        return queryset
    sede_id = request.query_params.get('sede')
    if sede_id:
        return queryset.filter(**{sede_field: sede_id})
    return queryset


def _get_medico_del_usuario(usuario):
    """Return the Medico profile for a usuario with rol='medico', or None."""
    if usuario and usuario.rol == 'medico':
        return usuario.medico_perfil.filter(activo=True).first()
    return None


def apply_medico_scope(request, queryset, medico_field='medico_id'):
    """
    When the caller is a medico, force-filter to their own Medico profile.
    Also honours the ?medico= query param for admin/superadmin users.
    """
    usuario = _get_usuario(request)
    medico = _get_medico_del_usuario(usuario)
    if medico:
        return queryset.filter(**{medico_field: medico.id})
    medico_id = request.query_params.get('medico')
    if medico_id:
        return queryset.filter(**{medico_field: medico_id})
    return queryset


# ─── Public endpoint: list clinics + sedes for registration ──────────────────

@api_view(['GET'])
@permission_classes([AllowAny])
def listar_clinicas_publico(request):
    """Returns all active clinics with their active sedes — used in registration."""
    clinicas = Clinica.objects.filter(activa=True).values('id', 'nombre')
    result = []
    for c in clinicas:
        sedes = list(Sede.objects.filter(clinica_id=c['id'], activa=True).values('id', 'nombre'))
        result.append({**c, 'sedes': sedes})
    return Response(result)


# ─── ViewSets ─────────────────────────────────────────────────────────────────

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
        queryset = apply_sede_scope(self.request, queryset)
        return queryset

    @action(detail=False, methods=['post'])
    def invitar(self, request):
        from django.contrib.hashers import make_password
        import secrets
        clinica_id = request.data.get('clinica_id')
        email = request.data.get('email', '').strip()
        nombre = request.data.get('nombre', '').strip()
        rol = request.data.get('rol', 'viewer')

        if not email or not clinica_id:
            return Response({'error': 'email y clinica_id son requeridos'}, status=status.HTTP_400_BAD_REQUEST)
        if Usuario.objects.filter(email=email).exists():
            return Response({'error': 'Ya existe un usuario con ese email'}, status=status.HTTP_400_BAD_REQUEST)

        temp_password = secrets.token_urlsafe(12)
        usuario = Usuario.objects.create(
            clinica_id=clinica_id,
            nombre=nombre or email.split('@')[0],
            email=email,
            password_hash=make_password(temp_password),
            rol=rol,
        )
        serializer = self.get_serializer(usuario)
        return Response({**serializer.data, 'temp_password': temp_password}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def desactivar(self, request, pk=None):
        # Reutilizamos el campo 'activo' — si no existe en el modelo, simplemente
        # bloqueamos marcando el email con prefijo INACTIVO
        usuario = self.get_object()
        usuario.email = f"INACTIVO_{usuario.id}_{usuario.email}" if not usuario.email.startswith('INACTIVO') else usuario.email
        usuario.save()
        return Response({'status': 'usuario desactivado'})

    @action(detail=True, methods=['post'])
    def cambiar_rol(self, request, pk=None):
        usuario = self.get_object()
        nuevo_rol = request.data.get('rol')
        if nuevo_rol not in ('admin', 'gerente', 'medico', 'viewer'):
            return Response({'error': 'rol inválido'}, status=status.HTTP_400_BAD_REQUEST)
        usuario.rol = nuevo_rol
        usuario.save()
        return Response({'status': 'rol actualizado', 'rol': nuevo_rol})


class MedicoViewSet(viewsets.ModelViewSet):
    queryset = Medico.objects.all()
    serializer_class = MedicoSerializer

    def get_queryset(self):
        queryset = Medico.objects.all()
        clinica_id = self.request.query_params.get('clinica')
        if clinica_id:
            queryset = queryset.filter(clinica_id=clinica_id)
        queryset = apply_sede_scope(self.request, queryset)
        return queryset


class PacienteViewSet(viewsets.ModelViewSet):
    queryset = Paciente.objects.all()
    serializer_class = PacienteSerializer

    def get_queryset(self):
        queryset = Paciente.objects.all()
        clinica_id = self.request.query_params.get('clinica')
        mostrar_inactivos = self.request.query_params.get('inactivos', 'false').lower() == 'true'
        if clinica_id:
            queryset = queryset.filter(clinica_id=clinica_id)
        if not mostrar_inactivos:
            queryset = queryset.filter(activo=True)
        queryset = apply_sede_scope(self.request, queryset)
        # For medicos: only show patients they have citas with
        usuario = _get_usuario(self.request)
        medico = _get_medico_del_usuario(usuario)
        if medico:
            queryset = queryset.filter(citas__medico=medico).distinct()
        return queryset


class CitaViewSet(viewsets.ModelViewSet):
    queryset = Cita.objects.all()
    serializer_class = CitaSerializer

    def get_queryset(self):
        queryset = Cita.objects.all()
        clinica_id = self.request.query_params.get('clinica')
        estado = self.request.query_params.get('estado')
        if clinica_id:
            queryset = queryset.filter(clinica_id=clinica_id)
        if estado:
            queryset = queryset.filter(estado=estado)
        queryset = apply_sede_scope(self.request, queryset)
        queryset = apply_medico_scope(self.request, queryset)
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
        tipo = self.request.query_params.get('tipo')
        horas = self.request.query_params.get('horas', '24')

        if clinica_id:
            queryset = queryset.filter(clinica_id=clinica_id)
        if tipo:
            queryset = queryset.filter(tipo=tipo)
        queryset = apply_sede_scope(self.request, queryset)
        # KPIs are sede/clinic-level records — medico field is always null in generated data.
        # Honour explicit ?medico= param only.
        explicit_medico = self.request.query_params.get('medico')
        if explicit_medico:
            queryset = queryset.filter(medico_id=explicit_medico)
        desde = timezone.now() - timedelta(hours=int(horas))
        queryset = queryset.filter(fecha_hora__gte=desde)
        return queryset.order_by('fecha_hora')

    @action(detail=False, methods=['get'], url_path='exportar')
    def exportar(self, request):
        """
        Devuelve todos los registros KPI del período con scores de detección
        (estadístico, Prophet, PyOD) calculados en el momento.
        Params: clinica, sede (opcional), horas (default 720 = 30d)
        """
        from .deteccion import detectar_estadistico, detectar_prophet, detectar_pyod

        clinica_id = request.query_params.get('clinica')
        horas = int(request.query_params.get('horas', 720))
        sede_id = request.query_params.get('sede') or None

        if not clinica_id:
            return Response({'error': 'clinica requerida'}, status=status.HTTP_400_BAD_REQUEST)

        desde = timezone.now() - timedelta(hours=horas)
        qs = RegistroKPI.objects.filter(clinica_id=clinica_id, fecha_hora__gte=desde)
        if sede_id:
            qs = qs.filter(sede_id=sede_id)
        qs = qs.order_by('tipo', 'sede_id', 'fecha_hora')

        # Group by (tipo, sede_id) to compute rolling detection
        from itertools import groupby
        rows = list(qs.select_related('sede'))
        resultado = []

        def key_fn(r):
            return (r.tipo, r.sede_id)

        for (tipo, s_id), grupo in groupby(rows, key=key_fn):
            grupo = list(grupo)
            sede_nombre = grupo[0].sede.nombre if grupo[0].sede else 'General'

            # Collect historical context BEFORE the period for better baselines
            hist_pre = list(
                RegistroKPI.objects.filter(
                    clinica_id=clinica_id, tipo=tipo, sede_id=s_id,
                    fecha_hora__lt=desde
                ).order_by('-fecha_hora').values_list('valor', flat=True)[:60]
            )

            # For Prophet: historical with dates before the period
            hist_fechas_pre = list(
                RegistroKPI.objects.filter(
                    clinica_id=clinica_id, tipo=tipo, sede_id=s_id,
                    fecha_hora__lt=desde
                ).order_by('fecha_hora').values_list('fecha_hora', 'valor')
            )

            rolling_valores = list(hist_pre)  # oldest first in rolling window

            for rec in grupo:
                valor = rec.valor
                historico = list(reversed(rolling_valores[-60:]))  # latest first

                # Statistical
                stat_anom, stat_esp, stat_dev = detectar_estadistico(valor, historico)

                # Prophet (needs ≥14 points)
                hist_fechas = hist_fechas_pre + [(r.fecha_hora, r.valor) for r in grupo if r.fecha_hora < rec.fecha_hora]
                prophet_result = None
                if len(hist_fechas) >= 14:
                    p_anom, p_esp, p_dev, p_extra = detectar_prophet(valor, hist_fechas)
                    if p_anom is not None:
                        prophet_result = {
                            'es_anomalia': p_anom,
                            'valor_esperado': p_esp,
                            'desviacion': p_dev,
                            **(p_extra or {}),
                        }

                # PyOD (needs ≥10 points)
                pyod_result = None
                if len(historico) >= 10:
                    py_anom, py_esp, py_dev, py_extra = detectar_pyod(valor, historico)
                    if py_anom is not None:
                        pyod_result = {
                            'es_anomalia': py_anom,
                            'valor_esperado': py_esp,
                            'desviacion': py_dev,
                            **(py_extra or {}),
                        }

                resultado.append({
                    'id': rec.id,
                    'fecha_hora': rec.fecha_hora.isoformat(),
                    'tipo_kpi': tipo,
                    'sede_id': s_id,
                    'sede_nombre': sede_nombre,
                    'valor': valor,
                    'periodo': rec.periodo,
                    'deteccion': {
                        'estadistico': {
                            'es_anomalia': stat_anom,
                            'valor_esperado': stat_esp,
                            'desviacion_pct': stat_dev,
                        },
                        'prophet': prophet_result,
                        'pyod': pyod_result,
                    },
                })

                rolling_valores.append(valor)

        return Response(resultado)


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
        queryset = apply_sede_scope(self.request, queryset)
        # Alertas are clinic/sede-level — NOT filtered by medico_id (always null).
        # Honour explicit ?medico= param for admins viewing a specific doctor.
        explicit_medico = self.request.query_params.get('medico')
        if explicit_medico:
            queryset = queryset.filter(medico_id=explicit_medico)
        dias = self.request.query_params.get('dias')
        if dias:
            desde = timezone.now() - timedelta(days=int(dias))
            queryset = queryset.filter(creada_en__gte=desde)

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

    @action(detail=False, methods=['post'])
    def resolver_todas(self, request):
        clinica_id = request.data.get('clinica_id')
        if not clinica_id:
            return Response({'error': 'clinica_id requerido'}, status=status.HTTP_400_BAD_REQUEST)
        count = Alerta.objects.filter(clinica_id=clinica_id, estado='activa').update(
            estado='revisada', revisada_en=timezone.now()
        )
        return Response({'status': f'{count} alertas marcadas como revisadas'})

    @action(detail=False, methods=['post'])
    def revisar_todas(self, request):
        clinica_id = request.data.get('clinica_id')
        if not clinica_id:
            return Response({'error': 'clinica_id requerido'}, status=status.HTTP_400_BAD_REQUEST)
        count = Alerta.objects.filter(clinica_id=clinica_id, estado='activa').update(
            estado='revisada', revisada_en=timezone.now()
        )
        return Response({'status': f'{count} alertas revisadas'})


class NotificacionViewSet(viewsets.ModelViewSet):
    queryset = Notificacion.objects.all()
    serializer_class = NotificacionSerializer

    def get_queryset(self):
        queryset = Notificacion.objects.all()
        alerta_id = self.request.query_params.get('alerta')
        usuario_id = self.request.query_params.get('usuario')
        estado = self.request.query_params.get('estado')
        clinica_id = self.request.query_params.get('clinica')
        if alerta_id:
            queryset = queryset.filter(alerta_id=alerta_id)
        if usuario_id:
            queryset = queryset.filter(usuario_id=usuario_id)
        if estado:
            queryset = queryset.filter(estado=estado)
        if clinica_id:
            queryset = queryset.filter(alerta__clinica_id=clinica_id)
        queryset = apply_sede_scope(self.request, queryset, sede_field='alerta__sede_id')
        return queryset.order_by('-enviada_en')

    @action(detail=False, methods=['post'])
    def marcar_todas_leidas(self, request):
        clinica_id = request.data.get('clinica_id')
        qs = Notificacion.objects.filter(estado__in=['enviada', 'entregada', 'pendiente'])
        if clinica_id:
            qs = qs.filter(alerta__clinica_id=clinica_id)
        count = qs.update(estado='leida', leida_en=timezone.now())
        return Response({'status': f'{count} notificaciones marcadas como leídas'})


class FeedbackAlertaViewSet(viewsets.ModelViewSet):
    queryset = FeedbackAlerta.objects.all()
    serializer_class = FeedbackAlertaSerializer

    def get_queryset(self):
        queryset = FeedbackAlerta.objects.all()
        alerta_id = self.request.query_params.get('alerta')
        fue_util = self.request.query_params.get('fue_util')
        if alerta_id:
            queryset = queryset.filter(alerta_id=alerta_id)
        if fue_util is not None:
            queryset = queryset.filter(fue_util=fue_util == 'true')
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

    @action(detail=False, methods=['post'], url_path='importar_csv')
    def importar_csv(self, request):
        return importar_csv(request)


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

class EmailNotificacionViewSet(viewsets.ModelViewSet):
    queryset = EmailNotificacion.objects.all()
    serializer_class = EmailNotificacionSerializer

    def get_queryset(self):
        queryset = EmailNotificacion.objects.all()
        clinica_id = self.request.query_params.get('clinica')
        if clinica_id:
            queryset = queryset.filter(clinica_id=clinica_id)
        return queryset.filter(activo=True)


@api_view(['POST'])
@permission_classes([AllowAny])
def ejecutar_motor(request):
    clinica_id = request.data.get('clinica_id')
    if not clinica_id:
        return Response({'error': 'clinica_id es requerido'}, status=status.HTTP_400_BAD_REQUEST)
    correr_motor(clinica_id, enviar_notif=True)
    return Response({'status': 'motor ejecutado correctamente'})


@api_view(['POST'])
@permission_classes([AllowAny])
def generar_datos(request):
    clinica_id = request.data.get('clinica_id')
    from .tasks import generar_datos_clinica_task, generar_datos_falsos_task
    if clinica_id:
        generar_datos_clinica_task.delay(int(clinica_id))
        return Response({'status': f'Generando datos para clínica {clinica_id}'})
    else:
        generar_datos_falsos_task.delay()
        return Response({'status': 'Generando datos para todas las clínicas'})


@api_view(['POST'])
@permission_classes([AllowAny])
def toggle_generador(request):
    clinica_id = request.data.get('clinica_id')
    if not clinica_id:
        return Response({'error': 'clinica_id requerido'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        clinica = Clinica.objects.get(id=clinica_id)
        clinica.generador_activo = not clinica.generador_activo
        clinica.save(update_fields=['generador_activo'])
        return Response({'generador_activo': clinica.generador_activo})
    except Clinica.DoesNotExist:
        return Response({'error': 'Clínica no encontrada'}, status=status.HTTP_404_NOT_FOUND)


def importar_csv(request):
    """
    Importa un archivo CSV para crear RegistroKPI o Cita.
    Params: clinica_id, sede_id (opcional), tipo (kpi|citas), file (multipart)
    Columnas KPI: tipo,valor,fecha_hora (fecha_hora opcional, usa now())
    Columnas Citas: medico_id,estado,ingreso_generado,fecha_hora_agendada (medico_id puede ser vacío)
    Llamado como @action desde IntegracionExternaViewSet.
    """
    import csv
    import io
    from django.utils.dateparse import parse_datetime

    clinica_id = request.data.get('clinica_id')
    sede_id = request.data.get('sede_id') or None
    tipo = request.data.get('tipo', 'kpi')
    archivo = request.FILES.get('file')

    if not clinica_id or not archivo:
        return Response({'error': 'clinica_id y file son requeridos'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        clinica = Clinica.objects.get(id=clinica_id)
    except Clinica.DoesNotExist:
        return Response({'error': 'Clínica no encontrada'}, status=status.HTTP_404_NOT_FOUND)

    sede = None
    if sede_id:
        try:
            sede = Sede.objects.get(id=sede_id, clinica=clinica)
        except Sede.DoesNotExist:
            return Response({'error': 'Sede no encontrada en esa clínica'}, status=status.HTTP_404_NOT_FOUND)

    # Crear o reutilizar la integración CSV de esta clínica
    integracion, _ = IntegracionExterna.objects.get_or_create(
        clinica=clinica, tipo='csv',
        defaults={'nombre': 'Importación CSV', 'estado': 'activa'}
    )

    errores = []
    creados = 0

    try:
        contenido = archivo.read().decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(contenido))
        filas = list(reader)

        TIPOS_KPI_VALIDOS = [
            'tasa_cancelacion', 'tasa_noshow', 'ocupacion_agenda', 'tiempo_espera',
            'ingresos_dia', 'ticket_promedio', 'pacientes_nuevos', 'retencion_90',
            'cancelaciones_medico', 'citas_reagendadas', 'nps',
        ]
        ESTADOS_CITA_VALIDOS = ['agendada', 'completada', 'cancelada', 'no_show', 'reagendada']

        if tipo == 'kpi':
            for i, fila in enumerate(filas, 1):
                try:
                    tipo_kpi = fila.get('tipo', '').strip()
                    valor_str = fila.get('valor', '').strip()
                    fecha_str = fila.get('fecha_hora', '').strip()

                    if tipo_kpi not in TIPOS_KPI_VALIDOS:
                        errores.append(f"Fila {i}: tipo '{tipo_kpi}' no válido")
                        continue
                    valor = float(valor_str)
                    fecha = parse_datetime(fecha_str) if fecha_str else timezone.now()

                    RegistroKPI.objects.create(
                        clinica=clinica,
                        sede=sede,
                        tipo=tipo_kpi,
                        valor=valor,
                        fecha_hora=fecha or timezone.now(),
                        periodo='dia',
                    )
                    creados += 1
                except (ValueError, KeyError) as e:
                    errores.append(f"Fila {i}: {e}")

        elif tipo == 'citas':
            for i, fila in enumerate(filas, 1):
                try:
                    medico_id = fila.get('medico_id', '').strip() or None
                    estado    = fila.get('estado', 'completada').strip()
                    ingreso   = float(fila.get('ingreso_generado', 0) or 0)
                    fecha_str = fila.get('fecha_hora_agendada', '').strip()

                    if estado not in ESTADOS_CITA_VALIDOS:
                        errores.append(f"Fila {i}: estado '{estado}' no válido")
                        continue

                    fecha = parse_datetime(fecha_str) if fecha_str else timezone.now()

                    # Necesitamos un paciente mínimo — preferir de la sede si se especificó
                    qs_pac = Paciente.objects.filter(clinica=clinica)
                    if sede:
                        qs_pac = qs_pac.filter(sede=sede)
                    paciente = qs_pac.first() or Paciente.objects.filter(clinica=clinica).first()
                    if not paciente:
                        errores.append(f"Fila {i}: no hay pacientes en la clínica para asignar")
                        continue

                    medico = None
                    if medico_id:
                        try:
                            medico = Medico.objects.get(id=int(medico_id), clinica=clinica)
                        except (Medico.DoesNotExist, ValueError):
                            errores.append(f"Fila {i}: médico {medico_id} no encontrado")
                            continue

                    if not medico:
                        qs_med = Medico.objects.filter(clinica=clinica, activo=True)
                        if sede:
                            qs_med = qs_med.filter(sede=sede)
                        medico = qs_med.first() or Medico.objects.filter(clinica=clinica, activo=True).first()
                        if not medico:
                            errores.append(f"Fila {i}: no hay médicos activos en la clínica")
                            continue

                    Cita.objects.create(
                        clinica=clinica,
                        sede=sede or medico.sede,
                        medico=medico,
                        paciente=paciente,
                        fecha_hora_agendada=fecha or timezone.now(),
                        estado=estado,
                        ingreso_generado=ingreso,
                    )
                    creados += 1
                except Exception as e:
                    errores.append(f"Fila {i}: {e}")

        # Crear SyncLog
        SyncLog.objects.create(
            integracion=integracion,
            registros_importados=creados,
            exitoso=len(errores) == 0,
            error_detalle='\n'.join(errores[:20]) if errores else '',
        )
        integracion.ultima_sync = timezone.now()
        integracion.estado = 'activa' if len(errores) == 0 else 'error'
        integracion.save()

        return Response({
            'creados': creados,
            'errores': errores[:20],
            'total_filas': len(filas),
            'tipo': tipo,
        })

    except Exception as e:
        SyncLog.objects.create(
            integracion=integracion,
            registros_importados=0,
            exitoso=False,
            error_detalle=str(e),
        )
        return Response({'error': f'Error al procesar el archivo: {e}'}, status=status.HTTP_400_BAD_REQUEST)

class SolicitudRolViewSet(viewsets.ModelViewSet):
    queryset = SolicitudRol.objects.all()
    serializer_class = SolicitudRolSerializer

    def perform_create(self, serializer):
        instance = serializer.save()
        from .tasks import enviar_email_solicitud_rol_task
        try:
            enviar_email_solicitud_rol_task.delay(instance.id)
        except Exception:
            # Celery no disponible — enviar síncronamente
            try:
                enviar_email_solicitud_rol_task(instance.id)
            except Exception:
                pass

    def get_queryset(self):
        qs = SolicitudRol.objects.select_related('usuario', 'revisada_por').all()
        clinica_id = self.request.query_params.get('clinica')
        estado = self.request.query_params.get('estado')
        usuario_id = self.request.query_params.get('usuario')
        if clinica_id:
            qs = qs.filter(usuario__clinica_id=clinica_id)
        if estado:
            qs = qs.filter(estado=estado)
        if usuario_id:
            qs = qs.filter(usuario_id=usuario_id)
        return qs.order_by('-creada_en')

    @action(detail=True, methods=['post'])
    def aprobar(self, request, pk=None):
        solicitud = self.get_object()
        if solicitud.estado != 'pendiente':
            return Response({'error': 'Solo se pueden aprobar solicitudes pendientes'}, status=status.HTTP_400_BAD_REQUEST)
        revisor_id = request.data.get('revisor_id')
        solicitud.estado = 'aprobada'
        solicitud.revisada_en = timezone.now()
        if revisor_id:
            try:
                solicitud.revisada_por = Usuario.objects.get(id=revisor_id)
            except Usuario.DoesNotExist:
                pass
        solicitud.save()
        # Apply the role change
        solicitud.usuario.rol = solicitud.rol_solicitado
        solicitud.usuario.save(update_fields=['rol'])
        return Response({'status': 'aprobada', 'nuevo_rol': solicitud.rol_solicitado})

    @action(detail=True, methods=['post'])
    def rechazar(self, request, pk=None):
        solicitud = self.get_object()
        if solicitud.estado != 'pendiente':
            return Response({'error': 'Solo se pueden rechazar solicitudes pendientes'}, status=status.HTTP_400_BAD_REQUEST)
        revisor_id = request.data.get('revisor_id')
        solicitud.estado = 'rechazada'
        solicitud.revisada_en = timezone.now()
        if revisor_id:
            try:
                solicitud.revisada_por = Usuario.objects.get(id=revisor_id)
            except Usuario.DoesNotExist:
                pass
        solicitud.save()
        return Response({'status': 'rechazada'})
