import json
from channels.generic.websocket import AsyncWebsocketConsumer

class StoreStatusConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Todos os clientes entrarão neste grupo global
        self.group_name = 'store_status_group'

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()
        # Enviaremos o status atual logo na conexão ou podemos deixar o front pedir/buscar via fetch 
        # e o ws só receber as atualizações. 
        # Como o frontend já faz um fetch inicial no carregamento ou logo no script, o ws só precisa das atualizações.

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    # Receive message from room group
    async def store_status_update(self, event):
        # O dicionário 'event' já é praticamente os dados que queremos enviar,
        # só precisamos remover a chave 'type' se necessário, ou enviar o event inteiro (o front ignora o type)
        # Como o envio no models.py coloca os dados diretamente na raiz do dicionário, o event É o data.
        
        # Copiamos o event para evitar modificar o original
        data = event.copy()
        
        # Removemos o 'type' opcionalmente, mas nem precisa pois no JS nós pegamos as chaves diretas
        if 'type' in data:
            del data['type']

        # Send message to WebSocket
        await self.send(text_data=json.dumps(data))
