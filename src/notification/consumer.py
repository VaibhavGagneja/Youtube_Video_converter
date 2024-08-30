import pika, sys, os, time,logging
from send import email

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
def main():
    logger.info("Starting notification consumer")
    try:
        # rabbitmq connection
        connection = pika.BlockingConnection(pika.ConnectionParameters(host="rabbitmq"))
        logger.info("Connected to RabbitMQ")

        channel = connection.channel()
        logger.info("Created channel")

        def callback(ch, method, properties, body):
            logger.info(f"Received message from queue: {method.routing_key}")
            try:
                err = email.notification(body)
                if err:
                    logger.error(f"Error sending email: {err}")
                    ch.basic_nack(delivery_tag=method.delivery_tag)
                else:
                    logger.info("Email sent successfully")
                    ch.basic_ack(delivery_tag=method.delivery_tag)
            except Exception as e:
                logger.error(f"Error sending email: {e}")
                ch.basic_nack(delivery_tag=method.delivery_tag)
        channel.basic_consume(
            queue=os.environ.get("MP3_QUEUE"), on_message_callback=callback
        )
        logger.info("Started consuming messages from queue")
        channel.start_consuming()

    except Exception as e:
        logger.error(f"Error starting notification consumer: {e}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupted")
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
