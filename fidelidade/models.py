from django.db import models
import json

class LoyaltyCard(models.Model):
    id_code = models.CharField(max_length=50, unique=True, verbose_name="ID do Cartão")
    customer_name = models.CharField(max_length=100, blank=True, verbose_name="Nome do Cliente")
    customer_phone = models.CharField(max_length=20, blank=True, verbose_name="WhatsApp")
    stamps = models.PositiveIntegerField(default=0, verbose_name="Quantidade de Selos")
    # New field to store JSON list of {x, y} coordinates for current cycle stamps
    stamp_positions = models.TextField(default="[]", verbose_name="Posições dos Selos (JSON)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cartão Fidelidade"
        verbose_name_plural = "Cartões Fidelidade"

    def __str__(self):
        return f"{self.id_code} - {self.customer_name or 'Sem Nome'}"

    @property
    def current_cycle_stamps(self):
        """Quantos selos no ciclo atual (0 a 6). No 7º o cliente ganha."""
        return self.stamps % 7

    @property
    def reward_count(self):
        """Total de recompensas conquistadas."""
        return self.stamps // 7

    def get_positions(self):
        try:
            return json.loads(self.stamp_positions)
        except:
            return []

    def add_stamp_pos(self, x, y):
        positions = self.get_positions()
        positions.append({'x': x, 'y': y})
        self.stamp_positions = json.dumps(positions)
        self.stamps += 1
        self.save()

    def remove_last_stamp(self):
        positions = self.get_positions()
        if positions:
            positions.pop()
            self.stamp_positions = json.dumps(positions)
            if self.stamps > 0:
                self.stamps -= 1
            self.save()
        elif self.stamps > 0:
            # Fallback for old cards or reward-only removals
            self.stamps -= 1
            self.save()
