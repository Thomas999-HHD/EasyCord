"""Desktop Command Center integration for EasyCord."""


def launch() -> None:
    """Launch the EasyCord desktop Command Center."""
    try:
        from .main import main
    except ImportError as exc:
        raise RuntimeError(
            'The desktop Command Center requires optional desktop dependencies. '
            'Install them with: pip install "easycord[desktop]"'
        ) from exc
    main()


__all__ = ["launch"]
