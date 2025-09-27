#!/bin/bash

# Install additional system dependencies for Ubuntu deployment
# Run this script before the main setup script

echo "Installing additional system dependencies for speech processing..."

# Update system
sudo apt update

# Install FFmpeg and media libraries
sudo apt install -y \
    ffmpeg \
    libavcodec-extra \
    libavformat-dev \
    libavdevice-dev \
    libavfilter-dev \
    libavresample-dev \
    libswscale-dev \
    libswresample-dev \
    libavutil-dev

# Install Python development packages
sudo apt install -y \
    python3-dev \
    python3-pip \
    python3-setuptools \
    python3-wheel \
    python3-venv

# Install system libraries for Python packages
sudo apt install -y \
    build-essential \
    pkg-config \
    libssl-dev \
    libffi-dev \
    libjpeg-dev \
    libpng-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libwebp-dev \
    libtiff5-dev \
    libopenjp2-7-dev \
    zlib1g-dev

# Install additional multimedia tools
sudo apt install -y \
    imagemagick \
    ghostscript \
    poppler-utils

# Install faster-whisper dependencies (if not already installed)
echo "Installing faster-whisper..."
pip3 install faster-whisper

# Verify installations
echo "Verifying installations..."

echo "FFmpeg version:"
ffmpeg -version | head -1

echo "Python version:"
python3 --version

echo "Faster-whisper installation:"
python3 -c "import faster_whisper; print('faster-whisper installed successfully')" 2>/dev/null || echo "faster-whisper installation may need attention"

echo "Dependencies installation completed!"