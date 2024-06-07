import json
import redis.asyncio as redis
import asyncio
from bluesky.protocols import Triggerable
from ophyd_async.core import StandardReadable
from ophyd_async.core.async_status import AsyncStatus

from dodal.devices.ophyd_async_utils import create_soft_signal_rw


class RedisClient(StandardReadable, Triggerable):
    def __init__(self, host="localhost", port=6379, db=0):
        self.redis_client = redis.StrictRedis(host=host, port=port, db=db)        
        self.subscribed_channels = set()
        self.is_listening = False
        self.x = create_soft_signal_rw(float, "x", self.name)
        self.y = create_soft_signal_rw(float, "y", self.name)
        self.microns_per_x_pixel = create_soft_signal_rw(float, "microns_per_x_pixel", self.name)
        self.microns_per_y_pixel = create_soft_signal_rw(float, "microns_per_y_pixel", self.name)
        self.set_readable_signals(
            read=[
                self.x, 
                self.y,
                self.microns_per_x_pixel,
                self.microns_per_y_pixel,
                ]
        )
    
    async def _listen_and_do(self, pubsub):
        while True:
            message = await pubsub.get_message()
            await asyncio.sleep(0.1)
            if message and message["type"] == "message":
                value = json.loads(message["data"])
                print(f'UUID: {value[0]["uuid"]}')
                await self.x.set(value[0]["x_pixel_coord"])
                await self.y.set(value[0]["y_pixel_coord"])
                metadata = None
                while metadata is None:
                    metadata = await self.hget("test-metadata", value[0]["uuid"])
                    metadata = json.loads(metadata)
                    print(metadata)
                    await self.microns_per_x_pixel.set(metadata["microns_per_x_pixel"])
                    await self.microns_per_y_pixel.set(metadata["microns_per_y_pixel"])
                    break
                break   

    async def hget(self, key, field):
        return await self.redis_client.hget(key, field)

    @AsyncStatus.wrap
    async def trigger(self):
        channel = "murko-results"
        async with self.redis_client.pubsub() as pubsub:
             await pubsub.subscribe(channel)
             self.subscribed_channels.add(channel)
             print(f"Subscribed to channel: {channel}")
             await self._listen_and_do(pubsub)

