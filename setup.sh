#!/bin/bash
# ══════════════════════════════════════════════════════════════════
#  setup.sh — Cài đặt môi trường cho Face Auth Demo
#  Nhóm 10, Lớp 01 — Introduction to Information Security
# ══════════════════════════════════════════════════════════════════

set -e
echo "╔══════════════════════════════════════════════╗"
echo "║     Face Authentication Demo — Setup         ║"
echo "╚══════════════════════════════════════════════╝"

# ── 1. Kiểm tra Python ──────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
    echo "❌ Cần Python 3.9+ để chạy demo này."
    exit 1
fi
PYTHON=$(python3 --version)
echo "✅ Python: $PYTHON"

# ── 2. Tạo virtual environment ──────────────────────────────────────
if [ ! -d "venv" ]; then
    echo "🔧 Tạo virtual environment..."
    python3 -m venv venv
fi
source venv/bin/activate
echo "✅ Virtual environment đã kích hoạt"

# ── 3. Upgrade pip ──────────────────────────────────────────────────
pip install --upgrade pip -q

# ── 4. Cài thư viện hệ thống (Ubuntu/Debian) ───────────────────────
if command -v apt-get &>/dev/null; then
    echo "📦 Cài thư viện hệ thống (cần sudo)..."
    sudo apt-get install -y \
        cmake \
        build-essential \
        libopenblas-dev \
        liblapack-dev \
        libx11-dev \
        libgtk-3-dev \
        python3-dev \
        libboost-python-dev \
        2>/dev/null || true
fi

# ── 5. Cài Python packages ──────────────────────────────────────────
echo "📦 Cài Python packages..."
pip install cmake
pip install dlib
pip install face-recognition
pip install opencv-python
pip install flask flask-cors
pip install scipy Pillow numpy

echo "✅ Tất cả packages đã cài"

# ── 6. Kiểm tra cài đặt ─────────────────────────────────────────────
echo ""
echo "🔍 Kiểm tra imports..."
python3 -c "
import cv2
import face_recognition
import flask
import numpy as np
from scipy.spatial import distance
print('✅ Tất cả imports thành công!')
print(f'   - OpenCV  : {cv2.__version__}')
print(f'   - Flask   : {flask.__version__}')
print(f'   - NumPy   : {np.__version__}')
"

# ── 7. Tạo thư mục data ──────────────────────────────────────────────
mkdir -p data/users
echo "✅ Thư mục data/users đã tạo"

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║  ✅ Cài đặt hoàn tất!                        ║"
echo "║                                              ║"
echo "║  Chạy demo:                                  ║"
echo "║    source venv/bin/activate                  ║"
echo "║    python app.py                             ║"
echo "║                                              ║"
echo "║  Mở trình duyệt: http://localhost:5000       ║"
echo "╚══════════════════════════════════════════════╝"
