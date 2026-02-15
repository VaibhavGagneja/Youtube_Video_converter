"""
Tests for the Converter microservice.
Covers: to_mp3.start() conversion logic.
"""
import json
import pytest
from unittest.mock import patch, MagicMock, mock_open
import os

os.environ.setdefault("VIDEO_QUEUE", "video")
os.environ.setdefault("MP3_QUEUE", "mp3")


class TestToMp3:
    """Tests for the video to MP3 conversion logic."""

    @patch("convert.to_mp3.os.remove")
    @patch("builtins.open", new_callable=mock_open, read_data=b"fake_audio")
    @patch("convert.to_mp3.tempfile")
    @patch("convert.to_mp3.moviepy.editor.VideoFileClip")
    def test_start_successful_conversion(self, mock_video, mock_tempfile,
                                          mock_file, mock_remove):
        from convert.to_mp3 import start

        # Setup mocks
        fs_videos = MagicMock()
        fs_mp3s = MagicMock()
        channel = MagicMock()

        fs_videos.get.return_value.read.return_value = b"fake_video_data"
        fs_mp3s.put.return_value = "mp3_fid_123"

        mock_tf = MagicMock()
        mock_tf.name = "/tmp/test_video"
        mock_tempfile.NamedTemporaryFile.return_value = mock_tf
        mock_tempfile.gettempdir.return_value = "/tmp"

        mock_audio = MagicMock()
        mock_video.return_value.audio = mock_audio

        message = json.dumps({
            "video_fid": "video_fid_123",
            "mp3_fid": None,
            "username": "test@test.com"
        })

        result = start(message, fs_videos, fs_mp3s, channel)

        # Verify file was retrieved from MongoDB
        fs_videos.get.assert_called_once()

        # Verify audio was extracted
        mock_audio.write_audiofile.assert_called_once()

        # Verify MP3 was stored in MongoDB
        fs_mp3s.put.assert_called_once()

        # Verify message published to RabbitMQ
        channel.basic_publish.assert_called_once()
        assert result is None  # No error

    def test_start_handles_invalid_message(self):
        from convert.to_mp3 import start

        fs_videos = MagicMock()
        fs_mp3s = MagicMock()
        channel = MagicMock()

        result = start(b"invalid json", fs_videos, fs_mp3s, channel)
        assert result is not None  # Should return error

    def test_start_handles_missing_video(self):
        from convert.to_mp3 import start

        fs_videos = MagicMock()
        fs_mp3s = MagicMock()
        channel = MagicMock()

        fs_videos.get.side_effect = Exception("File not found")

        message = json.dumps({
            "video_fid": "nonexistent",
            "mp3_fid": None,
            "username": "test@test.com"
        })

        result = start(message, fs_videos, fs_mp3s, channel)
        assert result is not None  # Should return error

    @patch("convert.to_mp3.os.remove")
    @patch("builtins.open", new_callable=mock_open, read_data=b"fake_audio")
    @patch("convert.to_mp3.tempfile")
    @patch("convert.to_mp3.moviepy.editor.VideoFileClip")
    def test_start_cleans_up_on_publish_failure(self, mock_video, mock_tempfile,
                                                 mock_file, mock_remove):
        from convert.to_mp3 import start

        fs_videos = MagicMock()
        fs_mp3s = MagicMock()
        channel = MagicMock()

        fs_videos.get.return_value.read.return_value = b"fake_video_data"
        fs_mp3s.put.return_value = "mp3_fid_123"

        mock_tf = MagicMock()
        mock_tf.name = "/tmp/test"
        mock_tempfile.NamedTemporaryFile.return_value = mock_tf
        mock_tempfile.gettempdir.return_value = "/tmp"

        mock_audio = MagicMock()
        mock_video.return_value.audio = mock_audio

        # Simulate publish failure
        channel.basic_publish.side_effect = Exception("RabbitMQ down")

        message = json.dumps({
            "video_fid": "video_fid_123",
            "mp3_fid": None,
            "username": "test@test.com"
        })

        result = start(message, fs_videos, fs_mp3s, channel)

        # Should clean up the MP3 from MongoDB on failure
        fs_mp3s.delete.assert_called_once_with("mp3_fid_123")
        assert result == "failed to publish message"
