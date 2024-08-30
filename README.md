# Scalable Video-to-MP3 Conversion System

This project is a scalable video-to-MP3 conversion system built using a microservices architecture and modern cloud-native technologies.

## Architecture

The system is designed with a microservices architecture, allowing for modularity, scalability, and easy maintenance. The key components include:

- **API Gateway**: Handles client requests and routes them to the appropriate services.
- **Auth Service**: Manages authentication and security for the system.
- **Video Conversion Service**: Handles the actual video-to-MP3 conversion process.
- **Email Service**: Sends notifications to clients upon successful conversion.
- **MongoDB Storage**: Stores converted MP3 files and related metadata.

The system is deployed in a **Kubernetes** cluster, which manages containerized services and ensures scalability.

## Technologies

- **Programming Language**: Python
- **Web Framework**: Flask
- **Message Broker**: RabbitMQ
- **Database**: MongoDB
- **Video Processing**: FFmpeg for video/audio processing tasks.

## Workflow

1. **Client Request**: A client submits a video conversion request to the API Gateway.
2. **Authentication**: The API Gateway authenticates the client using the Auth Service.
3. **Message Queue**: Upon successful authentication, the API Gateway places a conversion request message into a RabbitMQ queue.
4. **Conversion**: The Video Conversion Service picks up the message, processes the conversion using FFmpeg, and stores the resulting MP3 file in MongoDB.
5. **Notification**: Once the conversion is complete, the API Gateway sends a notification to the client via the Email Service.

## Key Features

- **Error Handling**: Robust error handling ensures smooth operation even in the event of failures.
- **Logging and Monitoring**: Comprehensive logging and monitoring are implemented for effective troubleshooting and performance optimization.
- **Scalability**: The system is designed to scale horizontally with Kubernetes, handling increased loads efficiently.
- **Security**: Proper security measures are in place for authentication, media file handling, and protection against abuse.
