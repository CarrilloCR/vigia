from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from django.core.exceptions import ValidationError
from .models import Clinica, Usuario, Sede
import re


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


def validate_password_strength(password):
    errors = []
    if len(password) < 8:
        errors.append('La contraseña debe tener al menos 8 caracteres.')
    if not re.search(r'[A-Z]', password):
        errors.append('La contraseña debe tener al menos una mayúscula.')
    if not re.search(r'[a-z]', password):
        errors.append('La contraseña debe tener al menos una minúscula.')
    if not re.search(r'\d', password):
        errors.append('La contraseña debe tener al menos un número.')
    return errors


def _user_dict(usuario_vigia):
    """Build the user dict returned by login / register / me."""
    is_superadmin = usuario_vigia.rol == 'superadmin'
    return {
        'id': usuario_vigia.id,
        'nombre': usuario_vigia.nombre,
        'email': usuario_vigia.email,
        'rol': usuario_vigia.rol,
        'clinica_id': None if is_superadmin else usuario_vigia.clinica.id,
        'clinica_nombre': None if is_superadmin else usuario_vigia.clinica.nombre,
        'sede_id': None if is_superadmin else (usuario_vigia.sede.id if usuario_vigia.sede else None),
        'sede_nombre': None if is_superadmin else (usuario_vigia.sede.nombre if usuario_vigia.sede else None),
    }


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    data = request.data

    nombre = data.get('nombre', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    nombre_clinica = data.get('nombre_clinica', '').strip()
    clinica_id = data.get('clinica_id')       # optional — join existing clinic
    sede_id = data.get('sede_id')             # optional — join existing sede

    joining = bool(clinica_id)

    if not all([nombre, email, password]):
        return Response(
            {'error': 'Nombre, email y contraseña son requeridos.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if not joining and not nombre_clinica:
        return Response(
            {'error': 'El nombre de la clínica es requerido para crear una nueva.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Validar email
    if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
        return Response({'error': 'Email inválido.'}, status=status.HTTP_400_BAD_REQUEST)

    # Validar contraseña
    password_errors = validate_password_strength(password)
    if password_errors:
        return Response({'error': ' '.join(password_errors)}, status=status.HTTP_400_BAD_REQUEST)

    # Verificar unicidad del email
    if User.objects.filter(email=email).exists():
        return Response({'error': 'Este email ya está registrado.'}, status=status.HTTP_400_BAD_REQUEST)

    if Clinica.objects.filter(email=email).exists():
        return Response({'error': 'Este email ya está registrado.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Crear usuario Django
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=nombre.split()[0],
            last_name=' '.join(nombre.split()[1:]) if len(nombre.split()) > 1 else ''
        )

        if joining:
            # ── Unirse a clínica existente ──────────────────────────────────
            try:
                clinica = Clinica.objects.get(id=clinica_id, activa=True)
            except Clinica.DoesNotExist:
                user.delete()
                return Response({'error': 'Clínica no encontrada.'}, status=status.HTTP_404_NOT_FOUND)

            sede = None
            if sede_id:
                try:
                    sede = Sede.objects.get(id=sede_id, clinica=clinica, activa=True)
                except Sede.DoesNotExist:
                    user.delete()
                    return Response({'error': 'Sede no encontrada en esa clínica.'}, status=status.HTTP_404_NOT_FOUND)

            usuario_vigia = Usuario.objects.create(
                clinica=clinica,
                sede=sede,
                nombre=nombre,
                email=email,
                password_hash=user.password,
                rol='viewer'
            )
            mensaje = 'Solicitud enviada. El administrador de la clínica revisará tu acceso.'

        else:
            # ── Crear nueva clínica ─────────────────────────────────────────
            clinica = Clinica.objects.create(
                nombre=nombre_clinica,
                email=email,
                plan='basico',
                activa=True
            )
            sede = Sede.objects.create(
                clinica=clinica,
                nombre='Sede Principal',
                activa=True
            )
            usuario_vigia = Usuario.objects.create(
                clinica=clinica,
                sede=sede,
                nombre=nombre,
                email=email,
                password_hash=user.password,
                rol='viewer'
            )
            mensaje = 'Cuenta creada. Acceso en revisión — recibirás confirmación pronto.'

        # Crear solicitud de rol admin y notificar
        from .models import SolicitudRol
        solicitud = SolicitudRol.objects.create(
            usuario=usuario_vigia,
            rol_solicitado='admin',
            motivo=f'Registro {"en" if joining else "de nueva clínica:"} {clinica.nombre}',
        )
        from .tasks import enviar_email_solicitud_rol_task
        try:
            enviar_email_solicitud_rol_task.delay(solicitud.id)
        except Exception:
            try:
                enviar_email_solicitud_rol_task(solicitud.id)
            except Exception:
                pass

        tokens = get_tokens_for_user(user)

        return Response({
            'message': mensaje,
            'tokens': tokens,
            'user': _user_dict(usuario_vigia),
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response(
            {'error': f'Error al crear la cuenta: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    email = request.data.get('email', '').strip().lower()
    password = request.data.get('password', '')

    if not email or not password:
        return Response(
            {'error': 'Email y contraseña son requeridos.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response({'error': 'Credenciales inválidas.'}, status=status.HTTP_401_UNAUTHORIZED)

    if not user.check_password(password):
        return Response({'error': 'Credenciales inválidas.'}, status=status.HTTP_401_UNAUTHORIZED)

    if not user.is_active:
        return Response({'error': 'Cuenta desactivada.'}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        usuario_vigia = Usuario.objects.select_related('clinica', 'sede').get(email=email)
    except Usuario.DoesNotExist:
        return Response({'error': 'Usuario no encontrado en el sistema.'}, status=status.HTTP_404_NOT_FOUND)

    tokens = get_tokens_for_user(user)
    return Response({'tokens': tokens, 'user': _user_dict(usuario_vigia)})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    try:
        refresh_token = request.data.get('refresh')
        token = RefreshToken(refresh_token)
        token.blacklist()
        return Response({'message': 'Sesión cerrada exitosamente.'})
    except Exception:
        return Response({'error': 'Token inválido.'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    try:
        usuario_vigia = Usuario.objects.select_related('clinica', 'sede').get(email=request.user.email)
        return Response(_user_dict(usuario_vigia))
    except Usuario.DoesNotExist:
        return Response({'error': 'Usuario no encontrado.'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def cambiar_password(request):
    password_actual = request.data.get('password_actual', '')
    password_nuevo = request.data.get('password_nuevo', '')

    if not request.user.check_password(password_actual):
        return Response(
            {'error': 'Contraseña actual incorrecta.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    errors = validate_password_strength(password_nuevo)
    if errors:
        return Response({'error': ' '.join(errors)}, status=status.HTTP_400_BAD_REQUEST)

    request.user.set_password(password_nuevo)
    request.user.save()
    return Response({'message': 'Contraseña actualizada exitosamente.'})
