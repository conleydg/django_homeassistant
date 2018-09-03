from django.db import models
import requests
import json
from django.conf import settings
from pandas.io.json import json_normalize


class Domain(models.Model):
    """ Represents Home Assistant Domains

    Domains are the highest level object in Home Assistant. Each domain
    has related services.  Z-Wave is an example of a domain, and 'add_node'
    is an example of a related service.

    Public Attributes:
    - name: (string)
    - services: property method that returns related services
    """
    name = models.CharField(max_length=200)

    @property
    def services(self):
        return Service.objects.filter(domain=self)

    def __str__(self):
        return '%s' % self.name


class Service(models.Model):
    """ Represents Home Assistant Services

    Public Attributes:

    """
    name = models.CharField(max_length=200)
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE)
    description = models.TextField()

    def call_service(self, data=None):
        state_url = settings.HOME_ASSISTANT_URL + 'services/' + self.domain.name + '/' + self.name
        r = requests.post(state_url, data)
        return r

    @property
    def fields(self):
        return Field.objects.filter(service=self)

    @classmethod
    def get_services(cls):
        """ Gets and Saves all Domains and Services from Home Assistant API """
        r = requests.get(settings.HOME_ASSISTANT_API_URL + 'services')
        services = r.json()
        for service in services:
            domain, created = Domain.objects.get_or_create(name=service['domain'])
            for key, value in service['services'].items():
                service, created = Service.objects.get_or_create(
                    name=key,
                    domain=domain,
                    description=value['description']
                )
                if 'fields' in value and value['fields']:
                    for entity, details in value['fields'].items():
                        example = ''
                        values = ''
                        return_routes = ''
                        if isinstance(details, dict):
                            description = details['description']
                            if 'example' in details:
                                example = str(details['example'])
                            if 'values' in details:
                                values = str(details['values'])
                            if 'return_routes' in details:
                                return_routes = str(details['return_routes'])
                        else:
                            description = str(details)
                        Field.objects.get_or_create(
                            service=service,
                            entity_id=entity,
                            description=description,
                            example=example,
                            values=values,
                            return_routes=return_routes,
                        )

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

    @classmethod
    def get_states(cls):
        """ Gets all states then saves entity and attributes """
        r = requests.get(settings.HOME_ASSISTANT_API_URL + 'states')
        states = r.json()
        df = json_normalize(states)
        for _, row in df.iterrows():
            non_null_attributes = row.dropna()
            entity_id = non_null_attributes.entity_id
            domain_name, _ = entity_id.split(".")
            domain, created = Domain.objects.get_or_create(name=domain_name)
            friendly_name = ''
            if hasattr(non_null_attributes, 'attributes.friendly_name'):
                friendly_name = non_null_attributes['attributes.friendly_name']
            entity, _ = Entity.objects.update_or_create(
                entity_id=entity_id,
                domain=domain,
                defaults={
                    'friendly_name': friendly_name,
                }
            )
            Attribute.objects.filter(entity=entity).update(is_current=False)
            for index, value in non_null_attributes.iteritems():
                Attribute.objects.create(
                    entity=entity,
                    title=index,
                    status=str(value),
                    is_current=True,
                    is_old_state=False,
                    is_new_state=False,
                )


class Attribute(models.Model):
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE)
    title = models.TextField(blank=True, null=True)
    status = models.TextField(blank=True, null=True)
    is_current = models.BooleanField(default=True)
    is_old_state = models.BooleanField(default=False)
    is_new_state = models.BooleanField(default=False)

    def __str__(self):
        return '%s: %s' % (self.title, self.status)

