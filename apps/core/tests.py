import pytest
from django.utils import timezone
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory

from apps.common.exceptions import custom_exception_handler
from apps.common.pagination import StandardResultsPagination
from apps.common.responses import success_response
from apps.core.models import ConcreteTestModel


@pytest.mark.django_db
def test_timestamped_and_soft_delete_model():
    # Test creation
    instance = ConcreteTestModel.objects.create(name="Test Item")
    assert instance.created_at is not None
    assert instance.updated_at is not None
    assert not instance.is_deleted
    assert instance.deleted_at is None

    # Test soft delete
    instance.soft_delete()
    instance.refresh_from_db()
    assert instance.is_deleted
    assert instance.deleted_at is not None
    last_deleted_at = instance.deleted_at

    # Test restore
    instance.restore()
    instance.refresh_from_db()
    assert not instance.is_deleted
    assert instance.deleted_at is None


def test_success_response():
    data = {"foo": "bar"}
    response = success_response(data=data, message="Operation Succeeded", status=201)

    assert isinstance(response, Response)
    assert response.status_code == 201
    assert response.data["success"] is True
    assert response.data["message"] == "Operation Succeeded"
    assert response.data["data"] == data


def test_custom_exception_handler():
    # Trigger a validation error
    exc = exceptions.ValidationError(detail="Invalid input data")
    context = {"request": APIRequestFactory().get("/")}

    response = custom_exception_handler(exc, context)

    assert response is not None
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["success"] is False
    assert "error" in response.data
    assert response.data["status_code"] == status.HTTP_400_BAD_REQUEST


def test_custom_exception_handler_none():
    # If it is a non-DRF exception (e.g. ValueError), standard exception_handler returns None
    exc = ValueError("A python error")
    context = {"request": APIRequestFactory().get("/")}

    response = custom_exception_handler(exc, context)
    assert response is None


def test_standard_pagination():
    paginator = StandardResultsPagination()
    assert paginator.page_size == 20
    assert paginator.page_size_query_param == "page_size"
    assert paginator.max_page_size == 100
