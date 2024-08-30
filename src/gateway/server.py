import os
import gridfs
import pika
import json
import logging
from flask import Flask, request, send_file
from flask_pymongo import PyMongo
from auth import validate
from auth_svc import access
from storage import util
from bson.objectid import ObjectId

# Configure logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Flask application
server = Flask(__name__)

# Initialize MongoDB and RabbitMQ
mongo_video = PyMongo(server, uri="mongodb://mongodb:27017/videos")
mongo_mp3 = PyMongo(server, uri="mongodb://mongodb:27017/mp3s")
fs_videos = gridfs.GridFS(mongo_video.db)
fs_mp3s = gridfs.GridFS(mongo_mp3.db)

connection = pika.BlockingConnection(pika.ConnectionParameters("rabbitmq"))
channel = connection.channel()

channel.queue_declare(queue="mp3", durable=False, exclusive=False)
channel.queue_declare(queue="video", durable=False, exclusive=False)
@server.route("/login", methods=["POST"])
def login():
    logger.debug("Login route called")
    token, err = access.login(request)

    if not err:
        logger.info("Login successful")
        return token
    else:
        logger.error(f"Login failed: {err}")
        return err


@server.route("/upload", methods=["POST"])
def upload():
    logger.debug("Upload route called")
    access, err = validate.token(request)

    if err:
        logger.error(f"Token validation error: {err}")
        return err

    try:
        access = json.loads(access)
    except json.JSONDecodeError as e:
        logger.error(f"JSON decoding error: {e}")
        return "Invalid JSON format", 400

    logger.debug(f"Access info: {access}")

    if access.get("admin"):
        if len(request.files) != 1:
            logger.warning(f"Invalid number of files: {len(request.files)}")
            return "exactly 1 file required", 400

        for filename, f in request.files.items():
            logger.debug(f"Processing file: {filename}")
            err = util.upload(f, fs_videos, channel, access)

            if err:
                logger.error(f"File upload error: {err}")
                return err

        logger.info("File uploaded successfully")
        return "success!", 200
    else:
        logger.warning("Unauthorized access attempt")
        return "not authorized", 401


@server.route("/download", methods=["GET"])
def download():
    logger.debug("Download route called")
    access, err = validate.token(request)

    if err:
        logger.error(f"Token validation error: {err}")
        return err

    try:
        access = json.loads(access)
    except json.JSONDecodeError as e:
        logger.error(f"JSON decoding error: {e}")
        return "Invalid JSON format", 400

    if access.get("admin"):
        fid_string = request.args.get("fid")

        if not fid_string:
            logger.warning("Fid is required but not provided")
            return "fid is required", 400

        try:
            out = fs_mp3s.get(ObjectId(fid_string))
            logger.info(f"File {fid_string} retrieved successfully")
            return send_file(out, download_name=f"{fid_string}.mp3")
        except Exception as e:
            logger.error(f"Error retrieving file: {e}")
            return "internal server error", 500

    logger.warning("Unauthorized access attempt")
    return "not authorized", 401


if __name__ == "__main__":
    server.run(host="0.0.0.0", port=8080)
