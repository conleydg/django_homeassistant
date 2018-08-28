from django.db import models
import requests
import json
from django.conf import settings


class Domain(models.Model):
    name = models.CharField(max_length=200)

    def get_available_services(self):
        return Service.objects.filter(domain=self)


class Service(models.Model):
    name = models.CharField(max_length=200)
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE)
    description = models.TextField()

    def call_service(self, data=None):
        state_url = settings.HOME_ASSISTANT_URL + 'services/' + self.domain.name + '/' + self.name
        r = requests.post(state_url, data)
        return r

    def get_fields(self):
        return Field.objects.filter(service=self)

    def __str__(self):
        return '%s: %s' % (self.name, self.description)


class Field(models.Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    entity_id = models.CharField(max_length=200)
    description = models.TextField()
    example = models.CharField(max_length=200, null=True, blank=True)
    values = models.CharField(max_length=200, null=True, blank=True)
    return_routes = models.CharField(max_length=200, null=True, blank=True)

    def __str__(self):
        return '%s: %s' % (self.entity_id, self.description)


class Entity(models.Model):
    entity_id = models.CharField(max_length=200)
    friendly_name = models.CharField(max_length=200)
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE)

    def get_state(self):
        state_url = settings.HOME_ASSISTANT_URL + 'states/' + self.entity_id
        r = requests.get(state_url)
        return r.json()

    def set_state(self, new_state):
        state_url = settings.HOME_ASSISTANT_URL + 'states/' + self.entity_id
        r = requests.post(state_url, data=json.dumps({"state": new_state}))
        return r.json()

    def get_available_services(self):
        return Service.objects.filter(domain=self.domain)

    def get_current_state(self):
        return Attribute.objects.filter(entity=self, is_current=True)


class Attribute(models.Model):
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE)
    title = models.TextField(blank=True, null=True)
    status = models.TextField(blank=True, null=True)
    is_current = models.BooleanField(default=True)
    is_old_state = models.BooleanField(default=False)
    is_new_state = models.BooleanField(default=False)

    def __str__(self):
        return '%s: %s' % (self.title, self.status)

