#!/bin/bash
set -e

INSTALL_DIR="$HOME/.local/bin/LazyOpt"
mkdir -p "$INSTALL_DIR"

echo "INSTALL SCRIPT FOR LazyOpt"

if [ -f "./LazyOpt" ] && [ -f "./server" ]; then
    echo "Found LazyOpt executable & server executable!"
else
    echo "Could not find LazyOpt executable & server executable, getting them!"
    read -p "The script is trying to download the executables, do you wish to download them? (yes/no): " YesOrNo
    if [ "$YesOrNo" = "yes" ]; then
        echo "Yes detected! Downloading files..."
        curl -L "https://github.com/alanbutidk/LazyOpt/releases/download/lin64-v1.0.1/LazyOptLinux64v1.0.1.zip" -o "./LazyOptLinux64v1.0.1.zip"
    else
        echo "No detected! Not downloading the files!"
        exit 0
    fi

    echo "Extracting..."
    unzip "./LazyOptLinux64v1.0.1.zip" -d "$INSTALL_DIR"
    echo "Almost Done! Files extracted to: $INSTALL_DIR"

    echo "Cleaning up..."
    rm "./LazyOptLinux64v1.0.1.zip"

    echo "Adding executable(s) to PATH!"
    chmod +x "$INSTALL_DIR/LazyOpt" "$INSTALL_DIR/server" 2>/dev/null || true

    SHELL_RC="$HOME/.bashrc"
    [ -n "$ZSH_VERSION" ] && SHELL_RC="$HOME/.zshrc"

    if ! grep -q "$INSTALL_DIR" "$SHELL_RC"; then
        echo "export PATH=\"\$PATH:$INSTALL_DIR\"" >> "$SHELL_RC"
    fi

    echo "Done! Run: source $SHELL_RC  (or restart your terminal)"
fi
