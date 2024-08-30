import pika
import json
import logging

# Configure logging (if not already configured in your main application)
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def upload(f, fs, channel, access):
    logger.debug("Upload function called")

    try:
        # Attempt to store the file in GridFS
        fid = fs.put(f)
        logger.info(f"File uploaded successfully with ID: {fid}")
    except Exception as err:
        logger.error(f"Error storing file in GridFS: {err}")
        return "internal server error", 500

    # Prepare the message for RabbitMQ
    message = {
        "video_fid": str(fid),
        "mp3_fid": None,
        "username": access["username"],
    }

    try:
        # channel.queue_declare(queue="mp3", durable=False, exclusive=False)
        # channel.queue_declare(queue="video", durable=False, exclusive=False)
        # Publish the message to the RabbitMQ queue
        channel.basic_publish(
            exchange="",
            routing_key="video",
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE
            ),
        )
        logger.info(f"Message published to RabbitMQ: {message}")

    except Exception as err:
        logger.error(f"Error publishing message to RabbitMQ: {err}")
        try:
            # Clean up by deleting the file from GridFS if message publishing fails
            fs.delete(fid)
            logger.info(f"File with ID {
                        fid} deleted from GridFS due to RabbitMQ failure")
        except Exception as cleanup_err:
            logger.error(
                f"Error deleting file from GridFS during cleanup: {cleanup_err}")
        return "internal server error", 500

    return "success", 200
