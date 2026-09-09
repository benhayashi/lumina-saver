# LuminaSaver - Modern Photo & Video Screensaver & Slideshow Player
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    QT_X11_NO_MITSHM=1

# Install system dependencies for Qt6 / PySide6, libmpv, OpenGL, and audio
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    mpv \
    libmpv-dev \
    libegl1 \
    libgl1 \
    libglx-mesa0 \
    libgl1-mesa-dri \
    libxkbcommon-x11-0 \
    libpulse0 \
    libxcb1 \
    libxcb-cursor0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-shape0 \
    libxcb-sync1 \
    libxcb-xfixes0 \
    libxcb-xinerama0 \
    libxcb-xkb1 \
    libx11-xcb1 \
    libdbus-1-3 \
    libfontconfig1 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast Python package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency definition and install
COPY pyproject.toml README.md ./
COPY lumina_saver ./lumina_saver
COPY resources ./resources

# Install package and dependencies into system environment
RUN uv pip install --system --break-system-packages .

# Create media directory for mounting host photos/videos
RUN mkdir -p /media /root/.lumina_saver

# Set default media directory in container config
RUN echo '{"media_directories": ["/media"], "window_mode": "fullscreen"}' > /root/.lumina_saver/config.json

VOLUME ["/media", "/root/.lumina_saver"]

ENTRYPOINT ["lumina-saver"]
CMD ["--fullscreen"]
