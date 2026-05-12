This is a scanner for the Guild Wars 2 Trading Post, focused on maximizing profit margins on craftable items.

As long as an item id is provided and said item is tradeable on the trading post, it can return required base crafting materials, as well as profit margins on crafting.

## Setup

This project uses [uv](https://docs.astral.sh/uv/) for fast, reliable package management.

### Prerequisites
- Python 3.9 or higher
- [uv](https://docs.astral.sh/uv/getting-started/installation/) installed

### Installation

1. Clone or download this repository
2. Navigate to the project directory
3. Run `uv sync` to install all dependencies and create a virtual environment

```bash
uv sync
```

This creates a `.venv` directory with all necessary packages pinned to compatible versions.

### Usage

An example of the scanner's usage can be found in `Demo.ipynb`. Open it with Jupyter or your preferred notebook viewer.

### Common Commands

```bash
uv sync          # Install/sync dependencies
uv add <package> # Add a new package
uv remove <package> # Remove a package
```

Happy Crafting!

![image](https://github.com/user-attachments/assets/966bd55f-360d-4364-b88a-3cfacfa7b36c)
