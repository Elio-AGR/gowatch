# gowatch 🚀

**gowatch** is a lightweight, super-fast, and robust Go hot-reloading CLI tool built with Python. Designed for high performance, smooth Linux/SSH development, and TUI (Terminal User Interface) applications.

---

## ✨ Features

- ⚡ **Process Group Management**: Spawns processes in their own process group (`os.setsid`) and terminates the entire process tree using `os.killpg`—say goodbye to zombie processes or Ctrl+C hangs!
- 🧠 **Smart Command Detection**: Automatically runs `go test -v ./...` when modifying test files (`*_test.go`), or `go run .` for regular Go source files.
- 📺 **TUI / Check Mode (`-c` / `--check`)**: Executes `go build -o /dev/null .` to check compilation without launching interactive binaries or causing terminal screen flickering.
- 🧹 **Clean Terminal & Recovery**: Automatically clears the terminal on reload and guarantees terminal style and cursor restoration on exit (`\033[0m\033[?25h`).
- 🛡️ **Smart File & Directory Filtering**: Automatically ignores hidden directories (`.git`, `.venv`, `.idea`, `.vscode`), dependency/build folders (`venv`, `__pycache__`, `bin`, `node_modules`), and editor temporary files (`*~`, `*.tmp`, `*.swp`, `.tmp.*`).
- ⏱️ **Execution Timer & Colored UI**: Clear timestamped status output with execution duration benchmarks in milliseconds or seconds.
- 🎛️ **Custom Commands & Configurable Debounce**: Specify custom execution commands or adjust debounce intervals (`-b`).

---

## 📥 Installation

1. **Clone the repository**:
   ```bash
   git clone git@github.com:Elio-AGR/gowatch.git
   cd gowatch
   ```

2. **Setup virtual environment & install requirements**:
   ```bash
   python3 -m venv venv
   ./venv/bin/pip install -r requirements.txt
   ```

3. **Install CLI wrapper globally**:
   ```bash
   ./install.sh
   ```
   *(Ensure `~/.local/bin` is in your `$PATH` environment variable).*

---

## 🚀 Usage

### Basic Usage
Run `gowatch` inside your Go project root:
```bash
gowatch
```

### Options & Flags

| Flag | Long Flag | Description | Default |
|------|-----------|-------------|---------|
| `-d` | `--dir` | Directory to watch for changes | `.` |
| `-b` | `--debounce` | Debounce timeout interval in seconds | `0.3` |
| `-c` | `--check` | Dry compilation check (`go build -o /dev/null .`) for TUI apps | `False` |
| | `--no-clear` | Disable automatic terminal screen clearing | `False` |
| `cmd` | | Optional custom command to execute | `go run .` / `go test` |

### Examples

- **Watch a specific directory**:
  ```bash
  gowatch -d ./cmd/server
  ```

- **TUI Mode (dry compile without terminal flicker)**:
  ```bash
  gowatch -c
  ```

- **Prevent terminal screen clearing**:
  ```bash
  gowatch --no-clear
  ```

- **Run custom commands**:
  ```bash
  gowatch go test -v ./...
  ```
  ```bash
  gowatch go build -o bin/app .
  ```

- **Custom debounce delay (e.g. 0.5s)**:
  ```bash
  gowatch -b 0.5
  ```

---

## 📄 License

MIT License
