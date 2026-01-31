# tests.py - Ejemplo básico
from django.test import TestCase
from .models import Lote, Almacen
from django.contrib.auth.models import User

class LoteTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser', 
            password='testpass123'
        )
    
    def test_crear_lote(self):
        lote = Lote.objects.create(
            codigo="TEST-001",
            nombre="Lote de prueba",
            cantidad_objetivo=100,
            creado_por=self.user
        )
        self.assertEqual(lote.estado, 'planeado')