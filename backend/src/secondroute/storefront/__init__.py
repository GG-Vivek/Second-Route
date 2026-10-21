"""
The public storefront (Phase 10).

The storefront is the shop window: a page anybody can look at, with the
devices that are for sale on it. It is a separate application on its own
port, and it reads through this module.

Nothing here is for the operator. The serial number, the reason the
device came back, the notes the person who took the return in wrote, the
cost of handling it and the engine's confidence are all the business's
own business, and none of them are on a shop window.
"""

from secondroute.storefront.api import router as storefront_router

__all__ = ["storefront_router"]
