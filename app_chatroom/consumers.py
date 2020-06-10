from channels.generic.websocket import AsyncWebsocketConsumer
import json
class Chatting(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_group_name = 'xiaoyuanqujing'
        # 加入聊天室
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # 离开聊天室
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # 通过WebSocket，接收数据
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']
        print(message)
        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message
            }
        )

    # Receive message from room group
    async def chat_message(self, event):
        message = '匿名用户：' + event['message']
        print('返回')
        # 通过WebSocket发送
        await self.send(text_data=json.dumps({
            'message': message
        }))