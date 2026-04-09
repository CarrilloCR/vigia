from django.db import models


class Clinica(models.Model):
    nombre = models.CharField(max_length=200)
    direccion = models.CharField(max_length=300, blank=True)
    telefono = models.CharField(max_length=20, blank=True)
    email = models.EmailField(unique=True)
    plan = models.CharField(max_length=20, choices=[
        ('basico', 'Básico'),
        ('profesional', 'Profesional'),
        ('enterprise', 'Enterprise'),
    ], default='basico')
    activa = models.BooleanField(default=True)
    creada_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre


class Sede(models.Model):
    clinica = models.ForeignKey(Clinica, on_delete=models.CASCADE, related_name='sedes')
    nombre = models.CharField(max_length=200)
    direccion = models.CharField(max_length=300, blank=True)
    telefono = models.CharField(max_length=20, blank=True)
    activa = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.clinica} - {self.nombre}"


class Usuario(models.Model):
    ROL_CHOICES = [
        ('admin', 'Administrador'),
        ('viewer', 'Visualizador'),
    ]
    clinica = models.ForeignKey(Clinica, on_delete=models.CASCADE, related_name='usuarios')
    sede = models.ForeignKey(Sede, on_delete=models.SET_NULL, null=True, blank=True, related_name='usuarios')
    nombre = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    password_hash = models.CharField(max_length=255)
    rol = models.CharField(max_length=20, choices=ROL_CHOICES, default='admin')
    ultimo_acceso = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.nombre} ({self.clinica})"


class Medico(models.Model):
    clinica = models.ForeignKey(Clinica, on_delete=models.CASCADE, related_name='medicos')
    sede = models.ForeignKey(Sede, on_delete=models.SET_NULL, null=True, blank=True, related_name='medicos')
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    especialidad = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    telefono = models.CharField(max_length=20, blank=True)
    descripcion = models.TextField(blank=True)
    foto_url = models.TextField(blank=True)
    fecha_ingreso = models.DateField(null=True, blank=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"Dr. {self.nombre} {self.apellido}"


class Paciente(models.Model):
    clinica = models.ForeignKey(Clinica, on_delete=models.CASCADE, related_name='pacientes')
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    fecha_nacimiento = models.DateField(null=True, blank=True)
    telefono = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    primera_visita = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombre} {self.apellido}"


class Cita(models.Model):
    ESTADO_CHOICES = [
        ('agendada', 'Agendada'),
        ('completada', 'Completada'),
        ('cancelada', 'Cancelada'),
        ('no_show', 'No Show'),
        ('reagendada', 'Reagendada'),
    ]
    clinica = models.ForeignKey(Clinica, on_delete=models.CASCADE, related_name='citas')
    sede = models.ForeignKey(Sede, on_delete=models.SET_NULL, null=True, blank=True, related_name='citas')
    medico = models.ForeignKey(Medico, on_delete=models.CASCADE, related_name='citas')
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE, related_name='citas')
    fecha_hora_agendada = models.DateTimeField()
    fecha_hora_real = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='agendada')
    motivo_cancelacion = models.TextField(blank=True)
    ingreso_generado = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    creada_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.paciente} con {self.medico} - {self.fecha_hora_agendada}"


class Encuesta(models.Model):
    cita = models.OneToOneField(Cita, on_delete=models.CASCADE, related_name='encuesta')
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE, related_name='encuestas')
    puntuacion = models.IntegerField()
    comentario = models.TextField(blank=True)
    respondida_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Encuesta cita {self.cita.id} - {self.puntuacion}/10"


class RegistroKPI(models.Model):
    TIPO_KPI = [
        ('tasa_cancelacion', 'Tasa de Cancelación'),
        ('tasa_noshow', 'Tasa de No Show'),
        ('ocupacion_agenda', 'Ocupación de Agenda'),
        ('tiempo_espera', 'Tiempo Promedio de Espera'),
        ('ingresos_dia', 'Ingresos por Día'),
        ('ticket_promedio', 'Ticket Promedio'),
        ('pacientes_nuevos', 'Pacientes Nuevos vs Recurrentes'),
        ('retencion_90', 'Retención a 90 Días'),
        ('cancelaciones_medico', 'Cancelaciones por Médico'),
        ('citas_reagendadas', 'Citas Reagendadas'),
        ('nps', 'Net Promoter Score'),
    ]
    clinica = models.ForeignKey(Clinica, on_delete=models.CASCADE, related_name='kpis')
    sede = models.ForeignKey(Sede, on_delete=models.SET_NULL, null=True, blank=True, related_name='kpis')
    medico = models.ForeignKey(Medico, on_delete=models.SET_NULL, null=True, blank=True, related_name='kpis')
    tipo = models.CharField(max_length=50, choices=TIPO_KPI)
    valor = models.FloatField()
    fecha_hora = models.DateTimeField(auto_now_add=True)
    periodo = models.CharField(max_length=10, choices=[
        ('dia', 'Día'),
        ('semana', 'Semana'),
        ('mes', 'Mes'),
    ], default='dia')

    def __str__(self):
        return f"{self.tipo} - {self.clinica} - {self.fecha_hora}"


class Alerta(models.Model):
    SEVERIDAD_CHOICES = [
        ('baja', 'Baja'),
        ('media', 'Media'),
        ('alta', 'Alta'),
        ('critica', 'Crítica'),
    ]
    ESTADO_CHOICES = [
        ('activa', 'Activa'),
        ('revisada', 'Revisada'),
        ('resuelta', 'Resuelta'),
    ]
    clinica = models.ForeignKey(Clinica, on_delete=models.CASCADE, related_name='alertas')
    sede = models.ForeignKey(Sede, on_delete=models.SET_NULL, null=True, blank=True, related_name='alertas')
    medico = models.ForeignKey(Medico, on_delete=models.SET_NULL, null=True, blank=True, related_name='alertas')
    tipo_kpi = models.CharField(max_length=50)
    valor_detectado = models.FloatField()
    valor_esperado = models.FloatField()
    desviacion = models.FloatField()
    severidad = models.CharField(max_length=10, choices=SEVERIDAD_CHOICES, default='media')
    mensaje = models.TextField()
    recomendacion = models.TextField(blank=True)
    metodo_deteccion = models.CharField(max_length=50, default='estadistico', help_text='Metodo que detecto la anomalia: estadistico, prophet, pyod, ensemble:...')
    detalle_deteccion = models.JSONField(default=dict, blank=True, help_text='Resultados individuales de cada método de detección')
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='activa')
    creada_en = models.DateTimeField(auto_now_add=True)
    revisada_en = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.severidad.upper()} - {self.tipo_kpi} - {self.clinica}"


class Notificacion(models.Model):
    CANAL_CHOICES = [
        ('email', 'Email'),
        ('whatsapp', 'WhatsApp'),
        ('sms', 'SMS'),
    ]
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('enviada', 'Enviada'),
        ('entregada', 'Entregada'),
        ('leida', 'Leída'),
        ('fallida', 'Fallida'),
    ]
    alerta = models.ForeignKey(Alerta, on_delete=models.CASCADE, related_name='notificaciones')
    usuario = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name='notificaciones')
    canal = models.CharField(max_length=20, choices=CANAL_CHOICES)
    destinatario = models.CharField(max_length=200)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    enviada_en = models.DateTimeField(null=True, blank=True)
    leida_en = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.canal} - {self.alerta} - {self.estado}"


class FeedbackAlerta(models.Model):
    alerta = models.ForeignKey(Alerta, on_delete=models.CASCADE, related_name='feedbacks')
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='feedbacks')
    fue_util = models.BooleanField()
    comentario = models.TextField(blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback {'útil' if self.fue_util else 'no útil'} - {self.alerta}"


class ConfiguracionAlerta(models.Model):
    clinica = models.ForeignKey(Clinica, on_delete=models.CASCADE, related_name='configuraciones')
    tipo_kpi = models.CharField(max_length=50)
    canal = models.CharField(max_length=20, choices=[
        ('email', 'Email'),
        ('whatsapp', 'WhatsApp'),
    ], default='email')
    umbral_sensibilidad = models.FloatField(default=20.0)
    activa = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.clinica} - {self.tipo_kpi}"


class IntegracionExterna(models.Model):
    TIPO_CHOICES = [
        ('doctoralia', 'Doctoralia'),
        ('odoo', 'Odoo'),
        ('hubspot', 'HubSpot'),
        ('salesforce', 'Salesforce'),
        ('csv', 'CSV Manual'),
    ]
    ESTADO_CHOICES = [
        ('activa', 'Activa'),
        ('inactiva', 'Inactiva'),
        ('error', 'Error'),
    ]
    clinica = models.ForeignKey(Clinica, on_delete=models.CASCADE, related_name='integraciones')
    tipo = models.CharField(max_length=50, choices=TIPO_CHOICES)
    nombre = models.CharField(max_length=200)
    api_key = models.CharField(max_length=500, blank=True)
    api_url = models.CharField(max_length=500, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='activa')
    ultima_sync = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.tipo} - {self.clinica}"


class SyncLog(models.Model):
    integracion = models.ForeignKey(IntegracionExterna, on_delete=models.CASCADE, related_name='logs')
    ejecutado_en = models.DateTimeField(auto_now_add=True)
    registros_importados = models.IntegerField(default=0)
    exitoso = models.BooleanField(default=True)
    error_detalle = models.TextField(blank=True)

    def __str__(self):
        return f"Sync {self.integracion} - {'OK' if self.exitoso else 'ERROR'} - {self.ejecutado_en}"


class PlanFacturacion(models.Model):
    ESTADO_CHOICES = [
        ('activo', 'Activo'),
        ('vencido', 'Vencido'),
        ('cancelado', 'Cancelado'),
        ('prueba', 'Prueba'),
    ]
    clinica = models.OneToOneField(Clinica, on_delete=models.CASCADE, related_name='plan_facturacion')
    plan = models.CharField(max_length=20, choices=[
        ('basico', 'Básico'),
        ('profesional', 'Profesional'),
        ('enterprise', 'Enterprise'),
    ])
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    moneda = models.CharField(max_length=10, default='USD')
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='prueba')
    fecha_inicio = models.DateField()
    fecha_renovacion = models.DateField()
    creado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.clinica} - {self.plan} - {self.estado}"


class EmailNotificacion(models.Model):
    clinica = models.ForeignKey(Clinica, on_delete=models.CASCADE, related_name='emails_notificacion')
    email = models.EmailField()
    nombre = models.CharField(max_length=100, blank=True)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['clinica', 'email']

    def __str__(self):
        return f"{self.email} - {self.clinica.nombre}"