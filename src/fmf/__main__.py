from .cli import main as _cli_main


def main() -> None:
    # Delegate to CLI main; this lets `python -m fmf` behave like `fmf`.
    _cli_main()


if __name__ == "__main__":
    main()
