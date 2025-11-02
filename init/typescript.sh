#!/bin/sh
# TypeScript container initialization

echo "Installing TypeScript globally..."
npm install -g typescript ts-node @types/node

echo "TypeScript installed successfully!"
tsc --version
