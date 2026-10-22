from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from django.core.validators import MinValueValidator
from django.db import models


def photo_path(instance, filename):
    return f'products/{uuid4().hex}{Path(filename).suffix.lower()}'


class Product(models.Model):
    label = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))]
    )
    photo = models.ImageField(upload_to=photo_path, blank=True)

    class Meta:
        ordering = ['-pk']
        constraints = [
            models.CheckConstraint(condition=models.Q(price__gte=0), name='product_price_nonnegative'),
        ]

    def __str__(self):
        return self.label
