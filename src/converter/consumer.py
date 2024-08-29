import pika
import sys
import os
import time
from pymongo import MongoClient
import gridfs
from convert import to_mp3
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    logger.debug("main method called")
    try:
        client = MongoClient("mongodb://mongodb:27017/")
        db_videos = client.videos
        db_mp3s = client.mp3s
        # gridfs
        logger.debug("gridfs code")

        fs_videos = gridfs.GridFS(db_videos)
        fs_mp3s = gridfs.GridFS(db_mp3s)

        logger.debug("rabbitmq connection")
        # rabbitmq connection
        connection = pika.BlockingConnection(pika.ConnectionParameters(host="rabbitmq"))
        channel = connection.channel()

        def callback(ch, method, properties, body):
            logger.debug("callback method")
            """
            Handles incoming messages from the RabbitMQ queue.

            Parameters:
                ch (pika.channel.Channel): The RabbitMQ channel.
                method (pika.frame.Method): The method frame.
                properties (pika.spec.BasicProperties): The message properties.
                body (bytes): The message body.

            Returns:
                None
            """
            logger.info("Received message from queue")
            try:
                err = to_mp3.start(body, fs_videos, fs_mp3s, ch)
                if err:
                    logger.error("Error processing message: {}".format(err))
                    ch.basic_nack(delivery_tag=method.delivery_tag)
                else:
                    logger.info("Message processed successfully")
                    ch.basic_ack(delivery_tag=method.delivery_tag)
            except Exception as e:
                logger.error("Error processing message: {}".format(e))

        channel.basic_consume(
            queue=os.environ.get("VIDEO_QUEUE"), on_message_callback=callback
        )

        logger.info("Waiting for messages. To exit press CTRL+C")

        channel.start_consuming()

    except KeyboardInterrupt:
        logger.info("Interrupted")
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)

if __name__ == "__main__":
    main()