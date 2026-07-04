"""Tests for the site topology tree."""

import asyncio

from tplink_omada_client.definitions import DeviceStatus, DeviceStatusCategory, LinkSpeed, LinkStatus
from tplink_omada_client.omadasiteclient import OmadaSiteClient
from tplink_omada_client.topology import OmadaTopology


def _topology_data() -> dict:
    return {
        "topologyArray": [
            {
                "type": "gateway",
                "name": "test-gateway",
                "mac": "gateway-mac",
                "model": "ER-TEST",
                "ip": "192.0.2.1",
                "status": 14,
                "statusCategory": 1,
                "clientCount": 0,
                "successors": [
                    {
                        "type": "switch",
                        "name": "test-switch",
                        "mac": "switch-mac",
                        "model": "SG-TEST",
                        "ip": "192.0.2.2",
                        "status": 14,
                        "statusCategory": 1,
                        "clientCount": 0,
                        "successors": [],
                        "wiredUpInfo": {
                            "port": {"port": "1"},
                            "upLinkPort": {"port": "4"},
                            "linkSpeed": 3,
                            "duplex": 2,
                        },
                    }
                ],
            }
        ],
        "lastUpdateTime": 1700000000000,
    }


class FakeApi:
    def __init__(self, topology: dict) -> None:
        self.topology = topology
        self.requests = []

    def format_url(self, end_point: str, site: str | None = None) -> str:
        return f"api/{site}/{end_point}"

    async def request(self, method: str, url: str, params=None, json=None, data=None):
        self.requests.append((method, url))
        if method == "get" and url.endswith("/topology"):
            return self.topology
        raise AssertionError(f"Unexpected request: {method} {url}")


def test_get_topology_returns_root_nodes():
    api = FakeApi(_topology_data())
    client = OmadaSiteClient("site-id", api)

    topology = asyncio.run(client.get_topology())

    assert isinstance(topology, OmadaTopology)
    assert api.requests == [("get", "api/site-id/topology")]
    assert len(topology.roots) == 1
    assert topology.roots[0].name == "test-gateway"
    assert topology.roots[0].type == "gateway"
    assert topology.roots[0].status_category == DeviceStatusCategory.CONNECTED


def test_topology_node_exposes_upstream_port_and_link_speed():
    topology = OmadaTopology(_topology_data())

    switch = topology.roots[0].successors[0]

    assert switch.name == "test-switch"
    assert switch.mac == "switch-mac"
    assert switch.own_uplink_port == "1"
    assert switch.upstream_port == "4"
    assert switch.upstream_link_speed == LinkSpeed.SPEED_1_GBPS
    assert switch.successors == []


def test_topology_node_defaults_missing_fields_to_unknown():
    node_data = {"type": "ap", "mac": "ap-mac"}
    topology = OmadaTopology({"topologyArray": [node_data]})

    node = topology.roots[0]

    assert node.name == "ap-mac"
    assert node.model is None
    assert node.ip_address is None
    assert node.upstream_port is None
    assert node.upstream_link_speed == LinkSpeed.UNKNOWN
    assert node.status_category == DeviceStatusCategory.UNKNOWN


def test_topology_node_disconnected_defaults_to_false():
    node_data = {"type": "ap", "mac": "ap-mac"}
    topology = OmadaTopology({"topologyArray": [node_data]})

    assert topology.roots[0].disconnected is False


def test_topology_node_reports_disconnected_when_flagged():
    node_data = {"type": "ap", "mac": "ap-mac", "disconnected": True}
    topology = OmadaTopology({"topologyArray": [node_data]})

    assert topology.roots[0].disconnected is True


def test_topology_node_reports_non_connected_status():
    node_data = {"type": "ap", "mac": "ap-mac", "status": 13, "statusCategory": 0}
    topology = OmadaTopology({"topologyArray": [node_data]})

    node = topology.roots[0]

    assert node.status == DeviceStatus.REBOOTING
    assert node.status_category == DeviceStatusCategory.DISCONNECTED


def test_topology_node_has_no_wan_ports_when_not_a_gateway():
    node_data = {"type": "ap", "mac": "ap-mac"}
    topology = OmadaTopology({"topologyArray": [node_data]})

    assert topology.roots[0].wan_ports == []


def test_topology_gateway_exposes_wan_port_summary():
    node_data = {
        "type": "gateway",
        "mac": "gateway-mac",
        "wanPorts": [
            {
                "port": "1",
                "name": "WAN1",
                "status": 1,
                "internetState": 1,
                "onlineDetection": 1,
                "linkSpeed": 3,
                "duplex": 2,
            }
        ],
    }
    topology = OmadaTopology({"topologyArray": [node_data]})

    wan_port = topology.roots[0].wan_ports[0]

    assert wan_port.name == "WAN1"
    assert wan_port.link_status == LinkStatus.LINK_UP
    assert wan_port.link_speed == LinkSpeed.SPEED_1_GBPS
    assert wan_port.wan_connected is True
    assert wan_port.online_detection is True
