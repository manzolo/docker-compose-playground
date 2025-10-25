#!/bin/bash
set -e
echo "🎮 Installing Retro Terminal Games & ASCII Art Tools..."
CONTAINER_NAME="$1"
docker exec "${CONTAINER_NAME}" bash -c '
set -e
export DEBIAN_FRONTEND=noninteractive

# Update and install base packages
apt-get update -qq >/dev/null 2>&1
apt-get install -y -qq \
    curl wget git build-essential \
    python3 python3-pip python3-venv \
    nodejs npm \
    ncurses-dev \
    figlet toilet cowsay fortune-mod \
    cmatrix hollywood \
    bsdgames ninvaders nsnake \
    moon-buggy pacman4console \
    bastet greed nudoku \
    >/dev/null 2>&1

if [ $? -eq 0 ]; then
    echo "✓ Installed base packages"
else
    echo "✗ Failed to install base packages"
    exit 1
fi

echo "export PATH=$PATH:/usr/local/bin:/usr/games:/usr/games/bin" >> /root/.bashrc
echo "✓ Added /usr/games to PATH in /root/.bashrc"

# Create and activate Python virtual environment
python3 -m venv /opt/venv
source /opt/venv/bin/activate

# Install Python packages in virtual environment
pip install --quiet asciinema rich blessed >/dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✓ Installed Python packages in virtual environment"
else
    echo "✗ Failed to install Python packages"
    exit 1
fi

# Deactivate virtual environment after installation
deactivate

# Install terminal-based Tetris
git clone https://github.com/samtay/tetris.git /tmp/tetris >/dev/null 2>&1
cd /tmp/tetris && make && cp tetris /usr/local/bin/ 2>/dev/null || true

# Create games-menu script CORRETTO
cat > /usr/local/bin/games-menu << "EOFGAMES"
#!/bin/bash
source /opt/venv/bin/activate
clear
toilet -f big "RETRO GAMES" --gay
echo ""
echo "🎮 AVAILABLE GAMES:"
echo "==================="
echo "  ninvaders      - Space Invaders clone"
echo "  nsnake         - Snake game"
echo "  moon-buggy     - Moon buggy jumping game"
echo "  pacman4console - Pac-Man clone"
echo "  bastet         - Tetris with a twist"
echo "  greed          - Eat as much as you can"
echo "  nudoku         - Sudoku in terminal"
echo "  robots         - Escape from robots"
echo "  worm           - Growing worm game"
echo "  hangman        - Word guessing game"
echo ""
echo "🎨 ASCII ART TOOLS:"
echo "==================="
echo "  figlet <text>  - Large ASCII text"
echo "  toilet <text>  - Colorful ASCII text"
echo "  cowsay <text>  - Cow says your message"
echo "  fortune        - Random fortune"
echo "  cmatrix        - Matrix rain effect"
echo "  hollywood      - Hacker screen effect"
echo ""
echo "Type any game name to start playing!"
deactivate
EOFGAMES

chmod +x /usr/local/bin/games-menu

# Create ASCII art demo CORRETTO
cat > /usr/local/bin/ascii-demo << "EOFASCII"
#!/bin/bash
source /opt/venv/bin/activate
clear
echo "🎨 ASCII Art Demo"
echo "================="
sleep 1
figlet "Welcome!"
sleep 2
toilet --gay "Rainbow Text"
sleep 2
cowsay "Hello from the cow!"
sleep 2
fortune | cowsay -f tux
sleep 2
echo ""
echo "Starting Matrix effect (press q to quit)..."
sleep 2
timeout 5 cmatrix
echo ""
echo "Demo complete! Try these commands yourself!"
deactivate
EOFASCII

chmod +x /usr/local/bin/ascii-demo

echo "✓ Retro games and ASCII art tools installed!"
echo "Run: games-menu for the main menu"
echo "Run: ascii-demo for a demo"
'