import factory
from django.contrib.auth.hashers import make_password

from apps.users.models import User


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.Sequence(lambda n: f"user{n}@example.com")
    full_name = factory.Faker("name")
    password = factory.LazyFunction(lambda: make_password("testpass123"))
    role = "general"
    is_email_verified = False
    is_active = True

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        kwargs.pop("password", None)
        manager = cls._get_manager(model_class)
        return manager.create_user("testpass123", *args, **kwargs)
