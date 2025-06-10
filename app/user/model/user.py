from tortoise.models import Model
from tortoise import fields

class User(Model):
    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=100)
    email = fields.CharField(max_length=100, unique=True)
    is_active = fields.BooleanField(default=True)
    first_name = fields.CharField(max_length=100)
    last_name = fields.CharField(max_length=100)


    class Meta:
        table = "users"