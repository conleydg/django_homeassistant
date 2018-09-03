from django.test import TestCase
from ha_integration.models import Domain
from ha_integration.models import Service


class TestDomainModel(TestCase):
    fixtures = [
        # "ha_integration/test_fixtures/attributes.json",
        "ha_integration/test_fixtures/domains.json",
        "ha_integration/test_fixtures/entities.json",
        "ha_integration/test_fixtures/fields.json",
        "ha_integration/test_fixtures/services.json",
    ]

    def setUp(self):
        self.home_assistant_domain = Domain.objects.get(name='homeassistant')

    def test_domain_count(self):
        domains = Domain.objects.all()
        self.assertEqual(domains.count(), 27)

    def test_domain_get_available_services(self):
        home_assistant_services = self.home_assistant_domain.services
        self.assertEqual(home_assistant_services.count(), 7)

    def test_str(self):
        self.assertEqual(str(self.home_assistant_domain), self.home_assistant_domain.name)

    # def test_service_call_service(self):
    #     services = Service.objects.all()
    #     for service in services:
    #         print(service)