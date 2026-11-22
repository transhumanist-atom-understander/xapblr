def main():
    try:
        import xapian  # noqa: F401
    except ModuleNotFoundError:
        from sys import exit

        exit(
            "xapblr: the xapian Python bindings are required but could not be "
            "imported. See README.md."
        )

    from .args import argparser

    args = argparser.parse_args()
    args.func(args)
