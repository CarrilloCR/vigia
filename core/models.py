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


class Medico(models.Model):
    clinica = models.ForeignKey(Clinica, on_delete=models.CASCADE, related_name='medicos')
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    especialidad = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
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
    ]

    clinica = models.ForeignKey(Clinica, on_delete=models.CASCADE, related_name='kpis')
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
    medico = models.ForeignKey(Medico, on_delete=models.SET_NULL, null=True, blank=True, related_name='alertas')
    tipo_kpi = models.CharField(max_length=50)
    valor_detectado = models.FloatField()
    valor_esperado = models.FloatField()
    desviacion = models.FloatField()
    severidad = models.CharField(max_length=10, choices=SEVERIDAD_CHOICES, default='media')
    mensaje = models.TextField()
    recomendacion = models.TextField(blank=True)
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='activa')
    creada_en = models.DateTimeField(auto_now_add=True)
    revisada_en = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.severidad.upper()} - {self.tipo_kpi} - {self.clinica}"


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