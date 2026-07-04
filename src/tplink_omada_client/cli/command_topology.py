"""Implementation for 'topology' command"""

from argparse import ArgumentParser

from tplink_omada_client.definitions import DeviceStatusCategory, LinkSpeed
from tplink_omada_client.topology import OmadaTopologyNode

from .config import get_target_config, to_omada_connection
from .util import dump_raw_data, get_checkbox_char, get_target_argument


async def command_topology(args) -> int:
    """Executes 'topology' command"""
    controller = get_target_argument(args)
    config = get_target_config(controller)

    async with to_omada_connection(config) as client:
        site_client = await client.get_site_client(config.site)
        topology = await site_client.get_topology()

        _print_children(topology.roots, "", args)

    return 0


def _print_children(nodes: list[OmadaTopologyNode], prefix: str, args) -> None:
    for index, node in enumerate(nodes):
        is_last = index == len(nodes) - 1
        connector = "└── " if is_last else "├── "
        extension = "    " if is_last else "│   "

        print(f"{prefix}{connector}{_format_node(node)}")
        dump_raw_data(args, node)
        _print_children(node.successors, prefix + extension, args)


def _format_node(node: OmadaTopologyNode) -> str:
    # "omada controller" is itself the physical controller appliance; the type label
    # would otherwise redundantly repeat its own device name (e.g. "Omada Controller
    # [omada controller]").
    type_label = "controller" if node.type == "omada controller" else node.type
    checkbox = get_checkbox_char(not node.disconnected)

    upstream_link_speed = node.upstream_link_speed
    if node.upstream_port is not None:
        speed = upstream_link_speed.name[6:] if upstream_link_speed != LinkSpeed.UNKNOWN else "?"
        port_info = f" <- port {node.upstream_port} ({checkbox} {speed})"
    else:
        port_info = f" ({checkbox})"

    status_info = ""
    if node.status_category not in (DeviceStatusCategory.UNKNOWN, DeviceStatusCategory.CONNECTED):
        status_info = f" [{node.status.name} / {node.status_category.name}]"

    wan_info = ""
    wan_ports = node.wan_ports
    if wan_ports:
        summaries = [
            f"{wan.name}: {get_checkbox_char(wan.wan_connected)} {wan.link_speed.name[6:]}" for wan in wan_ports
        ]
        wan_info = f" ({', '.join(summaries)})"
    return f"{node.name} [{type_label}] {node.mac}{port_info}{status_info}{wan_info}"


def arg_parser(subparsers) -> None:
    """Configures arguments parser for 'topology' command"""
    topology_parser: ArgumentParser = subparsers.add_parser(
        "topology", help="Shows the site's physical network topology tree (device wiring map)"
    )
    topology_parser.set_defaults(func=command_topology)
    topology_parser.add_argument("-d", "--dump", help="Output raw topology node information", action="store_true")
