#!/bin/bash

# ReMind V2 Installation Script
# Automates the installation process for macOS/Linux

set -e  # Exit on error

echo "=================================="
echo "🧠 ReMind V2 Installation Script"
echo "=================================="
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
required_version="3.7"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Python 3.7+ required. You have Python $python_version"
    exit 1
fi

echo "✅ Python $python_version detected"
echo ""

# Check OS
echo "Detecting operating system..."
OS="$(uname -s)"
case "${OS}" in
    Linux*)     machine=Linux;;
    Darwin*)    machine=Mac;;
    *)          machine="UNKNOWN:${OS}"
esac

echo "✅ Running on: $machine"
echo ""

# Install system dependencies
if [ "$machine" = "Mac" ]; then
    echo "Installing macOS dependencies..."

    # Check if Homebrew is installed
    if ! command -v brew &> /dev/null; then
        echo "⚠️  Homebrew not found. Please install from https://brew.sh"
        echo "   Then run this script again."
        exit 1
    fi

    echo "Installing CMake (required for dlib)..."
    brew install cmake || echo "CMake might already be installed"

elif [ "$machine" = "Linux" ]; then
    echo "Installing Linux dependencies..."

    sudo apt-get update
    sudo apt-get install -y \
        cmake \
        python3-dev \
        libopenblas-dev \
        liblapack-dev \
        libx11-dev \
        libgtk-3-dev \
        || echo "Some packages might already be installed"
fi

echo ""
echo "=================================="
echo "Installing Python packages..."
echo "=================================="
echo ""

# Upgrade pip
echo "Upgrading pip..."
python3 -m pip install --upgrade pip

# Install requirements
echo ""
echo "Installing required packages..."
echo "⚠️  Note: Installing dlib may take 5-10 minutes"
echo ""

python3 -m pip install -r requirements.txt

echo ""
echo "=================================="
echo "Verifying installation..."
echo "=================================="
echo ""

# Verify installations
echo "Checking installed packages..."

check_package() {
    package=$1
    if python3 -c "import $package" 2>/dev/null; then
        echo "✅ $package installed successfully"
        return 0
    else
        echo "❌ $package installation failed"
        return 1
    fi
}

all_ok=true

check_package "cv2" || all_ok=false
check_package "face_recognition" || all_ok=false
check_package "whisper" || all_ok=false
check_package "sounddevice" || all_ok=false
check_package "flask" || all_ok=false
check_package "numpy" || all_ok=false

echo ""

if [ "$all_ok" = true ]; then
    echo "=================================="
    echo "✅ Installation Complete!"
    echo "=================================="
    echo ""
    echo "🎉 ReMind V2 is ready to use!"
    echo ""
    echo "Quick Start:"
    echo "  1. Enroll a person:"
    echo "     python3 quick_enroll.py --name \"Your Name\" --relationship \"Self\""
    echo ""
    echo "  2. Start the web interface:"
    echo "     python3 web_app.py"
    echo "     Then open: http://localhost:5000"
    echo ""
    echo "  3. Or start the desktop app:"
    echo "     python3 remind_assistant_v2.py"
    echo ""
    echo "📖 For detailed instructions, see:"
    echo "   - README_V2.md (overview)"
    echo "   - SETUP_GUIDE.md (detailed setup)"
    echo ""
else
    echo "=================================="
    echo "⚠️  Installation Issues Detected"
    echo "=================================="
    echo ""
    echo "Some packages failed to install."
    echo "Please check the error messages above."
    echo ""
    echo "Common solutions:"
    echo "  1. Make sure you have Python 3.7+"
    echo "  2. Try: pip3 install --user -r requirements.txt"
    echo "  3. Check SETUP_GUIDE.md for manual installation"
    echo ""
    exit 1
fi
