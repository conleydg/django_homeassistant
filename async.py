import os
import json
import asyncio
import asyncws
import django
from pandas.io.json import json_normalize

os.environ["DJANGO_SETTINGS_MODULE"] = 'home.settings'
django.setup()


from ha_integration.models import Attribute
from ha_integration.models import Domain
from ha_integration.models import Entity
from django.conf import settings


@asyncio.coroutine
def echo():
    """ Connect to Home Assistant Websocket and save all messages """
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
            for _, row in df.iterrows():
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
                    new_state = False
                    old_state = False
                    is_current = False
                    title = ''
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
