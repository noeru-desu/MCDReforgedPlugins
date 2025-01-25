
from mcdreforged.api.rtext import RTextList, RText, RColor

from . import shared

def tell_admin(msg):
    rtext = RTextList(RText('[aruCraftR] ', color=RColor.gray), msg)
    shared.plg_server_inst.tell('@a[tag=admin]', rtext)
    shared.plg_server_inst.logger.info(msg)
