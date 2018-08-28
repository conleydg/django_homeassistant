import os
import json
import asyncio
import asyncws
import django
import requests
from pandas.io.json import json_normalize

os.environ["DJANGO_SETTINGS_MODULE"] = 'home.settings'
django.setup()


from ha_integration.models import Attribute
from ha_integration.models import Domain
from ha_integration.models import Entity
from ha_integration.models import Field
from ha_integration.models import Service
from django.conf import settings



def get_services():
    """ Gets and Saves all Domains and Services from Home Assistant API"""
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



def get_states():
    r = requests.get(settings.HOME_ASSISTANT_API_URL + 'states')
    states = r.json()
    df = json_normalize(states)
    for index, row in df.iterrows():
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
            print(index, value)


get_services()
get_states()


@asyncio.coroutine
def echo():
    websocket = yield from asyncws.connect(settings.HOME_ASSISTANT_WS_URL)

    yield from websocket.send(json.dumps(
        {'id': 1, 'type': 'subscribe_events', 'event_type': 'state_changed'}))

    while True:
        message = yield from websocket.recv()
        if message is None:
            break
        message = json.loads(message)
        df = json_normalize(message)
        if df.type[0] == 'event':
            for index, row in df.iterrows():
                entity_id = row['event.data.entity_id']
                domain_name, _ = entity_id.split(".")
                domain, created = Domain.objects.get_or_create(name=domain_name)
                friendly_name = ''
                if hasattr(row, 'event.data.new_state.attributes.friendly_name '):
                    friendly_name = row['event.data.new_state.attributes.friendly_name']
                entity, _ = Entity.objects.update_or_create(
                    entity_id=entity_id,
                    domain=domain,
                    defaults={
                        'friendly_name': friendly_name,
                    }
                )
                Attribute.objects.filter(entity=entity).update(is_current=False)
                for index, value in df.iteritems():
                    print(index)
                    new_state = False
                    old_state = False
                    is_current = False
                    if 'new_state' in index:
                        new_state = True
                        is_current = True
                        title = index.split('new_state.')[1]
                    elif 'old_state' in index:
                        old_state = True
                        title = index.split('old_state.')[1]
                    elif 'event' in index:
                        title = index.split('event.')[1]
                    Attribute.objects.create(
                        entity=entity,
                        title=title,
                        status=str(value[0]),
                        is_current=is_current,
                        is_old_state=old_state,
                        is_new_state=new_state,
                    )


asyncio.get_event_loop().run_until_complete(echo())
asyncio.get_event_loop().close()
