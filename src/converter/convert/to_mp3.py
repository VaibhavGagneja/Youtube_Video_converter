import logging
import tempfile
import json
import os
import pika
from bson.objectid import ObjectId
import moviepy.editor

# Configure logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def start(message, fs_videos, fs_mp3s, channel):
    try:
        logger.info("Received message: {}".format(message))
        message = json.loads(message)
        logger.debug("Parsed message: {}".format(message))

        # empty temp file
        tf = tempfile.NamedTemporaryFile()
        logger.debug("Created temp file: {}".format(tf.name))

        # video contents
        out = fs_videos.get(ObjectId(message["video_fid"]))
        logger.debug("Retrieved video contents from MongoDB")

        # add video contents to empty file
        tf.write(out.read())
        logger.debug("Wrote video contents to temp file")

        # create audio from temp video file
        audio = moviepy.editor.VideoFileClip(tf.name).audio
        logger.debug("Extracted audio from video")

        tf.close()
        logger.debug("Closed temp file")

        # write audio to the file
        tf_path = tempfile.gettempdir() + f"/{message['video_fid']}.mp3"
        audio.write_audiofile(tf_path)
        logger.debug("Wrote audio to file: {}".format(tf_path))

        # save file to mongo
        f = open(tf_path, "rb")
        data = f.read()
        fid = fs_mp3s.put(data)
        logger.info("Saved audio to MongoDB with fid: {}".format(fid))
        f.close()
        os.remove(tf_path)
        logger.debug("Removed temp audio file")

        message["mp3_fid"] = str(fid)

        try:
            channel.basic_publish(
                exchange="",
                routing_key=os.environ.get("MP3_QUEUE"),
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE
                ),
            )
            logger.info("Message published to RabbitMQ: {message}")
        except Exception as err:
            logger.error("Failed to publish message: {}".format(err))
            fs_mp3s.delete(fid)
            logger.error("Deleted audio from MongoDB with fid: {}".format(fid))
            return "failed to publish message"

    except Exception as err:
        logger.error("Error processing message: {}".format(err))
        return "error processing message"