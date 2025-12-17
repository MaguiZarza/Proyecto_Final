from django.db import models
from decimal import Decimal, ROUND_CEILING

print(">>> MODELS CALCULADORA CARGADOS <<<")

# Configuraciones pre-calculo
class TipoMaquina(models.TextChoices):
    RECTA = 'RECTA', 'Recta'
    OVERLOCK = 'OVERLOCK', 'Overlock'
    COLLARETA = 'COLLARETA', 'Collareta'

class TipoHilo(models.TextChoices):
    ALGODON = 'ALGODON', 'Algodón'
    POLIESTER = 'POLIESTER', 'Poliéster'

class Hilo(models.Model):
    tipo = models.CharField(max_length=20, choices=TipoHilo.choices)
    nombre = models.CharField(max_length=100)
    metros_por_cono = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.nombre} ({self.tipo})"
    
class Tela(models.Model):
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return self.nombre

# Tipo de maquina e hilos
class ConfiguracionMaquina(models.Model):
    nombre = models.CharField(max_length=100)

    tipo_maquina = models.CharField(
        max_length=20,
        choices=TipoMaquina.choices
    )

    def __str__(self):
        return f"{self.nombre} ({self.tipo_maquina})"

class ConfiguracionHilo(models.Model):
    configuracion = models.ForeignKey(
        ConfiguracionMaquina,
        related_name='hilos',
        on_delete=models.CASCADE
    )

    tipo_hilo = models.CharField(
        max_length=20,
        choices=TipoHilo.choices
    )

    cantidad_conos = models.PositiveIntegerField()

    class Meta:
        unique_together = ('configuracion', 'tipo_hilo')

    def __str__(self):
        return f"{self.tipo_hilo}: {self.cantidad_conos} conos"

# Calculo tela x hilo
class ConsumoTela(models.Model):
    tela = models.ForeignKey(Tela, on_delete=models.CASCADE)
    configuracion = models.ForeignKey(
        ConfiguracionMaquina,
        on_delete=models.CASCADE
    )
    metros_hilo_por_metro_tela = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    def calcular_consumo(self, metros_tela):
        consumo_total = Decimal(metros_tela) * self.metros_hilo_por_metro_tela

        hilos = self.configuracion.hilos.all()
        total_conos = sum(Decimal(h.cantidad_conos) for h in hilos)

        if total_conos == 0:
            return {}

        resultado = {}

        for h in hilos:
            proporcion = Decimal(h.cantidad_conos) / total_conos
            metros_hilo = consumo_total * proporcion

            hilo = Hilo.objects.get(tipo=h.tipo_hilo)

            conos_reales = metros_hilo / Decimal(hilo.metros_por_cono)
            conos_redondeados = conos_reales.to_integral_value(
                rounding=ROUND_CEILING
            )

            resultado[h.tipo_hilo] = {
                'metros_hilo': metros_hilo.quantize(Decimal('0.01')),
                'conos': conos_reales.quantize(Decimal('0.01')),
                'conos_redondeados': int(conos_redondeados)
            }

        return resultado

class Material(models.Model):
    TIPO_CHOICES = [
        ('tela', 'Tela'),
        ('hilo', 'Hilo'),
        ('avios', 'Avíos'),
        ('otro', 'Otro'),
    ]

    nombre = models.CharField(max_length=100)
    unidad = models.CharField(max_length=20)
    tipo = models.CharField(
        max_length=20,
        choices=TIPO_CHOICES,
        default='hilo'
    )
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    nombre = models.CharField(max_length=100)
    codigo = models.CharField(max_length=50, unique=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre


class Formula(models.Model):
    producto = models.OneToOneField(
        Producto,
        on_delete=models.CASCADE
    )
    activa = models.BooleanField(default=True)

    def __str__(self):
        return f"Fórmula - {self.producto.nombre}"


class FormulaDetalle(models.Model):
    formula = models.ForeignKey(
        Formula,
        on_delete=models.CASCADE,
        related_name='detalles'
    )
    material = models.ForeignKey(
        Material,
        on_delete=models.PROTECT
    )
    cantidad_por_unidad = models.DecimalField(
        max_digits=10,
        decimal_places=3
    )

    def __str__(self):
        return self.material.nombre

# # Calculadora de materiales:
# class Material(models.Model):
#     TIPO_CHOICES = [
#         ('tela', 'Tela'),
#         ('hilo', 'Hilo'),
#         ('avios', 'Avíos'),
#         ('otro', 'Otro'),
#     ]

#     nombre = models.CharField(max_length=100)
#     unidad = models.CharField(max_length=20)

#     tipo = models.CharField(
#         max_length=20,
#         choices=TIPO_CHOICES,
#         default='otro'
#     )

#     activo = models.BooleanField(default=True)

#     def __str__(self):
#         return f"{self.nombre} ({self.unidad})"



# # PRODUCTOS
# class Producto(models.Model):
#     nombre = models.CharField(max_length=100)

#     codigo = models.CharField(
#         max_length=50,
#         unique=True,
#         null=True,
#         blank=True
#     )

#     activo = models.BooleanField(default=True)

#     def __str__(self):
#         return self.nombre


# # =========================
# # FÓRMULA (CABECERA)
# # =========================
# class Formula(models.Model):
#     producto = models.OneToOneField(
#         Producto,
#         on_delete=models.CASCADE,
#         null=True,
#         blank=True
#     )

#     activa = models.BooleanField(default=True)

#     def __str__(self):
#         if self.producto:
#             return f"Fórmula - {self.producto.nombre}"
#         return "Fórmula sin producto"


# # FÓRMULA DETALLE
# class FormulaDetalle(models.Model):
#     formula = models.ForeignKey(
#         Formula,
#         on_delete=models.CASCADE,
#         related_name='detalles'
#     )

#     material = models.ForeignKey(
#         Material,
#         on_delete=models.PROTECT
#     )

#     cantidad_por_unidad = models.DecimalField(
#         max_digits=10,
#         decimal_places=3
#     )

#     def __str__(self):
#         return self.material.nombre