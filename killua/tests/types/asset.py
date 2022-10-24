from discord import Asset

class Asset:

    __class__ = Asset

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    @property
    def url(self) -> str:
        return "https://images.com/image.png"