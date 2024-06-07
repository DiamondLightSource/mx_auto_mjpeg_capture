import redis
import json
import os
import numpy as np
import zmq
import pickle


class RedisClient:
    def __init__(self, host="localhost", port=6379, db=0):
        self.redis_client = redis.StrictRedis(host=host, port=port, db=db)
        self.pubsub = self.redis_client.pubsub()
        self.subscribed_channels = set()
        self.is_listening = False

    def _listen_for_messages(self):
        while True:
            message = self.pubsub.get_message()
            if message and message["type"] == "message":
                print(f"Received message: {message['data'].decode('utf-8')}")

    def _listen_and_do(self):
        while True:
            message = self.pubsub.get_message()
            if message and message["type"] == "message":
                value = json.loads(message["data"])
                uuid = value[0]["uuid"]
                image = None
                while image is None:
                    image = self.hget("test-image", uuid)
                self.murko(pickle.loads(image), uuid)

    def murko(self, image, uuid):
        print("inside murko")
        request_arguments = {}
        model_img_size = (256, 320)
        request_arguments["to_predict"] = np.array(image)
        request_arguments["model_img_size"] = model_img_size
        request_arguments["save"] = False
        request_arguments["min_size"] = 64
        request_arguments["description"] = [
            "foreground",
            "crystal",
            "loop_inside",
            "loop",
            ["crystal", "loop"],
            ["crystal", "loop", "stem"],
        ]
        request_arguments["prefix"] = uuid

        print(f"after request_arguments for: {request_arguments['prefix']}")
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.connect("tcp://ws561.diamond.ac.uk:8008")
        socket.send(pickle.dumps(request_arguments))
        raw_predictions = socket.recv()
        predictions = pickle.loads(raw_predictions)
        # print(predictions)
        print(
            f"made a prediction, most likely click is: {predictions['descriptions'][0]['most_likely_click']}"
        )

    def set(self, key, value):
        self.redis_client.expire(key, 3600)
        self.redis_client.set(key, value)

    def get(self, key):
        return self.redis_client.get(key)

    def publish(self, channel, message):
        self.redis_client.publish(channel, message)

    def subscribe(self, channel):
        if channel not in self.subscribed_channels:
            self.pubsub.subscribe(channel)
            self.subscribed_channels.add(channel)
            print(f"Subscribed to channel: {channel}")
            if not self.is_listening:
                self.is_listening = True
                self._listen_for_messages()
        else:
            print(f"Already subscribed to channel: {channel}")

    def get_images(self, channel):
        if channel not in self.subscribed_channels:
            self.pubsub.subscribe(channel)
            self.subscribed_channels.add(channel)
            if not self.is_listening:
                self.is_listening = True
                self._listen_and_do()
        else:
            print(f"Already subscribed to channel: {channel}")

    def unsubscribe(self, channel):
        if channel in self.subscribed_channels:
            self.pubsub.unsubscribe(channel)
            self.subscribed_channels.remove(channel)
            print(f"Unsubscribed from channel: {channel}")
        else:
            print(f"Not subscribed to channel: {channel}")

    def hset(self, key, field, value):
        self.redis_client.hset(key, field, value)

    def hget(self, key, field):
        return self.redis_client.hget(key, field)

    def hkeys(self, key):
        return self.redis_client.hkeys(key)

    def hgetall(self, key):
        return self.redis_client.hgetall(key)

    def hdel(self, key, *fields):
        self.redis_client.hdel(key, *fields)

    def close(self):
        self.redis_client.close()


if __name__ == "__main__":
    import pickle

    client = RedisClient(host="ws561.diamond.ac.uk")
    # image = pickle.loads(client.get("image"))

    # Set and get example
    # metadata = "{'metadata':[{'omega_angle': 999.996},{'zoom_percentage':44.02},{'microns_per_x_pixel':0.944},{'microns_per_y_pixel':0.944},{'beam_centre_i':260},{'beam_centre_j':396}]}"
    # client.publish("murko",metadata)
    # print(client.get("murko"))

    # Publish/Subscribe example
    client.get_images("murko")
    # Run this in another terminal: redis-cli PUBLISH murko "metadata available!"

    # Hash example
    # client.hset('murko:123', 'metadata', metadata)
    # client.hset('murko:123', 'image', pickle.dumps(image))
#    print(client.hgetall('metadata'))
#    print(client.hget('metadata','4d0e18b5-c0b3-45e6-9aa9-480d006fb79d'))

# print(client.hkeys('test-image'))
# print(pickle.loads(client.hget('test-image', '2d21b7e8-8358-4d11-97b2-434c17c64dfc')))


#    print(client.set('images':pickle.dumps(np.array)))
# print(pickle.loads(client.hget('murko:123','image')))
