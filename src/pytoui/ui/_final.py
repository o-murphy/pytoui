__all__ = ("_final_",)


def _final_(cls):
    """Decorator to mark class an non accessible base class"""

    def __init_subclass__(cls, **kwargs):
        raise TypeError(f"{cls.__name__} is not an acceptable base type")

    cls.__init_subclass__ = classmethod(__init_subclass__)
    return cls
