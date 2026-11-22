def main():
    try:
        import xapian  # noqa: F401
    except ModuleNotFoundError:
        from sys import exit

        exit(
            "xapblr: the xapian Python bindings are required but could not be "
            "imported. They are not on PyPI; install them from your distribution "
            "(e.g. python-xapian on Arch, python3-xapian on Debian) and make them "
            "visible to xapblr's environment. See README.md."
        )

    from .args import argparser

    args = argparser.parse_args()
    args.func(args)
