from discord import Asset

class Asset:

    __class__ = Asset

    def __init__(self, url: str = None, **kwargs):
        self._url = url
        self.__dict__.update(kwargs)

    @property
    def url(self) -> str:
        return "https://images.com/image.png" if self._url is None else self._url