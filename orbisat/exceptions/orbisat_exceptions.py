class NewOrbisatSetupError(Exception):
    """Program can't find required satellite or station"""


class NewOrbisatIndexError(Exception):
    """Program can't use this index."""


class NewOrbisatDataError(Exception):
    """This data aren't defined yet."""
