"""
Definitions for the site's physical network topology tree.

Unlike the device and client APIs, which report each device or client in
isolation, the topology endpoint reports the actual physical wiring between
managed devices (gateway, switches, APs) and their nearest recognized
downstream nodes, including which port on the upstream device each node is
plugged into.
"""

from .definitions import DeviceStatus, DeviceStatusCategory, LinkDuplex, LinkSpeed, LinkStatus, OmadaApiData


class OmadaTopologyWanPort(OmadaApiData):
    """Summary WAN port health, as reported on a gateway node in the topology tree."""

    @property
    def port(self) -> str:
        """The port number."""
        return self._data["port"]

    @property
    def name(self) -> str:
        """The port name."""
        return self._data.get("name", self.port)

    @property
    def link_status(self) -> LinkStatus:
        """Low level connectivity status of the link."""
        return LinkStatus(self._data.get("status", LinkStatus.UNKNOWN))

    @property
    def link_speed(self) -> LinkSpeed:
        """The established link speed of the port."""
        return LinkSpeed(self._data.get("linkSpeed", LinkSpeed.UNKNOWN))

    @property
    def duplex(self) -> LinkDuplex:
        """Actual duplex mode of the port."""
        return LinkDuplex(self._data.get("duplex", LinkDuplex.UNKNOWN))

    @property
    def wan_connected(self) -> bool:
        """True, if the port is connected to the internet/WAN."""
        return self._data.get("internetState", 0) != 0

    @property
    def online_detection(self) -> bool:
        """True, if regular internet ping tests are working."""
        return self._data.get("onlineDetection", 0) != 0


class OmadaTopologyNode(OmadaApiData):
    """A single node (device, or a directly-identifiable client) in the topology tree."""

    @property
    def type(self) -> str:
        """The type of node. Known values include "gateway", "switch", "ap", and "omada controller"."""
        return self._data["type"]

    @property
    def mac(self) -> str:
        """The MAC address of the node."""
        return self._data["mac"]

    @property
    def name(self) -> str:
        """The display name of the node."""
        return self._data.get("name", self.mac)

    @property
    def model(self) -> str | None:
        """The model of the node, if it's a managed Omada device."""
        return self._data.get("model")

    @property
    def ip_address(self) -> str | None:
        """The IP address of the node, if known."""
        return self._data.get("ip")

    @property
    def status(self) -> DeviceStatus:
        """The status of the node, if it's a managed Omada device."""
        return DeviceStatus(self._data.get("status", DeviceStatus.UNKNOWN))

    @property
    def status_category(self) -> DeviceStatusCategory:
        """The high-level status of the node, if it's a managed Omada device."""
        return DeviceStatusCategory(self._data.get("statusCategory", DeviceStatusCategory.UNKNOWN))

    @property
    def disconnected(self) -> bool:
        """True, if the node is currently disconnected."""
        return self._data.get("disconnected", False)

    @property
    def client_count(self) -> int:
        """Number of clients attached to this node, if it's a managed Omada device."""
        return self._data.get("clientCount", 0)

    @property
    def upstream_port(self) -> str | None:
        """The port number, on the parent node, that this node is plugged into."""
        uplink_port = self._data.get("wiredUpInfo", {}).get("upLinkPort")
        return uplink_port.get("port") if uplink_port else None

    @property
    def own_uplink_port(self) -> str | None:
        """The port number, on this node's own hardware, used for its uplink (switches only)."""
        own_port = self._data.get("wiredUpInfo", {}).get("port")
        return own_port.get("port") if own_port else None

    @property
    def upstream_link_speed(self) -> LinkSpeed:
        """The negotiated link speed between this node and its parent."""
        return LinkSpeed(self._data.get("wiredUpInfo", {}).get("linkSpeed", LinkSpeed.UNKNOWN))

    @property
    def upstream_duplex(self) -> LinkDuplex:
        """The negotiated duplex mode between this node and its parent."""
        return LinkDuplex(self._data.get("wiredUpInfo", {}).get("duplex", LinkDuplex.UNKNOWN))

    @property
    def successors(self) -> list["OmadaTopologyNode"]:
        """The nodes plugged into this node."""
        return [OmadaTopologyNode(s) for s in self._data.get("successors", [])]

    @property
    def wan_ports(self) -> list[OmadaTopologyWanPort]:
        """WAN port health summaries, for gateway nodes."""
        return [OmadaTopologyWanPort(p) for p in self._data.get("wanPorts", [])]


class OmadaTopology(OmadaApiData):
    """The site's full physical network topology tree, rooted at its gateway(s)."""

    @property
    def roots(self) -> list[OmadaTopologyNode]:
        """The root nodes of the topology tree (typically the site's gateway(s))."""
        return [OmadaTopologyNode(n) for n in self._data.get("topologyArray", [])]
