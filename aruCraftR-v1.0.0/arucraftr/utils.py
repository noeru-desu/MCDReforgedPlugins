
from mcdreforged.api.rtext import RTextList, RText, RColor

from . import shared

def tell_admin(msg, log=True):
    rtext = RTextList(RText('[aruCraftR] ', color=RColor.dark_aqua), msg)
    shared.plg_server_inst.tell('@a[tag=admin]', rtext)
    if log:
        shared.plg_server_inst.logger.info(msg)
